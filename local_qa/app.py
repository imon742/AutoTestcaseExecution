"""Primary local agent UI. Existing project diagnostics remain available separately."""
import asyncio,base64,json,os,secrets,threading,urllib.parse,webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .models import Case,Policy,Budget,select_scope,redact,fingerprint,clean_url,SECRET_RE
from .store import Store
from .importer import load_file,load_public,load_oauth
from .ollama import Ollama
from .auth import LocalVault,bootstrap
from .browser import BrowserOwner
from .supervisor import Supervisor
from .writers import export_results,result_copy,SheetsOAuth,flush_writebacks
from .fixture import Fixture,MemoryVault

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.private'/'agent'
PORT=8784
TOKEN=secrets.token_urlsafe(32)

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)

class Vault:
    def __init__(self):self.fixture=None
    def get(self,name):
        if name=='fixture' and self.fixture:return {'username':self.fixture.username,'password':self.fixture.password}
        return LocalVault().get(name)

class App:
    def __init__(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        self.store=Store(PRIVATE/'agent.sqlite3');self.store.recover()
        self.config=json.loads((PRIVATE/'config.json').read_text(encoding='utf-8')) if (PRIVATE/'config.json').exists() else {
          'start_url':'','headless':False,'ollama':{'model':'','context':8192,'timeout':90,'vision':False},
          'auth':{'mode':'none'},'policy':{'origins':[],'allow_all_origins':False,'categories':['read'],'write_case_ids':[],'fixture_ids':{},
          'upload_root':'','allow_writeback':False},'budget':{'max_actions':20,'case_seconds':240,'action_ms':10000,'locator_retries':1}}
        self.config['policy'].setdefault('allow_all_origins',False)
        self.config['policy'].setdefault('fixture_ids',{})
        self.config.setdefault('browser_profile',str(PRIVATE/'browser-profile'))
        self.cases=[];self.source={};self.run_id='';self.busy=False;self.error='';self.lock=threading.RLock()
        self.vault=Vault();self.supervisor=None;self.fixture=None
        self.login_finish=threading.Event();self.login_active=False
    def start_job(self,fn):
        with self.lock:
            if self.busy:raise ValueError('A job is active. Pause/stop it before changing configuration.')
            self.busy=True;self.error=''
        def work():
            try:fn()
            except Exception as e:self.error=redact(str(e))[:1800]
            finally:self.busy=False
        threading.Thread(target=work,daemon=True).start()
    def models(self):return Ollama('',timeout=5).models()
    def state(self):
        results=self.store.results(self.run_id) if self.run_id else []
        return {'version':'local-agent-1','busy':self.busy,'error':self.error,'config':self.config,
            'cases':[{k:c.dict()[k] for k in ('case_id','scenario_id','title','source_status','steps','expected','source_hash','categories','fixture_id')} for c in self.cases],
            'source':{k:v for k,v in self.source.items() if k not in ('token','credentials')},
            'runs':self.store.runs(),'run_id':self.run_id,
            'results':[{k:r.get(k) for k in ('case_id','state','attempt_id','status','actual','started','finished','details')} for r in results],
            'events':self.store.events(self.run_id) if self.run_id else [],'chat':self.store.chat_history(),
            'writebacks':self.store.pending_writebacks(self.run_id) if self.run_id else []}
    def run(self,scope,scenario,selected):
        chosen=select_scope(self.cases,scope,scenario,selected)
        if not chosen:raise ValueError('No cases match the selected scope.')
        cfg=json.loads(json.dumps(self.config));policy=Policy(**cfg['policy'])
        policy.check_origin(cfg['start_url'])
        for case in chosen:
            policy.check_case(case)
            writes=set(case.categories)-{'read'}
            if writes:
                category=sorted(writes)[0]
                action_hash=fingerprint({'source_hash':case.source_hash,'fixture_id':case.fixture_id,'category':category})
                if not self.store.approval(case.case_id,case.fixture_id,category,action_hash):
                    raise ValueError('Side effect needs an exact stored approval for '+case.case_id+' / '+case.fixture_id+' / '+category+'.')
        if not cfg['ollama'].get('model'):raise ValueError('Select an installed local model.')
        if any('sign in' in c.steps.lower() or 'authorized' in c.preconditions.lower() for c in chosen) and cfg.get('auth',{}).get('mode','none')=='none' and not cfg.get('auth_state'):
            raise ValueError('Sign in first: Open browser to sign in, enter the site yourself, then Save signed-in session. No cases were started.')
        self.run_id=self.store.create_run(chosen,cfg,self.source)
        self.start_job(self.execute)
    def execute(self):
        self.supervisor=Supervisor(self.store,ROOT/'artifacts'/'agent',self.vault,fixtures=self.fixture)
        asyncio.run(self.supervisor.run(self.run_id))
        try:result_copy(self.store,self.run_id,ROOT/'artifacts'/'agent'/self.run_id)
        except Exception as e:
            export_results(self.store,self.run_id,ROOT/'artifacts'/'agent'/self.run_id)
            self.store.event(self.run_id,'export','Result-copy issue: '+str(e))
    def action(self,data):
        cmd=data['action']
        if cmd=='finish_login':
            if not self.login_active:raise ValueError('Open the sign-in browser first.')
            self.login_finish.set();return
        if cmd in ('pause','stop'):
            if self.supervisor:(self.supervisor.pause if cmd=='pause' else self.supervisor.stop).set()
            return
        if self.busy:raise ValueError('Wait for the current job, or Pause/Stop.')
        if cmd=='config':
            cfg=data['config'];cfg['policy'].setdefault('allow_all_origins',False);cfg['policy'].setdefault('fixture_ids',{})
            Policy(**cfg['policy'])
            for origin in cfg['policy']['origins']:Policy([origin]).check_origin(origin)
            self.config=cfg;save(PRIVATE/'config.json',cfg)
        elif cmd=='credential':
            LocalVault().save(data['name'],data['username'],data['password'])
            # Deliberately never return or persist these values in app config.
        elif cmd=='approve':
            case=next((c for c in self.cases if c.case_id==data.get('case_id')),None)
            if not case:raise ValueError('Choose an imported case before approving it.')
            category=data.get('category','')
            if category not in (set(case.categories)-{'read'}):raise ValueError('Approval category is not part of this case.')
            if data.get('fixture_id')!=case.fixture_id:raise ValueError('Approval fixture does not match the case fixture.')
            action_hash=fingerprint({'source_hash':case.source_hash,'fixture_id':case.fixture_id,'category':category})
            self.store.approve(case.case_id,case.fixture_id,category,action_hash,'User approved exact fixture/action through local UI.')
        elif cmd=='import_public':
            self.start_job(lambda:self.assign(*load_public(data['url'],data.get('sheet','Test Cases'))))
        elif cmd=='import_file':
            raw=base64.b64decode(data['content'],validate=True)
            if len(raw)>30_000_000:raise ValueError('Maximum source size is 30 MB.')
            suffix=Path(data['name']).suffix.lower()
            if suffix not in ('.xlsx','.csv'):raise ValueError('Use XLSX or CSV.')
            path=PRIVATE/'imports'/(secrets.token_hex(8)+suffix);path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
            self.assign(*load_file(path,data.get('sheet','Test Cases')))
        elif cmd=='google_connect':
            raw=base64.b64decode(data['content'],validate=True)
            if len(raw)>100000:raise ValueError('OAuth client config too large.')
            json.loads(raw);p=PRIVATE/'oauth'/'client.json';p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
            self.config['google']={'client_file':str(p),'token_file':str(p.parent/'token.json')}
            save(PRIVATE/'config.json',self.config)
            self.start_job(lambda:SheetsOAuth(**self.config['google']).connect(interactive=True))
        elif cmd=='import_google':
            def do_import():
                client=SheetsOAuth(**self.config['google']).connect()
                self.assign(*load_oauth(client,data['spreadsheet_id'],data.get('sheet','Test Cases')))
            self.start_job(do_import)
        elif cmd=='fixture':
            if self.fixture:self.fixture.close()
            self.fixture=Fixture();self.vault.fixture=self.fixture
            upload=PRIVATE/'fixture-files';upload.mkdir(exist_ok=True);(upload/'sample.txt').write_text('Disposable QA sample.',encoding='utf-8')
            model=self.config['ollama'].get('model','')
            self.config=self.fixture.config(model,upload)
            self.cases=self.fixture.cases();self.source={'kind':'fixture','sheet':'Local fixture'}
        elif cmd=='run':self.run(data.get('scope','non_pass'),data.get('scenario',''),data.get('selected',[]))
        elif cmd=='resume':
            id=data.get('run_id') or self.run_id
            if not id:raise ValueError('Choose a saved run to resume.')
            saved=self.store.run(id)
            if saved['source'].get('kind')=='fixture' and not self.fixture:
                raise ValueError('Disposable fixture sessions expire when the app closes. Load a new fixture for a new run. Real-site saved queues remain resumable.')
            self.run_id=id;self.config=saved['config'];self.source=saved['source']
            self.cases=[Case.from_dict(json.loads(r['data'])) for r in self.store.results(id)]
            self.start_job(self.execute)
        elif cmd=='export':
            if not self.run_id:raise ValueError('No run selected.')
            result_copy(self.store,self.run_id,ROOT/'artifacts'/'agent'/self.run_id)
        elif cmd=='export_replays':
            from .replay import export_replays
            export_replays(self.store,self.run_id,ROOT/'artifacts'/'agent'/self.run_id)
        elif cmd=='sync':self.start_job(lambda:flush_writebacks(self.store,self.run_id))
        elif cmd=='manual_login':
            self.login_finish.clear()
            async def sign_in():
                owner=await BrowserOwner(Policy(**self.config['policy']),ROOT/'artifacts'/'agent'/'manual-login',Budget(),self.config.get('browser_profile')).open(headless=False)
                self.login_active=True
                try:
                    await owner.page.goto(self.config['start_url'],wait_until='domcontentloaded',timeout=30000)
                    for _ in range(1200):
                        if self.login_finish.is_set():break
                        await asyncio.sleep(.5)
                    else:raise ValueError('Sign-in session expired after ten minutes. Open a new sign-in browser.')
                    pages=[p for p in owner.context.pages if not p.is_closed() and p.url.startswith(('http://','https://'))]
                    if not pages:raise ValueError('The sign-in browser was closed.')
                    page=pages[-1];url=clean_url(page.url)
                    if urllib.parse.urlsplit(url).path.rstrip('/').lower() in ('/login','/signin','/sign-in'):
                        raise ValueError('Still on a login page. Finish signing in and open the target page first.')
                    ready=self.config.get('session_ready_locator') or self.config.get('auth',{}).get('ready_locator')
                    if not ready:raise ValueError('Configure a session-ready locator before saving a real-site sign-in session.')
                    owner.page=page
                    await owner.locator(ready).wait_for(state='visible',timeout=15000)
                    folder=PRIVATE/'auth';folder.mkdir(exist_ok=True);path=folder/'manual-session.json'
                    await owner.context.storage_state(path=str(path),indexed_db=True)
                    self.config['auth_state']=str(path);self.config['auth']={'mode':'none'};self.config['start_url']=url
                    save(PRIVATE/'config.json',self.config)
                finally:self.login_active=False;await owner.close()
            self.start_job(lambda:asyncio.run(sign_in()))
        elif cmd=='test_login':
            async def test():
                owner=await BrowserOwner(Policy(**self.config['policy']),ROOT/'artifacts'/'agent'/'login-check',Budget(),self.config.get('browser_profile')).open()
                try:
                    await bootstrap(owner,self.config,self.vault)
                    folder=PRIVATE/'auth';folder.mkdir(exist_ok=True)
                    path=folder/(fingerprint(self.config['start_url'])[:16]+'.json')
                    await owner.context.storage_state(path=str(path),indexed_db=True)
                    self.config['auth_state']=str(path);save(PRIVATE/'config.json',self.config)
                finally:await owner.close()
            self.start_job(lambda:asyncio.run(test()))
        else:raise ValueError('Unknown application action.')
    def chat(self,message):
        """Map human text to fixed host actions; it never controls Playwright."""
        message=str(message).strip()
        if not message or len(message)>4000:raise ValueError('Chat message must be 1–4000 characters.')
        if SECRET_RE.search(message) or __import__('re').search(r'(?i)\b(password|passcode|jwt|bearer token)\b\s*(is|:|=)',message):
            self.store.chat_add('user','[Secret-like chat message rejected]')
            reply='I did not store that message. Enter credentials only in the local OS-vault form or the visible sign-in browser.'
            self.store.chat_add('assistant',reply);return {'intent':'reject_secret','reply':reply}
        self.store.chat_add('user',message)
        lower=message.casefold()
        if any(x in lower for x in ('what is running','what happened','status','show result')):
            reply=('No run is selected.' if not self.run_id else 'Run '+self.run_id+' is '+self.store.run(self.run_id)['state']+'. '+str(len(self.store.results(self.run_id)))+' case records are stored locally.')
            intent='show_result'
        elif 'pause' in lower:
            self.action({'action':'pause'});reply='Pause requested. The current case will finish its local commit first.';intent='pause'
        elif 'stop' in lower:
            self.action({'action':'stop'});reply='Stop requested. No new case will start.';intent='stop'
        elif 'open' in lower and ('sign in' in lower or 'login' in lower or 'browser' in lower):
            self.action({'action':'manual_login'});reply='Opened the local sign-in browser. Sign in there, then say Session ready.';intent='open_signin_browser'
        elif 'session ready' in lower or 'signed in' in lower:
            self.action({'action':'finish_login'});reply='The local app will validate and save the current browser session.';intent='session_ready'
        elif lower.startswith('list') or 'list cases' in lower:
            reply=str(len(self.cases))+' imported cases are available. Use the case table to review scope and fixtures.';intent='list_cases'
        elif lower.startswith('resume'):
            if not self.run_id:reply='Choose a saved run in the dashboard before resuming.';intent='resume'
            else:self.action({'action':'resume','run_id':self.run_id});reply='Resume requested for '+self.run_id+'.';intent='resume'
        elif lower.startswith('run'):
            reply='Review the selected scope and configuration, then use Run matching cases. Chat does not bypass action/fixture approval.';intent='run'
        else:
            reply='I can import cases, open the sign-in browser, record Session ready, list cases, show local run status, pause, stop, resume, export, or explain a blocked result. Please use a specific command.';intent='clarify'
        self.store.chat_add('assistant',reply)
        return {'intent':intent,'reply':reply}
    def assign(self,cases,source):self.cases=cases;self.source=source

def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def auth(self):return self.headers.get('Host')==f'127.0.0.1:{PORT}' and secrets.compare_digest(self.headers.get('X-QA-Token',''),TOKEN)
        def reply(self,data,status=200,kind='application/json'):
            body=json.dumps(data).encode() if kind=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/' and self.headers.get('Host')==f'127.0.0.1:{PORT}':return self.reply((ROOT/'local_qa'/'ui.html').read_bytes(),kind='text/html; charset=utf-8')
            if not self.auth():return self.reply({'error':'Use the local desktop launcher.'},403)
            try:
                if self.path=='/api/state':return self.reply(app.state())
                if self.path=='/api/models':return self.reply({'models':app.models()})
                if self.path.startswith('/api/evidence?'):
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    root=(ROOT/'artifacts'/'agent').resolve();path=(root/query.get('path',[''])[0]).resolve()
                    if not path.is_relative_to(root) or not path.is_file():raise ValueError('Evidence not found.')
                    import mimetypes
                    return self.reply(path.read_bytes(),kind=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
                return self.reply({'error':'Not found'},404)
            except Exception as e:self.reply({'error':redact(str(e))},400)
        def do_POST(self):
            if not self.auth() or self.headers.get('Origin')!=f'http://127.0.0.1:{PORT}':return self.reply({'error':'Unauthorized local request'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<42_000_000:raise ValueError('Request size invalid.')
                data=json.loads(self.rfile.read(length))
                if self.path=='/api/chat':return self.reply(app.chat(data.get('message','')))
                if self.path!='/api/action':return self.reply({'error':'Not found'},404)
                app.action(data);self.reply({'ok':True})
            except Exception as e:self.reply({'error':redact(str(e))},400)
    return Handler

def main():
    mutex=None
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.restype=ctypes.c_void_p
        mutex=kernel.CreateMutexW(None,False,'LocalQAAgent-ui4-'+fingerprint(str(ROOT))[:20])
        if ctypes.get_last_error()==183:
            runtime=PRIVATE/'runtime.json'
            if runtime.exists():webbrowser.open(json.loads(runtime.read_text())['url'])
            kernel.CloseHandle(ctypes.c_void_p(mutex))
            return
    app=App()
    server=ThreadingHTTPServer(('127.0.0.1',PORT),make_handler(app))
    url=f'http://127.0.0.1:{PORT}/#'+TOKEN
    save(PRIVATE/'runtime.json',{'url':url})
    webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        if app.supervisor:app.supervisor.stop.set()
        server.server_close()
        if mutex:kernel.CloseHandle(ctypes.c_void_p(mutex))

if __name__=='__main__':main()
