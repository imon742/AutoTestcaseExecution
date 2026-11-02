"""Explicit real-local-model acceptance on a disposable loopback fixture."""
import asyncio,json,sys
from pathlib import Path
from local_qa.fixture import Fixture,MemoryVault
from local_qa.store import Store
from local_qa.supervisor import Supervisor
from local_qa.ollama import Ollama
from local_qa.writers import export_results

async def main(model,ids=None):
    # Fail before creating a fixture/queue when Ollama is stopped or unavailable.
    Ollama(model,timeout=5).validate_model()
    root=Path(__file__).resolve().parents[2]/'artifacts'/'agent-acceptance'
    root.mkdir(parents=True,exist_ok=True)
    fixture=Fixture();upload=root/'fixture-files';upload.mkdir(exist_ok=True);(upload/'sample.txt').write_text('local fixture')
    cfg=fixture.config(model,upload,headless=True);cfg['ollama']['context']=4096;cfg['ollama']['timeout']=90
    cfg['budget']['case_seconds']=240
    store=Store(root/'acceptance.sqlite3');cases=fixture.cases()[:6]
    if ids:cases=[c for c in cases if c.case_id in ids.split(',')]
    run=store.create_run(cases,cfg,{'kind':'fixture','note':'Real local model; synthetic data only.'})
    vault=MemoryVault({'fixture':{'username':fixture.username,'password':fixture.password}})
    agent=Supervisor(store,root,vault,fixtures=fixture)
    print('Running',len(cases),'real-model cases with',model,'run',run,flush=True)
    task=asyncio.create_task(agent.run(run));seen=set()
    try:
        while not task.done():
            await asyncio.sleep(2)
            for r in store.results(run):
                if r['finished'] and r['case_id'] not in seen:
                    print(r['case_id'],r['status'],r['actual'][:400],flush=True);seen.add(r['case_id'])
        await task
        report=export_results(store,run,root/run)
        result={'model':model,'run_id':run,'results':report}
        (root/(model.replace(':','-').replace('/','-')+'-'+run[:8]+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        assert all(r['Status']=='Pass' for r in report),[(r['Case ID'],r['Status'],r['Actual Result']) for r in report]
        print(len(cases),'mixed-action cases passed with',model,flush=True)
    finally:store.close();fixture.close()

if __name__=='__main__':asyncio.run(main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None))
