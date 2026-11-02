"""Deterministic Playwright replay of successful, source-covered flows."""
import asyncio,json
from pathlib import Path
from .models import Case,Policy,Budget,Blocked
from .store import Store
from .browser import BrowserOwner
from .auth import bootstrap
from .verifier import verify,explicit_criteria

async def replay(run_id,case_id):
    from .app import ROOT,PRIVATE,Vault
    from .fixture import Fixture
    store=Store(PRIVATE/'agent.sqlite3');owner=None;fixture=None;vault=Vault()
    try:
        run=store.run(run_id);cfg=run['config']
        row=next(r for r in store.results(run_id) if r['case_id']==case_id)
        if row['status']!='Pass':raise Blocked('Replay export requires an observed successful flow.')
        case=Case.from_dict(json.loads(row['data']))
        flow=store.flow(case.source_hash+'|'+cfg['start_url'])
        if not flow:raise Blocked('No verified flow is saved for this case.')
        if run['source'].get('kind')=='fixture':
            fixture=Fixture();vault.fixture=fixture
            cfg=fixture.config(cfg['ollama']['model'],cfg['policy']['upload_root'],headless=False)
        policy=Policy(**cfg['policy']);policy.check_case(case)
        auth_state=cfg.get('auth_state')
        owner=await BrowserOwner(policy,ROOT/'artifacts'/'agent'/run_id/('replay-'+case_id),Budget()).open(headless=cfg.get('headless',False),auth_state=auth_state if auth_state and Path(auth_state).is_file() else None)
        await bootstrap(owner,cfg,vault);await owner.evidence_start(owner.folder)
        if case.preconditions.strip():
            criteria=cfg.get('contracts',{}).get(case.source_hash,{}).get('preconditions')
            if not criteria:
                criteria,known=explicit_criteria(Case(case.case_id,expected=case.preconditions))
                if not known:raise Blocked('Replay preconditions need an explicit mapping.')
            status,proof=await verify(owner,criteria,True)
            if status!='Pass':raise Blocked('Replay preconditions were not satisfied.')
        for action in flow['actions']:await owner.do(case,action)
        status,proof=await verify(owner,flow['assertions'],True)
        assert status=='Pass',proof
    finally:
        if owner:await owner.evidence_end();await owner.close()
        if fixture:fixture.close()
        store.close()

def export_replays(store,run_id,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    text='"""Review before running: saved flows can repeat approved business side effects."""\nimport asyncio\nfrom local_qa.replay import replay\n'
    count=0
    for row in store.results(run_id):
        if row['status']!='Pass':continue
        case=Case.from_dict(json.loads(row['data']));run=store.run(run_id)
        if not store.flow(case.source_hash+'|'+run['config']['start_url']):continue
        count+=1
        text+='\ndef test_saved_flow_'+str(count)+'():\n    asyncio.run(replay('+repr(run_id)+','+repr(case.case_id)+'))\n'
    if not count:raise Blocked('No successful source-covered flows are available.')
    target=out/'test_verified_flows.py';target.write_text(text,encoding='utf-8')
    return target
