"""Loopback-only local testing assistant. No cloud model, arbitrary shell tools or Sheet writes."""
import asyncio
import csv
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import qa
import assistant_engine as engine
import case_import

APP_VERSION='2026-10-29.3'

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.private'/'dashboard.json'
TOKEN=secrets.token_urlsafe(32)
PORT=8766
MUTEX=threading.RLock()
SIGNAL=threading.Event()
DEFAULT={'site':'https://meet2.synesisit.info:85','sheet':'https://docs.google.com/spreadsheets/d/1pDgSUjcMEjJJLicpeCrwmyFVwwDT9kLhSZN6e1yfRx4/edit',
         'tab':'Test Cases','gid':81082,'entry_path':'/','approved_paths':['/'],'qa_confirmed':False,
         'login_url':'https://meet2.synesisit.info',
         'cases':[],'messages':[],'source':'Not imported','preview':False,'selected':[], 'plans':{}}
DATA=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else DEFAULT.copy()
DATA.update(job='',busy=False,paused=False,error='',completed=0)
CACHED_CASES=None
CACHED_CONFIG=None
CACHED_ROOT=None

def persist():
    with MUTEX:
        qa.save(STATE,{k:v for k,v in DATA.items() if k not in ('job','busy','paused','error','completed')})

def say(text,role='assistant'):
    with MUTEX:
        DATA['messages'].append({'role':role,'text':str(text),'at':qa.now()})
        DATA['messages']=DATA['messages'][-60:]
        persist()

def settings():
    site=DATA['site'].rstrip('/')
    u=urlsplit(site)
    if u.scheme not in ('https','http') or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:
        raise ValueError('Enter a plain QA origin with no credentials, path or token.')
    c={'base_url':site,'approved_read_paths':list(DATA['approved_paths']), 'entry_path':DATA['entry_path'],
       'model':engine.MODEL,'headless':False,'policy_version':3}
    start=DATA.get('login_url') or (f'{u.scheme}://{u.hostname}' if u.hostname=='meet2.synesisit.info' and u.port==85 else site)
    start=start.rstrip('/')
    portal=urlsplit(start)
    if (portal.scheme!=u.scheme or portal.hostname!=u.hostname or portal.username or portal.password
            or portal.query or portal.fragment or portal.path not in ('','/')):
        raise ValueError('The sign-in starting website must be a plain origin on the same QA host.')
    if start!=site:
        c.update(login_url=start,bootstrap_label='Admin Settings')
    if DATA.get('backend_access_approved') or (u.hostname=='meet2.synesisit.info' and DATA.get('backend_access_approved') is not False):
        backend=f'{u.scheme}://{u.hostname}:8092'
        c.update(read_api_origins=[backend],session_auth_urls=[backend+'/services/dashboard/api/authenticate'],
                 optional_network_hosts=['www.googletagmanager.com','api-js.mixpanel.com','fonts.googleapis.com',
                                         'fonts.gstatic.com','cdn-cookieyes.com','ipapi.co'])
        if start!=site:
            c['read_api_origins'].append(start)
            c['session_auth_urls'].append(start+'/services/dashboard/api/authenticate')
    qa.safe_url(c,c['entry_path'])
    return c

def dataset():
    global CACHED_CASES,CACHED_CONFIG,CACHED_ROOT
    c=settings()
    key=(str(ROOT),qa.digest(c))
    if CACHED_CASES is not DATA['cases'] or CACHED_CONFIG!=key:
        CACHED_ROOT=ROOT/'artifacts'/'assistant'/qa.digest({'config':c,'cases':DATA['cases']})[:16]
        CACHED_CASES=DATA['cases'];CACHED_CONFIG=key
    return CACHED_ROOT

def folder(case):
    return dataset()/case['id']

def read_json(path,default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def displayed_result(f):
    actual=read_json(f/'result.json')
    if actual:
        return actual
    error=read_json(f/'preparation-error.json')
    if error:
        return {'status':'Blocked','actual':'Preparation blocked: '+error['error']}
    plan=read_json(f/'plan.json',{})
    missing=plan.get('plan',{}).get('unverifiable',[])
    return {'status':'Blocked','actual':'Preparation requires review: '+'; '.join(missing)} if missing else {}

def require_idle():
    if DATA['busy']:
        raise ValueError('A job is running. Pause between cases, or finish the open sign-in first.')

def job(name,func):
    with MUTEX:
        require_idle()
        DATA.update(busy=True,job=name,error='',paused=False)
        SIGNAL.clear()
    def work():
        try:
            func()
        except Exception as e:
            DATA['error']=str(e)
            say('Blocked: '+str(e))
        finally:
            with MUTEX:
                DATA.update(busy=False,job='')
                persist()
    threading.Thread(target=work,daemon=True).start()

def import_records(records,source,preview=False):
    cases=engine.normalize(records)
    DATA.update(cases=cases,source=source,preview=preview,plans={},selected=[])
    eligible=[c['id'] for c in cases if not engine.risk_reason(c)]
    DATA['selected']=eligible[:5]
    persist()
    say(f'Loaded {len(cases)} cases'+(' as a preview only' if preview else '')+'. Historical Sheet results are separate. Select up to five read-only cases and click Run; planning and validation happen automatically.')

async def login_browser(google=False):
    from playwright.async_api import async_playwright
    c=settings()
    url=DATA['sheet'] if google else c.get('login_url',c['base_url'])
    if google:
        match=re.fullmatch(r'https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)/?(?:edit)?(?:[?#].*)?',url)
        if not match:
            raise ValueError('Use a Google Sheets URL, not a credential/token URL.')
        sheet_id=match.group(1)
        auth=ROOT/'.private'/'google-auth.json'
    else:
        if not DATA['qa_confirmed']:
            raise ValueError('First confirm that this is your disposable QA environment.')
        auth=qa.PRIVATE/(qa.digest(c['base_url'])[:16]+'-auth.json')
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False)
        try:
            context=(await browser.new_context(storage_state=str(auth) if auth.exists() else None,accept_downloads=False)
                     if google else await qa.context_options(browser,c))
            page=await context.new_page()
            await page.goto(url,wait_until='domcontentloaded',timeout=45000)
            say('Sign in yourself in the opened browser. '+('Select the Test Cases tab, then click Finish Google sign-in/import here.' if google else
                'Sign in on the meeting site, click Admin Settings to enter CM, then click Save QA session here. Keep both tabs open if a new tab appears.'))
            waited=0
            session_origins={}
            while not SIGNAL.is_set():
                if not google:
                    for tab in context.pages:
                        try:
                            origin=await tab.evaluate('location.origin')
                            if origin in (c['base_url'],c.get('login_url',c['base_url'])):
                                session_origins[origin]=await tab.evaluate('Object.fromEntries(Object.entries(sessionStorage))')
                        except Exception:
                            pass
                await asyncio.sleep(.5)
                waited+=.5
                if waited>1200:
                    raise ValueError('Manual sign-in timed out after 20 minutes. Start sign-in again.')
            if google:
                # Read-only authenticated CSV export. No OAuth client secret/API key
                # is requested; Google cookies stay in the ignored local state file.
                gid=int(DATA['gid'])
                if gid<0:
                    raise ValueError('Invalid tab gid.')
                response=await context.request.get(f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}',timeout=45000)
                if response.status!=200:
                    raise ValueError('Google did not allow the read-only export. Export this tab to CSV yourself and import the file instead; do not change sharing permissions.')
                body=await response.body()
                if len(body)>5_000_000 or b'<html' in body[:500].lower() or b'<!doctype html' in body[:500].lower():
                    raise ValueError('Google returned a login page or oversized response. Use local CSV import.')
                rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
                import_records(rows,'Google Sheet: '+DATA['tab']+' (read-only browser export)')
                auth.parent.mkdir(exist_ok=True)
                await context.storage_state(path=str(auth))
            else:
                pages=[x for x in context.pages if urlsplit(x.url).netloc==urlsplit(c['base_url']).netloc]
                if not pages:
                    raise ValueError('No signed-in QA page found. Complete login and return to the QA website.')
                current=pages[-1].url
                u=urlsplit(current)
                path=u.path or '/'
                if u.query:
                    raise ValueError('The selected page has URL parameters. Choose a clean read-only page without credentials or session tokens in the URL.')
                auth.parent.mkdir(exist_ok=True)
                await context.storage_state(path=str(auth),indexed_db=True)
                session_values=await pages[-1].evaluate('Object.fromEntries(Object.entries(sessionStorage))')
                qa.save(qa.PRIVATE/(qa.digest(c['base_url'])[:16]+'-session.json'),session_values)
                session_origins[c['base_url']]=session_values
                qa.save(qa.PRIVATE/(qa.digest(c['base_url'])[:16]+'-session-origins.json'),session_origins)
                DATA['entry_path']=path
                if path not in DATA['approved_paths']:
                    DATA['approved_paths'].append(path)
                persist()
                say('QA session saved locally. Approved entry page: '+path+'. No password was requested in chat.')
        finally:
            await browser.close()

def selected_cases(ids=None):
    wanted=set(ids or DATA['selected'])
    result=[c for c in DATA['cases'] if c['id'] in wanted]
    if not result:
        raise ValueError('Select 1–10 cases first.')
    if len(result)>10:
        raise ValueError('Maximum batch size is 10. Start with five cases.')
    return result

def export_report():
    rows=[]
    root=dataset()
    for c in DATA['cases']:
        f=root/c['id']
        r=displayed_result(f)
        replay=read_json(f/'replay.json',{})
        rows.append({'Case ID':c['id'],'Status':r.get('status','Not Run'),'Actual Result':r.get('actual','Not executed.'),
                     'Evidence':str(f) if r else '', 'Playwright Replay':replay.get('status','Not Run')})
    p=dataset()/'report.csv'
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=['Case ID','Status','Actual Result','Evidence','Playwright Replay'])
        w.writeheader();w.writerows(rows)
    return p

def batch(kind):
    if not DATA['qa_confirmed']:
        raise ValueError('Confirm the disposable QA environment first.')
    c=settings()
    cases=selected_cases()
    async def work():
        for case in cases:
            if DATA['paused']:
                break
            f=folder(case)
            old=read_json(f/('replay.json' if kind=='replay' else 'result.json'),{})
            if kind!='prepare' and old.get('finished') and old.get('status') in ('Pass','Fail'):
                continue
            DATA['job']=kind+': '+case['id']
            try:
                if kind=='prepare':
                    saved=read_json(f/'plan.json',{})
                    if saved.get('case_hash')==qa.digest(case) and saved.get('config_hash')==qa.digest(c):
                        plan=saved['plan']
                    else:
                        plan=await engine.prepare(c,case,f)
                    (f/'preparation-error.json').unlink(missing_ok=True)
                    say(case['id']+': plan prepared. '+('Blocked criteria: '+'; '.join(plan['unverifiable']) if plan['unverifiable'] else 'Review the plan before approving execution.'))
                else:
                    if kind=='run':
                        reason=engine.risk_reason(case)
                        if reason:
                            raise ValueError('Side-effect/ambiguous case is not authorized for this read-only trial: '+reason)
                        saved=read_json(f/'plan.json',{})
                        if (saved.get('case_hash')!=qa.digest(case) or saved.get('config_hash')!=qa.digest(c)
                                or saved.get('plan',{}).get('unverifiable')):
                            DATA['job']='Preparing '+case['id']
                            await engine.prepare(c,case,f)
                            saved=read_json(f/'plan.json',{})
                        if saved.get('plan',{}).get('unverifiable'):
                            raise ValueError('Cannot verify the complete expected result: '+'; '.join(saved['plan']['unverifiable']))
                        # Explicit Run authorizes only this selected read-only plan.
                        # This is not a claim of human plan/evidence review.
                        qa.save(f/'execution-authorization.json',{'plan_hash':qa.digest(saved),
                            'source':'Explicit Run of selected read-only case','at':qa.now()})
                        DATA['job']='Running '+case['id']
                    if kind=='replay':
                        original=read_json(f/'result.json',{})
                        review=read_json(f/'flow-review.json',{})
                        if original.get('status')!='Pass' or review.get('result_hash')!=qa.digest(original):
                            raise ValueError('Only reviewed successful flows can be replayed.')
                    if kind=='replay':
                        import subprocess
                        test=ROOT/'tests'/'assistant_generated'/dataset().name/f'test_{case["id"]}.py'
                        if not test.exists():
                            raise ValueError('Generate the reviewed Playwright test first.')
                        proc=await asyncio.to_thread(subprocess.run,
                            [sys.executable,'-m','pytest',str(test),'-q','--junitxml='+str(f/'replay-junit.xml')],
                            cwd=ROOT,capture_output=True,text=True)
                        (f/'pytest-output.txt').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
                        r=read_json(f/'replay.json',{})
                        if not r.get('finished'):
                            raise ValueError('Generated test did not complete; see pytest-output.txt.')
                        if proc.returncode and r.get('status')=='Pass':
                            raise ValueError('Pytest failed after replay; see pytest-output.txt.')
                    else:
                        r=await engine.execute(c,case,f)
                    say(case['id']+': '+r['status']+'. '+r['actual'][:700])
            except Exception as e:
                if kind=='prepare':
                    qa.save(f/'preparation-error.json',{'error':str(e),'at':qa.now()})
                    say(case['id']+': preparation blocked: '+str(e))
                else:
                    qa.save(f/('replay.json' if kind=='replay' else 'result.json'),
                            {'id':case['id'],'status':'Blocked','actual':str(e),'finished':qa.now()})
                    say(case['id']+': Blocked. '+str(e))
            DATA['completed']+=1
            qa.save(dataset()/'checkpoint.json',{'last_case':case['id'],'operation':kind,'updated':qa.now()})
            export_report()
        say('Paused after the current case.' if DATA['paused'] else 'Batch finished. Pass/Fail executions are saved and skipped on resume; Blocked cases can be retried after correcting their cause. Inspect each actual result.')
    asyncio.run(work())

def approve_plan(case_id):
    case=next(c for c in DATA['cases'] if c['id']==case_id)
    f=folder(case)
    p=read_json(f/'plan.json')
    if not p or p['case_hash']!=qa.digest(case) or p['config_hash']!=qa.digest(settings()):
        raise ValueError('Prepare a fresh plan first.')
    if p['plan']['unverifiable']:
        raise ValueError('This plan has unverifiable criteria. It cannot be approved as a complete test; clarify requirements or provide authoritative data.')
    qa.save(f/'plan-review.json',{'plan_hash':qa.digest(p),'reviewed_at':qa.now()})
    say(case_id+': read-only plan approved for execution.')

def approve_flow(case_id):
    case=next(c for c in DATA['cases'] if c['id']==case_id)
    f=folder(case)
    r=read_json(f/'result.json',{})
    if r.get('status')!='Pass':
        raise ValueError('Only executed successful flows can be approved.')
    qa.save(f/'flow-review.json',{'result_hash':qa.digest(r),'reviewed_at':qa.now()})
    out=ROOT/'tests'/'assistant_generated'/dataset().name
    out.mkdir(parents=True,exist_ok=True)
    # A generated test is a literal replay of the reviewed plan, with fresh state
    # and assertions. No model-generated source code is executed.
    code=('import asyncio\nfrom dashboard import replay_exported\n\n'
          f'def test_{case_id.replace("-","_")}():\n'
          f'    asyncio.run(replay_exported({str(f)!r}, {settings()!r}, {case!r}, {qa.digest(r)!r}))\n')
    (out/f'test_{case_id}.py').write_text(code,encoding='utf-8')
    say(case_id+': successful flow approved; Playwright pytest file generated. Use Replay reviewed to run it.')

async def replay_exported(path,config,case,result_hash):
    f=Path(path)
    r=read_json(f/'result.json',{})
    review=read_json(f/'flow-review.json',{})
    if qa.digest(r)!=result_hash or review.get('result_hash')!=result_hash or r.get('status')!='Pass':
        raise ValueError('Result approval is missing or stale.')
    result=await engine.execute(config,case,f,replay=True)
    assert result['status']=='Pass',result['actual']

def run_from_chat(size=5):
    size=max(1,min(int(size),10))
    pending=[c for c in DATA['cases'] if c['id'] in DATA['selected'] and read_json(folder(c)/'result.json',{}).get('status') not in ('Pass','Fail')]
    if not pending:
        pending=[c for c in DATA['cases'] if not engine.risk_reason(c) and read_json(folder(c)/'result.json',{}).get('status') not in ('Pass','Fail')][:size]
        DATA['selected']=[c['id'] for c in pending]
        persist()
    if not pending:
        say('No pending read-only cases remain in the imported data. Import the full Sheet if this is a preview.')
        return
    if len(pending)>size:
        DATA['selected']=[c['id'] for c in pending[:size]]
    batch('run')

def chat(message):
    say(message,'user')
    low=message.lower().strip()
    # Exact, visible user commands invoke tools. Other text goes only to local
    # Ollama for conversation. Neither model replies nor Sheet cells execute tools.
    if low in ('run','run 5','run five','continue','resume','run selected'):
        if not DATA['cases']:
            say('Import your Sheet first using Google sign-in/import. I do not have local Google access until you sign in.')
        else:
            job('run selected',run_from_chat)
    elif low in ('prepare','prepare selected','plan','plan tests'):
        job('prepare selected',lambda:batch('prepare'))
    elif low in ('pause','stop'):
        DATA['paused']=True;say('I will stop after the current case and preserve its checkpoint.')
    elif low in ('login','sign in','open browser','open qa browser'):
        job('QA sign-in',lambda:asyncio.run(login_browser()))
    elif low in ('report','results','show results'):
        say('Results are in the case list. Select a case to inspect actual behavior and evidence. Download report exports local results only; your Sheet is unchanged.')
    elif re.search(r'https://docs\.google\.com/spreadsheets/d/',message):
        match=re.search(r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]+(?:/edit)?(?:[?#][^\s"<>]*)?',message)
        DATA['sheet']=match.group(0)
        persist()
        say('Public Sheet link saved. Click Import public Sheet; this uses no Google account or cookies. You can also upload .xlsx or CSV locally. Select the intended tab by name.')
    else:
        def converse():
            counts={s:0 for s in ['Pass','Fail','Blocked','Not Run']}
            for case in DATA['cases']:
                r=read_json(folder(case)/'result.json',{})
                counts[r.get('status','Not Run')]+=1
            context=('You are a concise local QA assistant. Your model runs locally via Ollama. '
                     'Classify the user request with intent chat/run/prepare/pause/login/report and supply a short reply. '
                     'Use an action intent ONLY for a clear request to do that action, not questions, quotations, '
                     'hypotheticals, negations, or descriptions. Default to chat when unsure. '
                     'Never claim a browser action ran: the application will execute supported intents separately. '
                     'Commands supported by the app: prepare, run, resume, pause, login, report. '
                     'UI buttons anonymously import public Google Sheets, import local Excel/CSV, save QA login, '
                     'automatically prepare and execute up to 10 selected read-only cases without manual plan approval, '
                     'review successful evidence and generate/replay Playwright tests. '
                     'No Sheet writes or destructive tests exist. Explain that ambiguous/backend checks can be Blocked. '
                     'Never ask for passwords/API keys in chat. Do not invent results. '
                     'Current verified state: '+json.dumps({'cases':len(DATA['cases']),'counts':counts,'source':DATA['source'],'preview':DATA['preview']}))
            schema={'type':'object','properties':{'intent':{'type':'string','enum':['chat','run','prepare','pause','login','report']},
                    'batch':{'type':'integer','minimum':1,'maximum':10},'reply':{'type':'string'}},'required':['intent','batch','reply']}
            answer=json.loads(engine.local_chat([{'role':'system','content':context},{'role':'user','content':message[:4000]}],schema))
            intent=answer.get('intent','chat')
            if intent=='run':
                run_from_chat(answer.get('batch',5))
            elif intent=='prepare':
                batch('prepare')
            elif intent=='login':
                DATA['job']='QA sign-in'
                asyncio.run(login_browser())
            elif intent=='pause':
                DATA['paused']=True;say('Pause requested. Completed results are preserved.')
            elif intent=='report':
                export_report();say('Current verified local results: '+json.dumps(counts)+'. Inspect case evidence or download the report. Your Sheet is unchanged.')
            else:
                say(answer.get('reply','Please use the workspace buttons to import, sign in, or run a small reviewed batch.'))
        job('Local chat',converse)

def state_view():
    with MUTEX:
        d={k:v for k,v in DATA.items() if k!='cases'}
        d['app_version']=APP_VERSION
        d['cases']=[]
        root=dataset()
        for case in DATA['cases']:
            f=root/case['id']
            r=displayed_result(f)
            d['cases'].append({**case,'status':r.get('status','Not Run'),'actual':r.get('actual','Not executed.'),
                              'risk':engine.risk_reason(case),'plan':read_json(f/'plan.json'),
                              'plan_review':read_json(f/'plan-review.json'),'result':r,
                              'flow_review':read_json(f/'flow-review.json'),'replay':read_json(f/'replay.json'),
                              'evidence':[str(x.relative_to(ROOT)) for x in sorted(f.glob('*')) if x.suffix in ('.png','.zip','.json','.xml','.txt')]})
        return d

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # Do not log tokens, request bodies, cookies, URLs or QA content.
    def authorized(self):
        return self.headers.get('Host')==f'127.0.0.1:{PORT}' and secrets.compare_digest(self.headers.get('X-QA-Token',''),TOKEN)
    def reply(self,value,code=200,ctype='application/json'):
        body=json.dumps(value).encode() if ctype=='application/json' else value
        self.send_response(code)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/' and self.headers.get('Host')==f'127.0.0.1:{PORT}':
            return self.reply((ROOT/'dashboard.html').read_bytes(),ctype='text/html; charset=utf-8')
        if not self.authorized():
            return self.reply({'error':'Open the dashboard using Start Local Assistant.cmd.'},403)
        try:
            if self.path=='/api/state':
                return self.reply(state_view())
            if self.path.startswith('/api/file?'):
                rel=parse_qs(urlsplit(self.path).query).get('path',[''])[0]
                path=(ROOT/rel).resolve()
                path.relative_to((ROOT/'artifacts').resolve())
                if not path.is_file():
                    raise ValueError('Evidence file not found.')
                import mimetypes
                return self.reply(path.read_bytes(),ctype=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
            if self.path=='/api/report':
                return self.reply(export_report().read_bytes(),ctype='text/csv; charset=utf-8')
            self.reply({'error':'Unknown endpoint'},404)
        except Exception as e:
            self.reply({'error':str(e)},400)
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.authorized() or origin!=f'http://127.0.0.1:{PORT}':
            return self.reply({'error':'Unauthorized local request'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=7_000_000:
                raise ValueError('Request too large or empty.')
            a=json.loads(self.rfile.read(length))
            cmd=a.get('action')
            with MUTEX:
                if cmd=='save':
                    require_idle()
                    previous={k:DATA.get(k) for k in ('site','login_url','sheet','tab','gid','entry_path','approved_paths','qa_confirmed','backend_access_approved')}
                    try:
                        DATA.update(site=str(a['site']).rstrip('/'),sheet=re.sub(r'^http://docs\.google\.com/', 'https://docs.google.com/',str(a['sheet'])),tab=str(a.get('tab','Test Cases')),gid=int(a['gid']),
                                    login_url=str(a.get('login_url',DATA.get('login_url') or a['site'])).rstrip('/'),
                                    entry_path=str(a.get('entry_path','/')),
                                    approved_paths=list(dict.fromkeys([x.strip() for x in str(a.get('paths','/')).splitlines() if x.strip()])),
                                    qa_confirmed=a.get('qa_confirmed') is True,
                                    backend_access_approved=a.get('backend_access_approved') is True)
                        settings()
                    except Exception:
                        DATA.update(previous);raise
                    persist();say('Settings saved locally. No website action or Sheet write was performed.')
                elif cmd=='select':
                    require_idle();DATA['selected']=[c['id'] for c in DATA['cases'] if c['id'] in a.get('ids',[])];persist()
                elif cmd=='csv':
                    require_idle();import_records(case_import.csv_records(a['content'].encode('utf-8')),'Local CSV export')
                elif cmd=='public_sheet':
                    job('Anonymous public Sheet import',lambda:import_records(
                        case_import.public_sheet(DATA['sheet'],DATA.get('tab','Test Cases'),DATA.get('gid')),
                        'Public Google Sheet: '+DATA.get('tab','Test Cases')+' (anonymous read)'))
                elif cmd=='excel':
                    require_idle()
                    import base64
                    raw=base64.b64decode(a['content'],validate=True)
                    tab=str(a.get('tab',DATA.get('tab','Test Cases')))
                    records=case_import.excel_records(raw,tab)
                    DATA['tab']=tab
                    import_records(records,'Local Excel workbook: '+tab)
                elif cmd=='preview':
                    require_idle()
                    p=read_json(ROOT/'data'/'sheet-preview.json')
                    import_records([dict(zip(p['headers'],r)) for r in p['rows']], 'Connected read-only preview of Test Cases',True)
                elif cmd=='google':
                    job('Google sign-in/import',lambda:asyncio.run(login_browser(True)))
                elif cmd=='login':
                    job('QA sign-in',lambda:asyncio.run(login_browser()))
                elif cmd=='finish_login':
                    if 'sign-in' not in DATA['job']:
                        raise ValueError('No sign-in browser is waiting.')
                    SIGNAL.set()
                elif cmd in ('prepare','run','replay'):
                    selected_cases();job(cmd,lambda:batch(cmd))
                elif cmd=='pause':
                    DATA['paused']=True;say('Pause requested; the current case will finish and be checkpointed.')
                elif cmd=='approve_plan':
                    require_idle();approve_plan(a['id'])
                elif cmd=='approve_flow':
                    require_idle();approve_flow(a['id'])
                elif cmd=='retry':
                    require_idle()
                    case=next(c for c in DATA['cases'] if c['id']==a['id'])
                    f=folder(case)
                    # Preserve earlier evidence as an immutable attempt before retry.
                    if f.exists():
                        dest=f.parent/'previous-attempts'/(case['id']+'-'+str(time.time_ns()))
                        dest.parent.mkdir(exist_ok=True)
                        f.rename(dest)
                    say(case['id']+': earlier evidence preserved. Prepare a new plan before retrying.')
                elif cmd=='chat':
                    if DATA['busy'] and str(a['text']).lower().strip() not in ('pause','stop','report','results','show results'):
                        raise ValueError('A local job is running; pause it or wait before starting another.')
                    chat(str(a['text'])[:4000])
                elif cmd=='shutdown':
                    require_idle()
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                else:
                    raise ValueError('Unknown action.')
            self.reply({'ok':True})
        except Exception as e:
            self.reply({'error':str(e)},400)

def main():
    ROOT.joinpath('.private').mkdir(exist_ok=True)
    runtime=ROOT/'.private'/'dashboard-runtime.json'
    previous=read_json(runtime,{})
    if previous:
        try:
            import urllib.request
            req=urllib.request.Request(f'http://127.0.0.1:{PORT}/api/state',headers={'X-QA-Token':previous['token']})
            with urllib.request.urlopen(req,timeout=2) as response:
                if response.status==200:
                    prior_version=json.load(response).get('app_version')
                    webbrowser.open(f'http://127.0.0.1:{PORT}/#'+previous['token'])
                    if prior_version!=APP_VERSION:
                        import ctypes
                        ctypes.windll.user32.MessageBoxW(None,
                            'An older Local QA Assistant is still running. In the browser, refresh and click Stop local assistant, then open this Desktop shortcut again. Your cases and login are preserved.',
                            'Update ready — restart the local assistant',0x30)
                    print('Opened the existing local assistant.',flush=True)
                    return
        except Exception:
            pass
    if not DATA['messages']:
        say('I run locally with qwen3:4b-instruct. Import a public Sheet or Excel/CSV without Google sign-in. Sign in only to the QA website, select up to five read-only cases and click Run. Planning/validation happen automatically. Your Sheet stays unchanged.')
    if not DATA['cases'] and DATA['source']=='Not imported' and (ROOT/'data'/'sheet-preview.json').exists():
        preview=read_json(ROOT/'data'/'sheet-preview.json')
        import_records([dict(zip(preview['headers'],row)) for row in preview['rows']],
                       'Read-only preview: Test Cases (first 11 cases, not the full Sheet)',True)
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    qa.save(runtime,{'token':TOKEN,'pid':os.getpid(),'port':PORT})
    # The fragment is not sent to the HTTP server or other websites. API calls
    # require this random per-launch token plus an exact Host/Origin check.
    url=f'http://127.0.0.1:{PORT}/#'+TOKEN
    webbrowser.open(url)
    print('Local assistant opened in your browser. Keep this process running. Ctrl+C stops the dashboard.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.unlink(missing_ok=True)

if __name__=='__main__':
    main()
