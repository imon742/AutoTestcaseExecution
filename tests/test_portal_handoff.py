import asyncio
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import qa


def test_portal_handoff_preserves_popup_and_both_origin_sessions(tmp_path,monkeypatch):
    from playwright.async_api import async_playwright,expect
    origins={}
    class CM(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path=='/':
                self.send_response(302);self.send_header('Location','/login?ticket=synthetic-fixture');self.end_headers();return
            body=('''<h1>Runtime error: direct visit has no handoff</h1><script>
              addEventListener('message',e=>{if(e.origin===PORTAL && e.data==='fixture-ready'
                && sessionStorage.cmFixture==='local'){history.replaceState(null,'','/');document.querySelector('h1').textContent='Organizations';}});
              if(window.opener){new WebSocket('ws://127.0.0.1:3000/ws');window.opener.postMessage('fixture-request',PORTAL);}
              </script>'''.replace('PORTAL',repr(origins['portal']))).encode()
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
    class Portal(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            body=('''<button onclick="window.open(CMURL,'cm-fixture')">Admin Settings</button><script>
              addEventListener('message',e=>{if(e.origin===CMURL && e.data==='fixture-request'
                && sessionStorage.portalFixture==='local')e.source.postMessage('fixture-ready',CMURL);});
              </script>'''.replace('CMURL',repr(origins['cm']))).encode()
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
    cm=ThreadingHTTPServer(('127.0.0.1',0),CM)
    portal=ThreadingHTTPServer(('127.0.0.1',0),Portal)
    origins.update(cm=f'http://127.0.0.1:{cm.server_port}',portal=f'http://127.0.0.1:{portal.server_port}')
    for server in (cm,portal):threading.Thread(target=server.serve_forever,daemon=True).start()
    monkeypatch.setattr(qa,'PRIVATE',tmp_path)
    c={'base_url':origins['cm'],'login_url':origins['portal'],'bootstrap_label':'Admin Settings',
       'entry_path':'/','approved_read_paths':['/'],'read_api_origins':[origins['portal']]}
    qa.save(tmp_path/(qa.digest(c['base_url'])[:16]+'-session-origins.json'),
        {origins['portal']:{'portalFixture':'local'},origins['cm']:{'cmFixture':'local'},
         'https://unapproved.example':{'neverRestore':'foreign'}})
    async def exercise():
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            context=await qa.context_options(browser,c)
            blocked=[]
            await qa.guard(context,c,blocked)
            # A plain manual context demonstrates the direct-visit problem;
            # it is not subject to the trial's intentional path restrictions.
            manual=await browser.new_context()
            direct=await manual.new_page()
            await direct.goto(origins['cm'])
            await expect(direct.get_by_role('heading')).to_have_text('Runtime error: direct visit has no handoff')
            await manual.close()
            # The helper must ignore the older failed CM tab and retain the
            # actual popup/opener created by the observed Admin Settings control.
            page,_=await qa.open_start_page(context,c)
            await expect(page.get_by_role('heading',name='Organizations',exact=True)).to_be_visible()
            assert len(context.pages)==2
            assert await page.evaluate('window.opener !== null')
            # Playwright may instrument the constructor internally. The required
            # behavior is successful construction without our synchronous error.
            assert await page.evaluate("(()=>{try{new WebSocket('ws://127.0.0.1:3000/ws');return true;}catch(e){return false;}})()")
            assert '_bootstrap_active' not in c
            assert not [x for x in blocked if x.get('essential',True)]
            assert any(x['method']=='WEBSOCKET' for x in blocked)
            await browser.close()
    try:asyncio.run(exercise())
    finally:
        for server in (cm,portal):server.shutdown();server.server_close()
