import asyncio
from local_qa.models import Case
from local_qa.store import Store
from local_qa.fixture import Fixture,MemoryVault
from local_qa.supervisor import Supervisor
from .test_core import DeterministicLocalModel

def test_unproven_precondition_cannot_pass(tmp_path):
    fixture=Fixture();uploads=tmp_path/'uploads';uploads.mkdir()
    cfg=fixture.config('local-test-double',uploads,headless=True)
    original=fixture.cases()[0];original.preconditions='An approved backend entitlement exists.';original.seal()
    store=Store(tmp_path/'queue.sqlite3');run=store.create_run([original],cfg,{'kind':'fixture'})
    vault=MemoryVault({'fixture':{'username':fixture.username,'password':fixture.password}})
    try:
        asyncio.run(Supervisor(store,tmp_path/'evidence',vault,lambda c:DeterministicLocalModel(),fixtures=fixture).run(run))
        assert store.results(run)[0]['status']=='NeedsReview'
        import json
        assert json.loads(store.results(run)[0]['details'])['preconditions'][0]['status']=='Unverified'
    finally:store.close();fixture.close()
