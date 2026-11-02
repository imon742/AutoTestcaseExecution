import asyncio

import pytest

from local_qa.auth import bootstrap
from local_qa.browser import BrowserOwner
from local_qa.fixture import Fixture, MemoryVault
from local_qa.importer import load_oauth
from local_qa.models import Budget, Case, Policy
from local_qa.models import fingerprint
from local_qa.app import App


def test_fixture_approval_is_bound_to_its_origin():
    case = Case('MUTATE', categories=['create'], fixture_id='fixture').seal()
    policy = Policy(
        origins=['https://qa-one.example', 'https://qa-two.example'],
        categories=['create'], write_case_ids=['MUTATE'],
        fixture_ids={'fixture': 'https://qa-one.example'},
    )
    policy.check_case(case)
    policy.check_fixture_origin(case, 'https://qa-one.example/records')
    with pytest.raises(PermissionError, match='current origin'):
        policy.check_fixture_origin(case, 'https://qa-two.example/records')


def test_google_import_quotes_a_tab_name():
    seen = []
    class Client:
        def read(self, spreadsheet_id, cell_range):
            seen.append((spreadsheet_id, cell_range))
            return [['Test Case ID', 'Test Steps', 'Expected Result'], ['A', 'Inspect', 'Text "A" is visible.']]
    cases, _ = load_oauth(Client(), 'workbook-id', 'Test Cases')
    assert cases[0].case_id == 'A'
    assert seen == [('workbook-id', "'Test Cases'!A1:GR30000")]


def test_read_only_navigation_blocks_dangerous_links_and_mutating_requests(tmp_path):
    async def exercise():
        fixture = Fixture()
        owner = None
        try:
            cfg = fixture.config('', tmp_path, headless=True)
            owner = await BrowserOwner(Policy(**cfg['policy']), tmp_path, Budget()).open(headless=True)
            await bootstrap(owner, cfg, MemoryVault({'fixture': {'username': fixture.username, 'password': fixture.password}}))
            await owner.page.evaluate("document.body.insertAdjacentHTML('beforeend', '<a href=\"/deactivate\">Deactivate account</a><a href=\"/approve\">Approve request</a>')")
            case = Case('READ', categories=['read']).seal()
            for label in ('Deactivate account', 'Approve request'):
                with pytest.raises(PermissionError, match='Read-only links'):
                    await owner.do(case, {'kind':'click','locator':{'by':'role','role':'link','name':label},'value':'','category':'read','reason':'test'})
            await owner.do(case, {'kind':'click','locator':{'by':'role','role':'link','name':'Records'},'value':'','category':'read','reason':'test'})
            assert owner.page.url.endswith('/records')
            with pytest.raises(Exception):
                await owner.page.evaluate("fetch('/delete', {method: 'POST'})")
            assert any(x.get('blocked') == 'read-only method' for x in owner.requests)
        finally:
            if owner:
                await owner.close()
            fixture.close()
    asyncio.run(exercise())


def test_policy_defaults_to_no_cross_origin_opt_in():
    assert Policy(origins=['https://qa.example']).allow_all_origins is False


def test_chat_rejects_secret_like_text_and_reads_state_locally(tmp_path, monkeypatch):
    import local_qa.app as app_module
    monkeypatch.setattr(app_module, 'PRIVATE', tmp_path / 'private')
    instance = App()
    try:
        reply = instance.chat('my password is do-not-store-this')
        assert reply['intent'] == 'reject_secret'
        assert 'do-not-store-this' not in str(instance.store.chat_history())
        reply = instance.chat('what is running')
        assert reply['intent'] == 'show_result'
        assert 'No run is selected' in reply['reply']
    finally:
        instance.store.close()


def test_mutating_case_requires_hash_bound_local_approval(tmp_path, monkeypatch):
    import local_qa.app as app_module
    monkeypatch.setattr(app_module, 'PRIVATE', tmp_path / 'private')
    instance = App()
    try:
        case = Case('CREATE-1', categories=['create'], fixture_id='fixture-a').seal()
        instance.cases = [case]
        instance.config.update({'start_url':'https://qa.example/', 'ollama':{'model':'local-model'}})
        instance.config['policy'] = {'origins':['https://qa.example'], 'categories':['read','create'], 'write_case_ids':['CREATE-1'], 'fixture_ids':{'fixture-a':'https://qa.example'}, 'allow_all_origins':False}
        with pytest.raises(ValueError, match='exact stored approval'):
            instance.run('all', '', [])
        digest = fingerprint({'source_hash':case.source_hash, 'fixture_id':'fixture-a', 'category':'create'})
        instance.store.approve('CREATE-1', 'fixture-a', 'create', digest)
        assert instance.store.approval('CREATE-1', 'fixture-a', 'create', digest)
    finally:
        instance.store.close()
