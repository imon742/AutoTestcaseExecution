import copy
import asyncio
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import pytest
import legacy_dashboard as app
import assistant_engine as engine
import qa


def test_plan_validation_rejects_unapproved_actions_and_missing_coverage():
    c={'base_url':'https://qa.example','approved_read_paths':['/']}
    p={'actions':[{'kind':'navigate','path':'/delete','criterion':'C'}],'criteria':['C'],'unverifiable':[]}
    with pytest.raises(ValueError):engine.validate_plan(p,c)
    p['actions']=[{'kind':'shell','criterion':'C'}]
    with pytest.raises(ValueError):engine.validate_plan(p,c)
    p['actions']=[]
    with pytest.raises(ValueError):engine.validate_plan(p,c)


def test_mutating_steps_are_not_approved_by_presence_of_readonly_text():
    case={'steps':'1. Inspect the Create button.\n2. Click Delete and confirm.','expected':'Record removed.'}
    assert engine.risk_reason(case)
    assert not engine.risk_reason({'steps':'1. Inspect the Create button.','expected':'Button visible.'})


def test_import_does_not_reuse_historical_pass():
    records=[{'Test Case ID':'A','Test Steps':'Inspect heading','Expected Result':'Heading visible','Status':'Pass','Actual Result':'old run'}]
    case=engine.normalize(records)[0]
    assert case['source_status']=='Pass'
    assert 'status' not in case


def test_chat_transport_is_optional_only_for_organization_checks():
    c={'approved_read_paths':['/']}
    case={'title':'Organization directory','steps':'Inspect organization rows','expected':'Organization heading visible'}
    assert engine.scoped_network(c,case)['optional_network_suffixes']==['.firebasedatabase.app']
    case['expected']='Organization chat conversation delivers messages'
    assert 'optional_network_suffixes' not in engine.scoped_network(c,case)


def test_preparation_errors_are_visible_without_claiming_execution(tmp_path):
    qa.save(tmp_path/'preparation-error.json',{'error':'Required backend blocked'})
    r=app.displayed_result(tmp_path)
    assert r['status']=='Blocked'
    assert 'backend blocked' in r['actual']
    assert not (tmp_path/'result.json').exists()
    assert engine.essential_blocks([{'essential':False},{'essential':True}])==[{'essential':True}]


def test_dashboard_generated_pytest_runs_and_rejects_stale_approval(tmp_path,monkeypatch):
    import subprocess,sys
    from demo.server import Handler
    actual_root=Path(app.__file__).resolve().parent
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    c={'base_url':f'http://127.0.0.1:{server.server_port}','approved_read_paths':['/help'],
       'entry_path':'/help','model':engine.MODEL,'headless':True}
    case={'id':'GENERATED-SMOKE','title':'Heading','steps':'Inspect Help center heading.',
          'expected':'Help center heading visible.','precondition':'Synthetic fixture only.'}
    data=copy.deepcopy(app.DEFAULT)
    data.update(cases=[case],job='',busy=False,paused=False,error='',completed=0)
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'STATE',tmp_path/'.private'/'dashboard.json')
    monkeypatch.setattr(app,'DATA',data)
    monkeypatch.setattr(app,'settings',lambda:c)
    f=app.folder(case)
    p={'case_hash':qa.digest(case),'config_hash':qa.digest(c),'plan':{
       'summary':'Synthetic heading check','criteria':['Heading visible'],'unverifiable':[],
       'actions':[{'kind':'role','criterion':'Heading visible','role':'heading','name':'Help center'}]}}
    qa.save(f/'plan.json',p)
    qa.save(f/'plan-review.json',{'plan_hash':qa.digest(p),'scope':'synthetic test only'})
    try:
        actual=asyncio.run(engine.execute(c,case,f,replay=True))
        assert actual['status']=='Pass'
        qa.save(f/'result.json',actual)
        app.approve_flow(case['id'])
        generated=next((tmp_path/'tests'/'assistant_generated').rglob('test_GENERATED-SMOKE.py'))
        proc=subprocess.run([sys.executable,'-m','pytest','-c',str(actual_root/'pytest.ini'),'--confcutdir',str(generated.parent),str(generated),'-q'],cwd=actual_root,capture_output=True,text=True)
        assert proc.returncode==0,proc.stdout+proc.stderr
        actual['actual']='Changed after review'
        qa.save(f/'result.json',actual)
        proc=subprocess.run([sys.executable,'-m','pytest','-c',str(actual_root/'pytest.ini'),'--confcutdir',str(generated.parent),str(generated),'-q'],cwd=actual_root,capture_output=True,text=True)
        assert proc.returncode!=0
        assert 'stale' in proc.stdout.lower()
    finally:
        server.shutdown();server.server_close()


def test_dashboard_real_browser_and_request_boundaries(tmp_path,monkeypatch):
    from playwright.sync_api import sync_playwright,expect
    actual_root=Path(app.__file__).resolve().parent
    (tmp_path/'dashboard.html').write_bytes((actual_root/'dashboard.html').read_bytes())
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'STATE',tmp_path/'.private'/'dashboard.json')
    data=copy.deepcopy(app.DEFAULT)
    data.update(job='',busy=False,paused=False,error='',completed=0)
    monkeypatch.setattr(app,'DATA',data)
    server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    monkeypatch.setattr(app,'PORT',server.server_port)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base+'/api/state')
        assert e.value.code==403
        req=urllib.request.Request(base+'/api/action',data=b'{"action":"pause"}',
              headers={'X-QA-Token':app.TOKEN,'Content-Type':'application/json','Origin':'https://evil.example'})
        with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        assert e.value.code==403
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1600,'height':1100})
            page.goto(base+'/#'+app.TOKEN)
            expect(page.get_by_role('heading',name='Local QA Assistant',exact=True)).to_be_visible()
            page.locator('details').first.locator('summary').click()
            raw='Test Case ID,Test Case,Test Steps,Expected Result,Status,Actual Result\nUI-001,View local heading,Inspect heading,Heading visible,Pass,Historical result only\n'
            page.locator('#csv').set_input_files({'name':'test-cases.csv','mimeType':'text/csv','buffer':raw.encode()})
            expect(page.locator('#source')).to_contain_text('1 cases')
            expect(page.locator('#cases')).to_contain_text('Not Run')
            page.get_by_role('button',name='UI-001 View local heading').click()
            expect(page.locator('#caseDetails')).to_contain_text('Historical result only')
            # No Sheet or QA website was contacted by this UI test.
            page.screenshot(path=str(actual_root/'artifacts'/'dashboard-preview.png'),full_page=True)
            request=page.request.get(base+'/api/file?path=.private/dashboard.json',headers={'X-QA-Token':app.TOKEN})
            assert request.status==400
            browser.close()
    finally:
        server.shutdown();server.server_close()
