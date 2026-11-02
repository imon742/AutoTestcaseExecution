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
    def __init__(self,policy,folder,budget):
        self.policy=policy;self.folder=Path(folder);self.budget=budget
        self.folder.mkdir(parents=True,exist_ok=True)
        self.context=None;self.page=None;self.p=None;self.browser=None;self.requests=[]
    async def open(self,auth_state=None,headless=False):
        from playwright.async_api import async_playwright
        self.p=await async_playwright().start()
        self.browser=await self.p.chromium.launch(headless=headless)
        self.context=await self.browser.new_context(storage_state=auth_state,accept_downloads=False)
        async def boundary(route):
            try:self.policy.check_origin(route.request.url)
            except PermissionError:
                self.requests.append({'method':route.request.method,'url':clean_url(route.request.url),'blocked':'origin'})
                await route.abort();return
            # Approved app origins use normal SPA POST/WebSocket behavior. Safety
            # is enforced on permitted user actions/fixtures, not all HTTP methods.
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
        self.page=await self.context.new_page()
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
        return {'url':clean_url(self.page.url),'title':await self.page.title(),
                'elements':[{k:redact(v) if isinstance(v,str) else v for k,v in item.items()} for item in items],
                'visible_text':redact((await self.page.locator('body').inner_text())[:7000]),
                'blocked_origins':self.requests[-5:]}
    async def do(self,case,action):
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
            if action.get('category','read')=='read':
                links=await self.page.locator('a[href]').evaluate_all('(els)=>els.map(e=>e.href)')
                if url not in links and url!=self.page.url:raise PermissionError('Read-only navigation must follow an observed page link.')
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
            if metadata['href']:self.policy.check_origin(urljoin(self.page.url,metadata['href']))
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
