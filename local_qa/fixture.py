"""Disposable loopback-only mixed-action QA fixture; never real business data."""
import html,json,secrets,threading,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from .models import Case

class MemoryVault:
    def __init__(self,values=None):self.values=values or {}
    def get(self,name):
        from .models import AuthRequired
        if name not in self.values:raise AuthRequired('Credential not configured in this test vault.')
        return dict(self.values[name])

def action(kind,name='',role='button',value='',category='read',by='role'):
    return {'kind':kind,'locator':{'by':by,'role':role,'name':name},'value':value,'category':category,'reason':'Execute the explicit source fixture action.'}

class Fixture:
    def __init__(self):
        self.username='fixture-'+secrets.token_hex(4);self.password=secrets.token_urlsafe(18)
        self.sessions=set();self.lock=threading.RLock();self.reset()
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send_html(self,body,code=200,cookie=None):
                body=body.encode();self.send_response(code)
                self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)))
                if cookie:self.send_header('Set-Cookie',cookie)
                self.end_headers();self.wfile.write(body)
            def redirect(self,to,cookie=None):
                self.send_response(303);self.send_header('Location',to)
                if cookie:self.send_header('Set-Cookie',cookie)
                self.end_headers()
            def authenticated(self):return any(('sid='+s) in self.headers.get('Cookie','') for s in owner.sessions)
            def login(self):
                self.send_html('<h1>Sign in</h1><form method="post" action="/login"><label>Username<input name="username" autocomplete="username"></label><label>Password<input type="password" name="password" autocomplete="current-password"></label><button>Sign in</button></form>')
            def shell(self,content):
                return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Disposable QA fixture</title><header data-testid="authenticated">Local fixture signed in</header><nav><a href="/dashboard">Dashboard</a> <a href="/records">Records</a> <a href="/expire">Expire session</a></nav>'+content+'</html>'
            def form(self,name='',editing=False):
                return '<h1>'+('Edit fixture' if editing else 'Create fixture')+'</h1><form method="post" action="'+('/edit' if editing else '/create')+'"><label>Name<input name="name" value="'+html.escape(name,quote=True)+'"></label><label for="fixture-type">Type</label><select id="fixture-type" name="type"><option>Personal</option><option>Team</option></select><label>Priority<input type="checkbox" name="priority"></label><button>Save</button></form>'
            def do_GET(self):
                path=urllib.parse.urlsplit(self.path).path
                if path=='/login' or not self.authenticated():self.login();return
                if path=='/expire':
                    owner.return_to='/records';self.redirect('/login','sid=; Max-Age=0; Path=/');return
                if path=='/new':self.send_html(self.shell(self.form()));return
                if path=='/edit':self.send_html(self.shell(self.form('QA-Seed',True)));return
                if path=='/bug':self.send_html(self.shell('<h1>Incorrect value</h1>'));return
                if path=='/records':
                    body='<h1>Records</h1><a role="button" href="/new">Create fixture</a><a role="button" href="/edit">Edit QA-Seed</a><a href="/bug">Show broken result</a>'
                    body+='<button onclick="document.querySelector(\'dialog\').showModal()">View details</button><dialog>Fixture details</dialog>'
                    body+='<form method="post" action="/delete"><button>Delete QA-Disposable</button></form>'
                    body+='<form method="post" enctype="multipart/form-data" action="/upload"><label>Attachment<input type="file" name="attachment"></label><button>Upload sample</button></form>'
                    body+='<table><tr><th>Name</th></tr>'+''.join('<tr><td>'+html.escape(x)+'</td></tr>' for x in owner.records)+'</table>'
                    self.send_html(self.shell(body));return
                self.send_html(self.shell('<h1>Dashboard</h1><p>Disposable local QA application.</p>'))
            def do_POST(self):
                body=self.rfile.read(min(int(self.headers.get('Content-Length','0')),1_000_000))
                form=urllib.parse.parse_qs(body.decode(errors='replace'))
                if self.path=='/login':
                    if form.get('username',[''])[0]!=owner.username or form.get('password',[''])[0]!=owner.password:
                        self.send_html('<h1>Invalid login</h1>',401);return
                    sid=secrets.token_hex(12);owner.sessions.add(sid)
                    dest=owner.return_to or '/dashboard';owner.return_to=None
                    self.redirect(dest,'sid='+sid+'; HttpOnly; SameSite=Lax; Path=/');return
                if not self.authenticated():self.login();return
                if self.path in ('/create','/edit'):
                    name=form.get('name',[''])[0]
                    if not name:
                        self.send_html(self.shell(self.form()+'<p>Name is required</p>'));return
                    if not name.startswith('QA-'):
                        self.send_html(self.shell('<p>Only QA fixture names are allowed</p>'),400);return
                    owner.records.append(name)
                    self.send_html(self.shell('<h1>Saved '+html.escape(name)+'</h1>'));return
                if self.path=='/delete':
                    owner.records=[r for r in owner.records if r!='QA-Disposable']
                    self.send_html(self.shell('<h1>Deleted QA-Disposable</h1>'));return
                if self.path=='/upload':
                    self.send_html(self.shell('<h1>Received sample.txt</h1>' if b'filename="sample.txt"' in body else '<h1>Missing sample</h1>'));return
                self.send_html('<h1>Not found</h1>',404)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.origin=f'http://127.0.0.1:{self.server.server_port}'
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    def reset(self):
        self.records=['QA-Seed','QA-Disposable'];self.return_to=None
    def close(self):self.server.shutdown();self.server.server_close()
    def config(self,model,upload_root,headless=False):
        return {'start_url':self.origin+'/login','headless':headless,
          'ollama':{'model':model,'context':8192,'timeout':90,'vision':False},
          'auth':{'mode':'password','credential_name':'fixture',
            'ready_locator':{'by':'test_id','role':'','name':'authenticated'},
            'login_locator':{'by':'label','role':'','name':'Password'},
            'steps':[{'kind':'fill','locator':{'by':'label','role':'','name':'Username'},'credential':'username'},
                     {'kind':'fill','locator':{'by':'label','role':'','name':'Password'},'credential':'password'},
                     {'kind':'click','locator':{'by':'role','role':'button','name':'Sign in'}}]},
          'policy':{'origins':[self.origin],'categories':['read','create','edit','delete','upload'],
                    'write_case_ids':[c.case_id for c in self.cases()], 'fixture_ids':{'local-fixture':self.origin},
                    'upload_root':str(upload_root),'allow_writeback':False},'budget':{'max_actions':12,'case_seconds':120,'model_seconds':60,'action_ms':5000,'locator_retries':1}}
    def cases(self):
        nav=action('click','Records','link')
        rows=[
          ('F01','Read records',[nav],'Text "Records" is visible.',['read']),
          ('F02','Required validation',[nav,action('click','Create fixture',category='create'),action('click','Save',category='create')],'Text "Name is required" is visible.',['create']),
          ('F03','Create fixture',[nav,action('click','Create fixture',category='create'),action('fill','Name',value='QA-Alpha',category='create',by='label'),action('click','Save',category='create')],'Text "Saved QA-Alpha" is visible.',['create']),
          ('F04','Edit fixture',[nav,action('click','Edit QA-Seed',category='edit'),action('fill','Name',value='QA-Edited',category='edit',by='label'),action('click','Save',category='edit')],'Text "Saved QA-Edited" is visible.',['edit']),
          ('F05','Delete disposable fixture',[nav,action('click','Delete QA-Disposable',category='delete')],'Text "Deleted QA-Disposable" is visible.',['delete']),
          ('F06','Upload safe sample',[nav,action('upload_fixture','Attachment',value='sample.txt',category='upload',by='label'),action('click','Upload sample',category='upload')],'Text "Received sample.txt" is visible.',['upload']),
          ('F07','Select and check',[nav,action('click','Create fixture',category='create'),action('fill','Name',value='QA-Selected',category='create',by='label'),action('select','Type',value='Team',category='create',by='label'),action('check','Priority',category='create',by='label'),action('click','Save',category='create')],'Text "Saved QA-Selected" is visible.',['create']),
          ('F08','Close modal',[nav,action('click','View details'),action('close_dialog')],'Text "Fixture details" is absent.',['read']),
          ('F09','Application bug',[nav,action('click','Show broken result','link')],'Text "Expected value" is visible.',['read']),
          ('F10','Missing locator',[action('click','Never exists')],'Text "Anything" is visible.',['read']),
          ('F11','Expired session',[action('click','Expire session','link')],'Text "Records" is visible.',['read']),
          ('F12','Model timeout',[nav],'Text "Records" is visible.',['read'])]
        return [Case(id,scenario_id='LOCAL-FIXTURE',title=title,steps=json.dumps(actions),expected=expected,
                     categories=categories,fixture_id='local-fixture',source_status='Pass' if id in ('F07','F08') else 'Not Run').seal()
                for id,title,actions,expected,categories in rows]
