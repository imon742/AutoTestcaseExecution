"""Start the local fixture, run a demo command, and stop only our fixture process."""
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import qa

root = Path(__file__).resolve().parent
command = sys.argv[1] if len(sys.argv) > 1 else 'explore'
if command not in ('explore', 'replay', 'report'):
    raise SystemExit('Usage: demo_run.py [explore|replay|report]')
if qa.config()['base_url'] != 'http://127.0.0.1:8765':
    raise SystemExit('Demo helper requires the example local demo configuration. Your QA configuration was not changed.')

server = None
try:
    with socket.socket() as probe:
        occupied = probe.connect_ex(('127.0.0.1', 8765)) == 0
    if occupied:
        with urllib.request.urlopen('http://127.0.0.1:8765', timeout=3) as response:
            if b'Read-only local test fixture.' not in response.read():
                raise SystemExit('Port 8765 belongs to another service. Stop it or use the manual workflow.')
    else:
        log = root / 'artifacts' / 'demo-server.log'
        log.parent.mkdir(exist_ok=True)
        with log.open('a', encoding='utf-8') as output:
            server = subprocess.Popen([sys.executable, str(root / 'demo' / 'server.py')],
                                      stdout=output, stderr=output, cwd=root,
                                      creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for attempt in range(40):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8765', timeout=1) as response:
                    assert b'Read-only local test fixture.' in response.read()
                break
            except OSError:
                if server.poll() is not None:
                    raise SystemExit('Demo server failed; inspect artifacts/demo-server.log.')
                time.sleep(.25)
        else:
            raise SystemExit('Demo server did not start.')
    result = subprocess.run([sys.executable, str(root / 'qa.py'), command, '--csv', 'demo/cases.csv', '--batch', '5'], cwd=root)
    raise SystemExit(result.returncode)
finally:
    if server is not None:
        server.terminate()
        server.wait(timeout=10)
