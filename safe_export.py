"""Create a source-only package. No runtime state, credentials, inputs or evidence."""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def export(target=None):
    selected=[p for p in (ROOT/'local_qa').rglob('*') if p.is_file() and p.suffix in ('.py','.html') and '__pycache__' not in p.parts]
    selected += [p for p in (ROOT/'tests'/'agent').rglob('*.py') if '__pycache__' not in p.parts]
    selected += [ROOT/n for n in ('dashboard.py','launch_assistant.pyw','Start Local Assistant.cmd','requirements-agent.txt','AGENT-GUIDE.md','ACCEPTANCE.md','RESUME-HERE.md','safe_export.py','tests/__init__.py') if (ROOT/n).is_file()]
    target=Path(target) if target else ROOT/'exports'/'Local-QA-Agent-source.zip'
    target.parent.mkdir(parents=True,exist_ok=True)
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in selected}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in selected:z.write(p,'Local-QA-Agent/'+str(p.relative_to(ROOT)))
        z.writestr('Local-QA-Agent/MANIFEST.json',json.dumps(manifest,indent=2))
        z.writestr('Local-QA-Agent/.gitignore','.private/\n.venv/\nartifacts/\ndata/\n*.sqlite3*\n__pycache__/\n')
    return target
if __name__=='__main__':print(export())
