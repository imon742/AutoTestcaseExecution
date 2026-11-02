import asyncio,csv,json
from pathlib import Path
import pytest
from local_qa.models import Case,Policy,Blocked,select_scope,redact
from local_qa.store import Store
from local_qa.importer import load_file
from local_qa.writers import result_copy,SheetsOAuth
from local_qa.fixture import Fixture,MemoryVault
from local_qa.supervisor import Supervisor

class DeterministicLocalModel:
    """Protocol test double; real local-model acceptance is tested separately."""
    def validate_model(self):return {}
    async def json(self,prompt,schema,image=None):
        if '"case_id": "F12"' in prompt:raise Blocked('Simulated local model timeout')
        if 'REQUIRED NEXT SOURCE ACTION=' in prompt:
            return json.loads(prompt.rsplit('REQUIRED NEXT SOURCE ACTION=',1)[1])
        return {'kind':'verify','locator':{'by':'role','name':'','role':''},'value':'','category':'read','reason':'verify'}

def test_scope_seven_cases_with_two_historical_passes():
    cases=[Case(str(i),scenario_id='A' if i<4 else 'B',source_status=' PaSs ' if i<2 else 'Not Run').seal() for i in range(7)]
    assert len(select_scope(cases))==5
    assert len(select_scope(cases,'all'))==7
    assert len(select_scope(cases,'all','B'))==3

def test_store_crash_recovery_and_no_duplicate_commits(tmp_path):
    path=tmp_path/'db.sqlite';s=Store(path);cases=[Case('A').seal(),Case('B').seal()]
    run=s.create_run(cases,{},{});attempt=s.begin(run,cases[0]);s.close()
    s=Store(path);s.recover();assert s.next_case(run).case_id=='A'
    a=s.begin(run,cases[0]);s.commit(a,'Pass','Verified',{},[])
    with pytest.raises(ValueError):s.commit(a,'Pass','Duplicate',{},[])
    assert s.next_case(run).case_id=='B'
    s.close()

def test_specific_fixture_approval_and_redaction():
    case=Case('DELETE',categories=['delete'],fixture_id='fixture-123').seal()
    p=Policy(['https://qa.example'],['read','delete'],['DELETE'],['another-fixture'])
    with pytest.raises(PermissionError):p.check_case(case)
    p.fixture_ids=['fixture-123'];p.check_case(case)
    with pytest.raises(PermissionError):p.check_origin('https://outside.example')
    text=redact('password=private-secret https://qa.example/login?jwt=secret-jwt')
    assert 'private-secret' not in text and 'secret-jwt' not in text

def test_all_origins_does_not_approve_side_effects():
    policy=Policy([],allow_all_origins=True)
    policy.check_origin('https://another.example:85/path')
    policy.check_origin('http://127.0.0.1:1234/api')
    with pytest.raises(PermissionError):policy.check_origin('file:///C:/private')
    with pytest.raises(PermissionError):policy.check_origin('https://user:password@example.test')
    with pytest.raises(PermissionError):policy.check_case(Case('DELETE',categories=['delete'],fixture_id='real'))

def test_crash_does_not_repeat_uncertain_write(tmp_path):
    store=Store(tmp_path/'crash.sqlite');case=Case('WRITE',categories=['create'],fixture_id='disposable').seal()
    run=store.create_run([case],{},{});store.begin(run,case);store.recover()
    assert store.next_case(run) is None
    assert store.results(run)[0]['status']=='NeedsReview'
    store.close()

def test_exported_playwright_flow_runs_without_model(tmp_path,monkeypatch):
    from local_qa import app
    from local_qa.replay import export_replays,replay
    monkeypatch.setattr(app,'PRIVATE',tmp_path)
    fixture=Fixture();upload=tmp_path/'uploads';upload.mkdir();(upload/'sample.txt').write_text('safe')
    cfg=fixture.config('local-test-double',upload,headless=True)
    store=Store(tmp_path/'agent.sqlite3');run=store.create_run(fixture.cases()[:1],cfg,{'kind':'fixture'})
    vault=MemoryVault({'fixture':{'username':fixture.username,'password':fixture.password}})
    try:
        asyncio.run(Supervisor(store,tmp_path/'evidence',vault,lambda c:DeterministicLocalModel(),fixtures=fixture).run(run))
        target=export_replays(store,run,tmp_path/'export')
        assert 'test_saved_flow_1' in target.read_text()
        asyncio.run(replay(run,'F01'))
    finally:store.close();fixture.close()

def test_xlsx_result_copy_preserves_other_tabs_formulas_and_source(tmp_path):
    import openpyxl
    source=tmp_path/'input.xlsx';book=openpyxl.Workbook();ws=book.active;ws.title='Test Cases'
    ws.append(['Scenario ID','Test Case ID','Test Steps','Expected Result','Status','Actual Result'])
    ws.append(['S','A','[]','Text "Ready" is visible.','Not Run',''])
    ws['D2'].font=openpyxl.styles.Font(bold=True)
    other=book.create_sheet('Scenarios');other['A1']='Original';other['B1']='=1+2';book.save(source)
    original=source.read_bytes();cases,meta=load_file(source)
    store=Store(tmp_path/'db.sqlite');run=store.create_run(cases,{},meta);a=store.begin(run,cases[0])
    store.commit(a,'Pass','Ready observed',{},[])
    copy=result_copy(store,run,tmp_path/'output');result=openpyxl.load_workbook(copy)
    assert result['Scenarios']['B1'].value=='=1+2'
    assert result['Test Cases']['D2'].font.bold
    assert result['Test Cases']['E2'].value=='Pass'
    assert source.read_bytes()==original
    result.close();store.close()

def test_google_writeback_targets_only_two_mapped_cells_and_detects_conflict():
    from local_qa.importer import normalize_grid
    grid=[['Test Case ID','Test Steps','Expected Result','Actual Result','Status'],['A','[]','Text "Ready" is visible.','','Not Run']]
    cases,meta=normalize_grid(grid);case=cases[0]
    class Response:
        def raise_for_status(self):pass
    class Session:
        def __init__(self):self.payload=None
        def post(self,url,json,timeout):self.payload=json;return Response()
    client=SheetsOAuth('unused','unused');client.session=Session()
    reads=[grid,[['Pass']],[['Ready observed']]]
    client.read=lambda *args:reads.pop(0)
    client.write_checked('fake-sheet',meta,case,{'status':'Pass','actual':'Ready observed'})
    ranges={x['range'] for x in client.session.payload['data']}
    assert ranges=={"'Test Cases'!E2","'Test Cases'!D2"}
    assert client.session.payload['valueInputOption']=='RAW'
    grid[1][2]='Changed requirement'
    client.read=lambda *args:grid
    with pytest.raises(Blocked):client.write_checked('fake-sheet',meta,case,{'status':'Pass','actual':'no'})

def test_full_fixture_queue_classification_resume_and_evidence(tmp_path):
    fixture=Fixture();uploads=tmp_path/'uploads';uploads.mkdir();(uploads/'sample.txt').write_text('safe fixture')
    cases=fixture.cases();cfg=fixture.config('local-test-double',uploads,headless=True)
    store=Store(tmp_path/'db.sqlite');run=store.create_run(cases,cfg,{'kind':'fixture'})
    vault=MemoryVault({'fixture':{'username':fixture.username,'password':fixture.password}})
    agent=Supervisor(store,tmp_path/'evidence',vault,lambda c:DeterministicLocalModel(),fixtures=fixture)
    try:
        asyncio.run(agent.run(run))
        result={r['case_id']:r for r in store.results(run)}
        expected={'F01':'Pass','F02':'Pass','F03':'Pass','F04':'Pass','F05':'Pass','F06':'Pass',
                  'F07':'Pass','F08':'Pass','F09':'Fail','F10':'Blocked','F11':'Pass','F12':'Blocked'}
        actual={id:r['status'] for id,r in result.items()}
        assert actual==expected,{id:(r['status'],r['actual']) for id,r in result.items()}
        count=store.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        asyncio.run(agent.run(run));assert store.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==count
        assert list((tmp_path/'evidence').rglob('observed.png'))
        assert list((tmp_path/'evidence').rglob('trace.zip'))
    finally:store.close();fixture.close()
