"""Integration verification against our disposable fixture, never a user QA site."""
import asyncio
import json
import threading
from http.server import ThreadingHTTPServer
from demo.server import Handler
import qa


def test_reviewed_flow_generation_and_real_playwright_replay(tmp_path, monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    c = {'base_url': f'http://127.0.0.1:{server.server_port}', 'approved_read_paths': ['/help'],
         'model': 'qwen3:4b-instruct', 'headless': True}
    row = {'Case ID': 'PIPELINE-FIXTURE', 'Instructions': 'Open help and verify heading',
           'Start Path': '/help', 'Expected Role': 'heading', 'Expected Name': 'Help center',
           'Read Only Approved': 'yes'}
    root = tmp_path / 'artifacts' / 'fixture'
    folder = root / row['Case ID']
    # Synthetic approval exists only in pytest's temporary folder. This does not
    # approve any demo/QA exploration or claim a human reviewed the user's cases.
    r = {'status': 'Pass', 'signature': qa.case_signature(c, row),
         'steps': [{'action': 'goto', 'path': '/help'}]}
    qa.save(folder / 'result.json', r)
    qa.save(folder / 'review.json', {'approved': True, 'result_hash': qa.digest(r)})
    monkeypatch.setattr(qa, 'ROOT', tmp_path)
    monkeypatch.setattr(qa, 'ART', tmp_path / 'artifacts')
    monkeypatch.setattr(qa, 'PRIVATE', tmp_path / '.private')
    monkeypatch.setattr(qa, 'config', lambda: c)
    try:
        qa.generate(c, [row], root)
        test_file = tmp_path / 'tests' / 'generated' / 'fixture' / 'test_PIPELINE-FIXTURE.py'
        namespace = {}
        exec(compile(test_file.read_text(), str(test_file), 'exec'), namespace)
        namespace['test_PIPELINE_FIXTURE']()
        replay = json.loads((folder / 'replay.json').read_text())
        assert replay['status'] == 'Pass'
        assert (folder / 'replay.png').stat().st_size > 0
        assert (folder / 'replay-trace.zip').stat().st_size > 0
        # A wrong expectation must actually fail, not produce a green report.
        row['Expected Name'] = 'This heading does not exist'
        r['signature'] = qa.case_signature(c, row)
        qa.save(folder / 'result.json', r)
        qa.save(folder / 'review.json', {'approved': True, 'result_hash': qa.digest(r)})
        import pytest
        with pytest.raises(AssertionError):
            asyncio.run(qa.replay_case(row, ['/help'], 'fixture', qa.digest(r)))
        assert json.loads((folder / 'replay.json').read_text())['status'] == 'Fail'
    finally:
        server.shutdown()
        server.server_close()
