import asyncio,json,re,time
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from .models import Blocked,Policy,redact,clean_url

LOCATOR_SCHEMA={'type':'object','properties':{'by':{'type':'string','enum':['role','label','placeholder','test_id']},
    'role':{'type':'string'},'name':{'type':'string'}},'required':['by','role','name'],'additionalProperties':False}
ACTION_SCHEMA={'type':'object','properties':{
 'kind':{'type':'string','enum':['navigate','click','fill','select','check','uncheck','press','scroll','upload_fixture','wait_for','extract','switch_tab','close_dialog','verify','blocked']},
 'locator':LOCATOR_SCHEMA,'value':{'type':'string'},'category':{'type':'string','enum':['read','create','edit','delete','upload','email','payment']},
 'reason':{'type':'string'},'alternate':LOCATOR_SCHEMA},'required':['kind','locator','value','category','reason'],'additionalProperties':False}

class BrowserOwner:
    def __init__(self,policy,folder,budget,profile_dir=None):
        self.policy=policy;self.folder=Path(folder);self.budget=budget
        self.profile_dir=Path(profile_dir) if profile_dir else None
        self.folder.mkdir(parents=True,exist_ok=True)
        self.context=None;self.page=None;self.p=None;self.browser=None;self.requests=[]
        self.active_case=None;self.observed_navigation_urls=set()
    async def open(self,auth_state=None,headless=False):
        from playwright.async_api import async_playwright
        self.p=await async_playwright().start()
        if self.profile_dir:
            self.profile_dir.mkdir(parents=True,exist_ok=True)
            self.context=await self.p.chromium.launch_persistent_context(str(self.profile_dir),headless=headless,accept_downloads=False,service_workers='block')
            self.browser=None
        else:
            self.browser=await self.p.chromium.launch(headless=headless)
            self.context=await self.browser.new_context(storage_state=auth_state,accept_downloads=False,service_workers='block')
        async def boundary(route):
            try:self.policy.check_origin(route.request.url)
            except PermissionError:
                self.requests.append({'method':route.request.method,'url':clean_url(route.request.url),'blocked':'origin'})
                await route.abort();return
            # A read-only case is structurally incapable of sending a mutation,
            # apart from an explicitly configured authentication endpoint.
            if self.active_case and set(self.active_case.categories)=={'read'}:
                method=route.request.method.upper()
                if method not in ('GET','HEAD','OPTIONS') and not self.policy.session_auth_allowed(route.request.url):
                    self.requests.append({'method':method,'url':clean_url(route.request.url),'blocked':'read-only method'})
                    await route.abort();return
            await route.continue_()
        await self.context.route('**/*',boundary)
        async def socket_boundary(socket):
            try:
                self.policy.check_origin(socket.url.replace('wss://','https://',1).replace('ws://','http://',1))
                socket.connect_to_server()
            except PermissionError:
                self.requests.append({'method':'WEBSOCKET','url':clean_url(socket.url),'blocked':'origin'})
                await socket.close(code=1008,reason='Outside approved QA origins')
        await self.context.route_web_socket('**/*',socket_boundary)
        self.page=next((p for p in self.context.pages if not p.is_closed()),None) or await self.context.new_page()
        return self
    def locator(self,spec):
        by=spec.get('by');name=spec.get('name','')
        if not name or len(name)>250:raise Blocked('Missing or oversized locator name.')
        if by=='role':
            if not re.fullmatch(r'[a-z]+',spec.get('role','')):raise Blocked('Invalid accessible role.')
            return self.page.get_by_role(spec['role'],name=name,exact=True)
        if by=='label':return self.page.get_by_label(name,exact=True)
        if by=='placeholder':return self.page.get_by_placeholder(name,exact=True)
        if by=='test_id':return self.page.get_by_test_id(name)
        raise Blocked('Only role, label, placeholder and test-id locators are allowed.')
    async def observe(self):
        # DOM-derived observation excludes entered values/passwords. No cookies,
        # storage, request headers or hidden tokens are inspected for the model.
        items=await self.page.evaluate('''() => [...document.querySelectorAll('a,button,input,select,textarea,h1,h2,h3,[role],label')]
          .filter(e=>e.getClientRects().length).slice(0,100).map(e=>({
            tag:e.tagName.toLowerCase(),role:e.getAttribute('role')||'',
            name:(e.getAttribute('aria-label')||e.innerText||e.getAttribute('placeholder')||'').slice(0,140),
            label:e.labels?.[0]?.innerText||'',type:e.getAttribute('type')||'',
            test_id:e.getAttribute('data-testid')||'',href:e.tagName==='A'?e.getAttribute('href'):'',
            disabled:!!e.disabled,secret:e.type==='password'||/password|token|secret|otp/i.test(e.name||'')
          })).filter(e=>!e.secret)''')
        await self.capture_navigation_landmarks()
        return {'url':clean_url(self.page.url),'title':await self.page.title(),
                'elements':[{k:redact(v) if isinstance(v,str) else v for k,v in item.items()} for item in items],
                'visible_text':redact((await self.page.locator('body').inner_text())[:7000]),
                'blocked_origins':self.requests[-5:]}
    async def capture_navigation_landmarks(self):
        landmarks=await self.page.locator('nav a[href], [role="navigation"] a[href], [aria-label*="breadcrumb" i] a[href]').evaluate_all('(els)=>els.map(e=>e.href)')
        self.observed_navigation_urls.update(str(x) for x in landmarks)
    async def do(self,case,action):
        self.active_case=case
        self.policy.check_fixture_origin(case,self.page.url)
        kind=action.get('kind')
        allowed={'navigate','click','fill','select','check','uncheck','press','scroll','upload_fixture','wait_for','extract','switch_tab','close_dialog','verify','blocked'}
        if kind not in allowed:raise Blocked('Unknown action kind.')
        if kind=='blocked':raise Blocked(action.get('reason','Model cannot proceed.'))
        if kind=='verify':return {'kind':'verify'}
        if kind=='navigate':
            url=urljoin(self.page.url,action.get('value',''));self.policy.check_origin(url)
            if re.search(r'/(logout|delete|remove|purge)(?:[/?]|$)',url,re.I):
                raise PermissionError('Mutating endpoint navigation is not permitted.')
            self.policy.check_action(case,action)
            await self.capture_navigation_landmarks()
            if action.get('category','read')=='read' and not self.policy.approved_read_url(url,self.observed_navigation_urls):
                raise PermissionError('Read-only navigation needs an approved path or observed navigation landmark.')
            response=await self.page.goto(url,wait_until='domcontentloaded',timeout=self.budget.action_ms)
            if response and response.status>=400:raise Blocked('Navigation returned HTTP '+str(response.status))
            return {'kind':kind,'url':clean_url(self.page.url)}
        if kind=='switch_tab':
            tabs=[p for p in self.context.pages if not p.is_closed()]
            matches=[p for p in tabs if action.get('value') in (clean_url(p.url),await p.title())]
            if len(matches)!=1:raise Blocked('Tab choice is ambiguous.')
            self.policy.check_origin(matches[0].url);self.page=matches[0]
            return {'kind':kind,'url':clean_url(self.page.url)}
        if kind=='close_dialog':
            self.policy.check_action(case,action)
            await self.page.keyboard.press('Escape');return {'kind':kind}
        if kind=='scroll':
            self.policy.check_action(case,action)
            amount=max(-900,min(900,int(action.get('value','500'))));await self.page.mouse.wheel(0,amount)
            return {'kind':kind,'pixels':amount}
        loc=self.locator(action.get('locator',{}))
        if await loc.count()!=1:raise Blocked('Locator is missing or ambiguous.')
        readonly_field=False
        if kind in ('fill','select','check','uncheck','press'):
            metadata=await loc.evaluate('(e)=>({type:e.type||"",role:e.getAttribute("role")||"",name:e.getAttribute("placeholder")||e.getAttribute("aria-label")||""})')
            if metadata['type']=='password':raise PermissionError('Password fields are reserved for the deterministic login adapter.')
            readonly_field=(metadata['type']=='search' or metadata['role']=='searchbox' or re.search(r'\b(search|filter)\b',metadata['name'],re.I) is not None)
        if kind=='click':
            metadata=await loc.evaluate('(e)=>({tag:e.tagName,role:e.getAttribute("role")||"",text:e.innerText||"",href:e.getAttribute("href")||""})')
            if action.get('category')=='read' and metadata['tag']!='A' and metadata['role'] not in ('tab','menuitem'):
                if not re.fullmatch(r'(search|filter|filters|apply filters|next|previous|back|cancel|close|view(?: details)?|details|show.*|expand.*|admin settings)',metadata['text'].strip(),re.I):
                    raise PermissionError('An unknown business button cannot be treated as read-only.')
            if metadata['href']:
                target=urljoin(self.page.url,metadata['href']);self.policy.check_origin(target)
                await self.capture_navigation_landmarks()
                if action.get('category')=='read' and not self.policy.approved_read_url(target,self.observed_navigation_urls):
                    raise PermissionError('Read-only links must be approved paths or observed navigation landmarks.')
        self.policy.check_action(case,action,readonly_field)
        timeout=self.budget.action_ms
        if kind=='click':await loc.click(timeout=timeout)
        elif kind=='fill':await loc.fill(action.get('value',''),timeout=timeout)
        elif kind=='select':await loc.select_option(label=action.get('value',''),timeout=timeout)
        elif kind=='check':await loc.check(timeout=timeout)
        elif kind=='uncheck':await loc.uncheck(timeout=timeout)
        elif kind=='press':
            if action.get('value') not in ('Enter','Tab','Escape','ArrowDown','ArrowUp'):raise Blocked('Unsupported key.')
            if action.get('value')=='Enter' and action.get('category')=='read' and not readonly_field:
                raise PermissionError('Enter may submit a business form; category approval required.')
            await loc.press(action['value'],timeout=timeout)
        elif kind=='wait_for':await loc.wait_for(state='visible',timeout=timeout)
        elif kind=='extract':return {'kind':kind,'text':redact((await loc.inner_text())[:2000])}
        elif kind=='upload_fixture':
            root=Path(self.policy.upload_root).resolve();path=(root/action.get('value','')).resolve()
            if not self.policy.upload_root or not path.is_relative_to(root) or not path.is_file():raise PermissionError('Upload fixture is outside the approved folder.')
            await loc.set_input_files(str(path),timeout=timeout)
        else:raise Blocked('Action could not execute.')
        return {'kind':kind,'locator':action.get('locator'),'value':redact(action.get('value',''))[:300]}
    async def evidence_start(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.requests=[]
        await self.context.tracing.start(screenshots=True,snapshots=True,sources=False)
    async def evidence_end(self):
        files=[]
        try:
            p=self.folder/'observed.png';await self.page.screenshot(path=str(p),full_page=True,timeout=10000);files.append(('screenshot',p))
        except Exception:pass
        try:
            p=self.folder/'trace.zip';await asyncio.wait_for(self.context.tracing.stop(path=str(p)),15);files.append(('trace',p))
        except Exception:pass
        for p in self.folder.glob('before-auth-*.zip'):files.append(('trace',p))
        return files
    async def close(self):
        for obj in (self.context,self.browser,self.p):
            if obj:
                try:await asyncio.wait_for(obj.stop() if obj is self.p else obj.close(),10)
                except Exception:pass
