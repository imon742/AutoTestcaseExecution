import asyncio
from local_qa.browser import BrowserOwner
from local_qa.models import Policy,Budget

def test_approved_websocket_reaches_server(tmp_path):
    async def run():
        import websockets
        async def echo(ws):
            async for message in ws:await ws.send(message)
        async with websockets.serve(echo,'127.0.0.1',0) as server:
            port=server.sockets[0].getsockname()[1]
            owner=await BrowserOwner(Policy([f'http://127.0.0.1:{port}']),tmp_path,Budget()).open(headless=True)
            try:
                await owner.evidence_start(tmp_path)
                value=await asyncio.wait_for(owner.page.evaluate('''url=>new Promise((resolve,reject)=>{
                  const ws=new WebSocket(url);ws.onopen=()=>ws.send('fixture-echo');
                  ws.onmessage=e=>{resolve(e.data);ws.close()};ws.onerror=()=>reject(new Error('socket failed'));
                })''',f'ws://127.0.0.1:{port}'),10)
                assert value=='fixture-echo'
                await owner.evidence_end()
            finally:await owner.close()
    asyncio.run(run())
