"""Opt-in real Ollama smoke check against a disposable local fixture only."""
import asyncio
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from demo.server import Handler
import assistant_engine as engine
import qa


async def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    c={'base_url':f'http://127.0.0.1:{server.server_port}','approved_read_paths':['/help'],'entry_path':'/help',
       'model':engine.MODEL,'headless':True}
    case={'id':'LOCAL-MODEL-SMOKE','title':'Check local Help heading','steps':'Inspect the Help center heading.',
          'expected':'The heading Help center is visible.','precondition':'Disposable local fixture only.'}
    f=Path(__file__).resolve().parents[1]/'artifacts'/'assistant-smoke'
    try:
        plan=await engine.prepare(c,case,f)
        print('Local model plan:',json.dumps(plan),flush=True)
        assert not plan['unverifiable'],plan
        saved=json.loads((f/'plan.json').read_text(encoding='utf-8'))
        qa.save(f/'plan-review.json',{'plan_hash':qa.digest(saved),'reviewed_at':qa.now(),'scope':'synthetic smoke fixture only'})
        r=await engine.execute(c,case,f)
        print('Browser-use execution:',r['status'],r['actual'],flush=True)
        assert r['status']=='Pass',r
        replay=await engine.execute(c,case,f,replay=True)
        print('Playwright replay:',replay['status'],flush=True)
        assert replay['status']=='Pass',replay
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':
    asyncio.run(main())
