import asyncio
import json
import pytest
import qa


def test_urls_require_exact_approval_and_same_origin():
    c = {'base_url': 'https://qa.example', 'approved_read_paths': ['/help', '//evil.example', '/\\evil.example']}
    assert qa.safe_url(c, '/help') == 'https://qa.example/help'
    for bad in ['https://evil.example', '//evil.example', '/\\evil.example', '/delete', '/help?delete=yes', '/help#other']:
        with pytest.raises(ValueError):
            qa.safe_url(c, bad)


def test_csv_duplicate_ids_are_rejected(tmp_path):
    p = tmp_path / 'cases.csv'
    header = 'Case ID,Instructions,Start Path,Expected Role,Expected Name,Read Only Approved\n'
    p.write_text(header + 'A,View,/,heading,Home,yes\nA,View,/,heading,Home,yes\n')
    with pytest.raises(ValueError, match='unique'):
        qa.load_cases(p)


def test_changed_results_invalidate_review(tmp_path):
    folder = tmp_path / 'A'
    folder.mkdir()
    result = {'status': 'Pass', 'actual': 'Observed Home'}
    qa.save(folder / 'result.json', result)
    qa.save(folder / 'review.json', {'approved': True, 'result_hash': qa.digest(result)})
    assert qa.approved_result(tmp_path, {'Case ID': 'A'}) == result
    result['actual'] = 'Changed after approval'
    qa.save(folder / 'result.json', result)
    assert qa.approved_result(tmp_path, {'Case ID': 'A'}) is None


def test_resume_skips_completed_and_retries_unfinished(tmp_path, monkeypatch):
    rows = [{'Case ID': x} for x in ['A', 'B', 'C']]
    qa.save(tmp_path / 'A' / 'result.json', {'finished': 'yesterday'})
    qa.save(tmp_path / 'B' / 'result.json', {'status': 'Blocked', 'interrupted': True})
    called = []
    async def fake(c, row, folder):
        called.append(row['Case ID'])
    monkeypatch.setattr(qa, 'explore_case', fake)
    monkeypatch.setattr(qa, 'report', lambda *args: None)
    asyncio.run(qa.explore({}, rows, tmp_path, 1))
    assert called == ['B']
    assert json.loads((tmp_path / 'checkpoint.json').read_text())['last_completed_case'] == 'B'


def test_guard_blocks_mutations_external_origins_and_unapproved_navigation():
    handlers = []
    class Context:
        async def route(self, pattern, handler):
            handlers.append(handler)
        async def add_init_script(self, script):
            pass
    class Request:
        def __init__(self, method, url, nav):
            self.method, self.url, self.nav = method, url, nav
        def is_navigation_request(self):
            return self.nav
    class Route:
        def __init__(self, request):
            self.request, self.outcome = request, None
        async def abort(self):
            self.outcome = 'blocked'
        async def continue_(self):
            self.outcome = 'allowed'
    async def exercise():
        blocked = []
        await qa.guard(Context(), {'base_url': 'https://qa.example', 'approved_read_paths': ['/help']}, blocked)
        cases = [('POST', 'https://qa.example/help', False, 'blocked'),
                 ('GET', 'https://evil.example/pixel', False, 'blocked'),
                 ('GET', 'https://qa.example/delete', True, 'blocked'),
                 ('GET', 'https://qa.example/help', True, 'allowed')]
        for method, url, nav, expected in cases:
            route = Route(Request(method, url, nav))
            await handlers[0](route)
            assert route.outcome == expected
        assert len(blocked) == 3
    asyncio.run(exercise())


def test_explicit_backend_rules_allow_reads_and_session_validation_only():
    handlers=[]
    class Context:
        async def route(self,pattern,handler):handlers.append(handler)
        async def add_init_script(self,script):pass
    class Request:
        def __init__(self,method,url,nav=False,kind='fetch'):
            self.method,self.url,self.nav,self.resource_type=method,url,nav,kind
        def is_navigation_request(self):return self.nav
    class Route:
        def __init__(self,request):self.request=request;self.allowed=None
        async def abort(self):self.allowed=False
        async def continue_(self):self.allowed=True
    async def exercise():
        blocked=[]
        c={'base_url':'https://qa.example','approved_read_paths':['/home'],
           'read_api_origins':['https://qa.example:8092'],
           'session_auth_urls':['https://qa.example:8092/services/dashboard/api/authenticate'],
           'optional_network_hosts':['analytics.example']}
        await qa.guard(Context(),c,blocked)
        cases=[('GET','https://qa.example:8092/services/user',False,'fetch',True),
               ('POST','https://qa.example:8092/services/dashboard/api/authenticate',False,'xhr',True),
               ('POST','https://qa.example:8092/services/dashboard/api/authenticate',True,'document',False),
               ('POST','https://qa.example:8092/services/organization/delete',False,'fetch',False),
               ('DELETE','https://qa.example:8092/services/user',False,'fetch',False),
               ('GET','https://qa.example:8092/home',True,'document',False),
               ('POST','https://analytics.example/track',False,'fetch',False)]
        for method,url,nav,kind,expected in cases:
            r=Route(Request(method,url,nav,kind));await handlers[0](r);assert r.allowed is expected
        assert blocked[-1]['essential'] is False
        assert all(b['essential'] for b in blocked[:-1])
    asyncio.run(exercise())
