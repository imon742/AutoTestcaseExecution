import asyncio
import copy
import io
import json
import threading
import zipfile
from http.server import ThreadingHTTPServer
from xml.etree import ElementTree as ET
import pytest
import case_import as imports
import dashboard as app
import assistant_engine as engine
import qa


def workbook_bytes():
    out=io.BytesIO()
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    root=ET.Element('worksheet',xmlns=ns);data=ET.SubElement(root,'sheetData')
    rows=[['QA cases'],['Case ID','Title','Steps','Expected','Status'],
          ['XLSX-1','Read heading','Inspect Help center heading.','Help center heading visible.','Pass']]
    for n,values in enumerate(rows,1):
        row=ET.SubElement(data,'row',r=str(n))
        for i,value in enumerate(values):
            c=ET.SubElement(row,'c',r=chr(65+i)+str(n),t='inlineStr')
            ET.SubElement(ET.SubElement(c,'is'),'t').text=value
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="'+ns+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Test Cases" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',ET.tostring(root))
    return out.getvalue()


def test_excel_import_finds_named_tab_and_headers_without_google():
    rows=imports.excel_records(workbook_bytes())
    cases=engine.normalize(rows)
    assert cases[0]['id']=='XLSX-1'
    assert cases[0]['steps']=='Inspect Help center heading.'
    assert cases[0]['source_status']=='Pass'
    assert 'status' not in cases[0]


def test_public_import_is_anonymous_and_targets_tab_not_stale_gid(monkeypatch):
    requested=[]
    class Response(io.BytesIO):
        pass
    class Opener:
        def open(self,request,timeout):
            requested.append(request)
            return Response(b'Case ID,Steps,Expected\nPUBLIC-1,Inspect heading,Heading visible\n')
    monkeypatch.setattr(imports.urllib.request,'build_opener',lambda *args:Opener())
    records=imports.public_sheet('https://docs.google.com/spreadsheets/d/example/edit?gid=0','Test Cases',81082)
    assert records[0]['Test Case ID']=='PUBLIC-1'
    assert 'sheet=Test+Cases' in requested[0].full_url
    assert requested[0].get_header('Cookie') is None
    assert requested[0].get_header('Authorization') is None
    with pytest.raises(ValueError):imports.public_sheet('http://127.0.0.1/private')
    with pytest.raises(ValueError):imports.csv_records(b'<html>Sign in</html>')


def test_one_click_run_executes_assertions_without_manual_plan_gate(tmp_path,monkeypatch):
    from demo.server import Handler
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    c={'base_url':f'http://127.0.0.1:{server.server_port}','approved_read_paths':['/help'],
       'entry_path':'/help','model':engine.MODEL,'headless':True}
    safe={'id':'ONE-CLICK','title':'Heading','steps':'Inspect Help center heading.',
          'expected':'Help center heading visible.','precondition':'Synthetic fixture only.'}
    unsafe={**safe,'id':'DO-NOT-DELETE','steps':'Click Delete and confirm.'}
    data=copy.deepcopy(app.DEFAULT)
    data.update(cases=[safe,unsafe],selected=[safe['id'],unsafe['id']],qa_confirmed=True,
                busy=False,job='',paused=False,error='',completed=0)
    monkeypatch.setattr(app,'DATA',data)
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'STATE',tmp_path/'.private'/'dashboard.json')
    monkeypatch.setattr(app,'settings',lambda:c)
    prepared=[]
    async def prepare(config,case,f):
        prepared.append(case['id'])
        p={'summary':'Synthetic read-only check','criteria':['Heading visible'],'unverifiable':[],
           'actions':[{'kind':'role','criterion':'Heading visible','role':'heading','name':'Help center'}]}
        qa.save(f/'plan.json',{'case_hash':qa.digest(case),'config_hash':qa.digest(config),'plan':p})
        return p
    real_execute=engine.execute
    async def execute(config,case,f):
        # Real Playwright browser/assertion; deterministic test bypasses only the
        # model wrapper, which has a separate real-Ollama smoke verification.
        r=await real_execute(config,case,f,replay=True)
        qa.save(f/'result.json',r)
        return r
    monkeypatch.setattr(engine,'prepare',prepare)
    monkeypatch.setattr(engine,'execute',execute)
    try:
        app.batch('run')
        f=app.folder(safe)
        assert app.read_json(f/'result.json')['status']=='Pass'
        assert not (f/'plan-review.json').exists()
        assert (f/'execution-authorization.json').exists()
        assert (f/'replay-final.png').exists()
        assert app.read_json(app.folder(unsafe)/'result.json')['status']=='Blocked'
        assert prepared==[safe['id']]
        # A second click resumes without re-running a completed Pass.
        app.DATA['selected']=[safe['id']]
        app.batch('run')
        assert prepared==[safe['id']]
    finally:
        server.shutdown();server.server_close()
