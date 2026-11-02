import asyncio,json,threading,time
from pathlib import Path
from .models import Case,Policy,Budget,Blocked,NeedsReview,AuthRequired,redact
from .browser import BrowserOwner,ACTION_SCHEMA
from .verifier import explicit_criteria,validate_criteria,verify,PLAN_SCHEMA
from .auth import bootstrap,authenticate
from .ollama import Ollama

class Supervisor:
    def __init__(self,store,output,vault,model_factory=None,fixtures=None):
        self.store=store;self.output=Path(output);self.vault=vault
        self.model_factory=model_factory or (lambda cfg:Ollama(**cfg))
        self.fixtures=fixtures
        self.pause=threading.Event();self.stop=threading.Event()
    def public_case(self,case):
        # Credential/test-data secret values are never placed in model context.
        text=redact(case.test_data)
        if any(x in case.test_data.casefold() for x in ('password','token','secret','api_key','credential')):
            text='[Credential-like test data withheld; configure a local vault/fixture adapter.]'
        return {'case_id':case.case_id,'title':redact(case.title),'preconditions':redact(case.preconditions),
                'steps':redact(case.steps),'expected':redact(case.expected),'test_data':text,
                'approved_fixture_id':case.fixture_id}
    async def run(self,run_id):
        run=self.store.run(run_id);cfg=run['config'];policy=Policy(**cfg['policy']);budget=Budget(**cfg.get('budget',{}))
        model=self.model_factory(cfg['ollama'])
        await asyncio.to_thread(model.validate_model)
        self.store.state(run_id,'Running');self.pause.clear();self.stop.clear()
        owner=None
        try:
            profile=cfg.get('browser_profile')
            auth_state=cfg.get('auth_state')
            owner=await BrowserOwner(policy,self.output/run_id/'browser',budget,profile).open(auth_state=auth_state if auth_state and Path(auth_state).is_file() else None,headless=cfg.get('headless',False))
            while not self.pause.is_set() and not self.stop.is_set():
                case=self.store.next_case(run_id)
                if not case:break
                attempt=self.store.begin(run_id,case);folder=self.output/run_id/attempt
                status='Blocked';actual='Execution could not establish expected results.';details={};evidence=[]
                try:
                    policy.check_case(case)
                    if self.fixtures and cfg['start_url'].startswith(self.fixtures.origin+'/'):self.fixtures.reset()
                    # One persistent Playwright context owns the full run. Case
                    # boundaries reset only evidence/checkpoint state, not login.
                    owner.folder=folder
                    self.store.event(run_id,'case','Starting '+case.case_id)
                    status,actual,details=await asyncio.wait_for(self.execute_case(owner,case,cfg,model,budget),budget.case_seconds)
                except asyncio.TimeoutError:
                    status='NeedsReview' if set(case.categories)-{'read'} else 'Blocked'
                    actual='Side effect may have partly applied; reconcile the approved fixture before any new run.' if status=='NeedsReview' else 'Case time budget exceeded; next case will continue.'
                except AuthRequired as e:status='Blocked';actual='AuthRequired: '+str(e)
                except NeedsReview as e:status='NeedsReview';actual=str(e)
                except Exception as e:status='Blocked';actual=redact(type(e).__name__+': '+str(e))[:2000]
                finally:
                    if owner:
                        evidence=await owner.evidence_end()
                self.store.commit(attempt,status,actual,details,evidence,policy.allow_writeback)
                if self.fixtures and cfg['start_url'].startswith(self.fixtures.origin+'/'):self.fixtures.reset()
                self.store.event(run_id,'result',case.case_id+': '+status+' — '+actual)
                if policy.allow_writeback:
                    try:
                        from .writers import flush_writebacks
                        await asyncio.to_thread(flush_writebacks,self.store,run_id)
                    except Exception as e:self.store.event(run_id,'sync','Local result committed; writeback pending: '+str(e))
            self.store.state(run_id,'Stopped' if self.stop.is_set() else 'Paused' if self.pause.is_set() else 'Completed')
        finally:
            if owner:await owner.close()
            if self.store.run(run_id)['state']=='Running':self.store.state(run_id,'Paused')
    async def execute_case(self,owner,case,cfg,model,budget):
        # Authentication may fill a password.  It always happens before trace
        # collection; replay repair follows the same rule below.
        await bootstrap(owner,cfg,self.vault)
        await owner.evidence_start(owner.folder)
        criteria,authoritative=explicit_criteria(case)
        contract=cfg.get('contracts',{}).get(case.source_hash)
        precondition_proof=[]
        unresolved_precondition=False
        if case.preconditions.strip():
            precriteria=(contract or {}).get('preconditions')
            if not precriteria:
                precriteria,known=explicit_criteria(Case(case.case_id,expected=case.preconditions))
                if not known:
                    if set(case.categories)-{'read'}:raise NeedsReview('Preconditions need an explicit verifiable mapping before changing data.')
                    unresolved_precondition=True
                    precondition_proof=[{'status':'Unverified','requirement':case.preconditions,'observed':'Read-only exploration permitted; precondition not assumed true.'}]
            if not unresolved_precondition:
                prestatus,precondition_proof=await verify(owner,precriteria,True)
                if prestatus!='Pass':raise Blocked('Required precondition is not established: '+json.dumps(precondition_proof))
        prescribed=None
        if contract:
            criteria=validate_criteria(contract['criteria']);authoritative=True;prescribed=contract['actions']
        else:
            try:
                raw=json.loads(case.steps)
                if isinstance(raw,list) and raw and all(isinstance(a,dict) and 'kind' in a for a in raw):prescribed=raw
            except (json.JSONDecodeError,TypeError):pass
        if prescribed:
            import re
            for step in prescribed:
                if step.get('kind')=='fill' and re.search(r'password|token|secret|otp|card|security code',step.get('locator',{}).get('name',''),re.I):
                    raise Blocked('Sensitive field values must use an authorized deterministic credential/sandbox adapter, not a model action.')
        # Passing assertions alone do not establish that unstructured source
        # steps were followed. Unmapped business prose remains NeedsReview.
        source_coverage=authoritative and prescribed is not None and not unresolved_precondition
        case_data=self.public_case(case)
        review={'case_review':'Valid','suggested_steps':'','unverifiable':[]}
        if not authoritative:
            plan=await model.json('Decompose EVERY expected-result obligation into atomic assertions. Do not drop backend/data requirements; mark those authoritative_data. Suggest clearer steps separately. Never label uncertainty as verified.\nCASE='+json.dumps(case_data)+'\nPAGE='+json.dumps(await owner.observe()),PLAN_SCHEMA)
            criteria=validate_criteria(plan['criteria']);review=plan
        flow_key=case.source_hash+'|'+cfg['start_url']
        flow=self.store.flow(flow_key) if cfg.get('replay_first',True) and authoritative else None
        actions=[];observations=[];repair=False
        if flow and source_coverage:
            try:
                for a in flow['actions']:await owner.do(case,a);actions.append(a)
                status,proof=await verify(owner,criteria,True)
                if status=='Pass':return 'Pass','Verified replay: all source assertions passed.',{'actions':actions,'criteria':proof,'replay':True}
                repair=True
            except Exception:repair=True
            # Repair never replays already committed business side effects.
            if set(case.categories)-{'read'}:raise NeedsReview('A mutating replay failed. Evidence retained; automatic repetition of side effects is prohibited.')
            await owner.context.tracing.stop(path=str(owner.folder/'before-auth-repair.zip'))
            await bootstrap(owner,cfg,self.vault)
            await owner.context.tracing.start(screenshots=True,snapshots=True,sources=False)
            owner.requests.append({'event':'trace paused for deterministic authentication repair'})
            actions=[]
        for index in range(budget.max_actions):
            if self.stop.is_set():raise Blocked('Stop requested during case; result/evidence recorded.')
            snapshot=await owner.observe()
            if prescribed is not None and len(actions)>=len(prescribed):break
            observations.append(snapshot)
            prompt=('Perform the next single permitted UI action for this case. Use actual observed role/name/label/placeholder/test-id; do not invent locators. '
                    'Return verify only after performing all required steps; blocked if a prerequisite/data source is unavailable. '
                    'Use exact category read/create/edit/delete/upload/email/payment and never relabel a write as read. '
                    'Allowed actions are in the schema. No generated code, secrets, external model calls or unrelated tasks. '
                    'CASE='+json.dumps(case_data)+'\nATOMIC CRITERIA='+json.dumps(criteria)+
                    '\nRECENT ACTIONS='+json.dumps(actions[-5:])+'\nCURRENT PAGE='+json.dumps(snapshot)+
                    ('\nREQUIRED NEXT SOURCE ACTION='+json.dumps(prescribed[len(actions)]) if prescribed is not None else ''))
            image=await owner.page.screenshot(mask=[owner.page.locator('input[type=password],input[autocomplete="one-time-code"],input[name*="token" i],input[name*="secret" i]')]) if cfg['ollama'].get('vision') else None
            action=await model.json(prompt,ACTION_SCHEMA,image)
            if prescribed is not None:
                required=prescribed[len(actions)]
                signature=lambda a:{k:a.get(k,'') for k in ('kind','locator','value','category')}
                if signature(action)!=signature(required):
                    action=await model.json(prompt+'\nThe previous proposal did not match the source action. Return that exact permitted action.',ACTION_SCHEMA,image)
                    if signature(action)!=signature(required):raise Blocked('Local model could not execute the exact source action within retry budget.')
            if action.get('kind')=='verify':break
            if action.get('kind')=='blocked':raise Blocked(action.get('reason','Cannot proceed.'))
            try:result=await owner.do(case,action)
            except Blocked:
                alternate=action.get('alternate')
                if not alternate or budget.locator_retries<1:raise
                action={**action,'locator':alternate};result=await owner.do(case,action)
            login=cfg.get('auth',{}).get('login_locator')
            if login and await owner.locator(login).is_visible():
                # Never capture password entry/credential POSTs in traces.
                await owner.context.tracing.stop(path=str(owner.folder/'before-auth-refresh.zip'))
                await authenticate(owner,cfg,self.vault)
                await owner.context.tracing.start(screenshots=True,snapshots=True,sources=False)
                owner.requests.append({'event':'deterministic session refresh; tracing paused for credentials'})
            actions.append(action)
            if prescribed is not None and len(actions)>=len(prescribed):break
        else:raise Blocked('Maximum browser action budget reached; no unverified Pass recorded.')
        status,proof=await verify(owner,criteria,source_coverage)
        if review.get('unverifiable') and status=='Pass':status='Blocked'
        details={'actions':actions,'criteria':proof,'preconditions':precondition_proof,'criteria_authoritative':authoritative,'source_step_coverage':source_coverage,
                 'case_review':review.get('case_review'),'suggested_steps':review.get('suggested_steps'),
                 'unverifiable':review.get('unverifiable'),'repair':repair,'observation_count':len(observations)}
        actual='; '.join(x['id']+' '+x['status']+': '+redact(x['observed']) for x in proof)
        if not source_coverage:actual='NeedsReview: source step/assertion mapping is not independently established; executed checks are evidence, not a full expected-result certification. '+actual
        if status=='Pass':self.store.put_flow(flow_key,actions,criteria)
        return status,actual,details
