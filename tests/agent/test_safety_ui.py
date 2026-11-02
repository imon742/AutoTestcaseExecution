import asyncio,json,threading,urllib.request,urllib.error,zipfile
from pathlib import Path
import pytest
from local_qa.models import Case,Blocked
from local_qa.ollama import Ollama
from local_qa.store import Store
from local_qa.fixture import Fixture,MemoryVault
from local_qa.supervisor import Supervisor
from tests.agent.test_core import DeterministicLocalModel

def test_pending_writeback_does_not_rerun_browser_case(tmp_path):
    s=Store(tmp_path/'db');c=Case('A').seal();run=s.create_run([c],{'policy':{'allow_writeback':True}},{'kind':'public_sheet'})
    a=s.begin(run,c);s.commit(a,'Blocked','No authoritative data',{},[],writeback=True)
    jobs=s.pending_writebacks(run);assert len(jobs)==1
    s.writeback_state(jobs[0]['id'],'Pending','Network down')
    assert s.next_case(run) is None
    assert s.results(run)[0]['status']=='Blocked'
    s.close()

def test_cloud_and_uninstalled_models_cannot_run():
    m=Ollama('model-cloud')
    m.request=lambda path,payload=None:({'models':[{'name':'model-cloud'}]} if path=='/api/tags' else {'remote_host':'remote.example'})
    with pytest.raises(Blocked):m.validate_model()
    m=Ollama('missing');m.request=lambda *args:{'models':[]}
    with pytest.raises(Blocked):m.validate_model()

def test_unstructured_steps_never_get_automatic_pass(tmp_path):
    fixture=Fixture();cfg=fixture.config('test',tmp_path,headless=True)
    c=Case('UNMAPPED',steps='Please do a vaguely specified workflow.',expected='Text "Dashboard" is visible.').seal()
    cfg['policy']['categories']=['read'];cfg['policy']['write_case_ids']=[]
    s=Store(tmp_path/'db');run=s.create_run([c],cfg,{'kind':'fixture'})
    vault=MemoryVault({'fixture':{'username':fixture.username,'password':fixture.password}})
    try:
        asyncio.run(Supervisor(s,tmp_path/'evidence',vault,lambda c:DeterministicLocalModel(),fixtures=fixture).run(run))
        assert s.results(run)[0]['status']=='NeedsReview'
    finally:s.close();fixture.close()

def test_source_only_archive_excludes_runtime_inputs_and_secrets(tmp_path):
    import safe_export
    package=safe_export.export(tmp_path/'source.zip')
    with zipfile.ZipFile(package) as z:
        names=z.namelist()
        assert any(n.endswith('local_qa/supervisor.py') for n in names)
        assert not any('/.private/' in n or '/.venv/' in n or '/artifacts/' in n or n.endswith('.sqlite3') for n in names)
        assert not any('legacy_dashboard' in n or n.endswith('qa.py') and '/local_qa/' not in n for n in names)

def test_new_dashboard_controls_and_origin_boundary(tmp_path,monkeypatch):
    from http.server import ThreadingHTTPServer
    from playwright.sync_api import sync_playwright,expect
    import local_qa.app as module
    monkeypatch.setattr(module,'PRIVATE',tmp_path/'private')
    app=module.App();app.models=lambda:['local-model-A','local-model-B']
    server=ThreadingHTTPServer(('127.0.0.1',0),module.make_handler(app));monkeypatch.setattr(module,'PORT',server.server_port)
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(base+'/api/state')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1100})
            page.goto(base+'/#'+module.TOKEN)
            expect(page.get_by_role('heading',name='Local Ollama QA Agent')).to_be_visible()
            expect(page.locator('#model')).to_contain_text('local-model-B')
            expect(page.get_by_label('Allow all origins',exact=True)).to_be_checked()
            page.locator('#model').select_option('local-model-A')
            page.once('dialog',lambda d:d.accept())
            page.get_by_role('button',name='Load isolated local acceptance fixture').click()
            expect(page.locator('#count')).to_have_text('(12)')
            expect(page.locator('#scope')).to_have_value('non_pass')
            expect(page.get_by_role('button',name='Run matching cases')).to_be_visible()
            page.screenshot(path=str(Path(__file__).resolve().parents[2]/'artifacts'/'agent-dashboard.png'),full_page=True)
            browser.close()
    finally:
        if app.fixture:app.fixture.close()
        server.shutdown();server.server_close();app.store.close()
