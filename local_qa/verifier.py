import json,re
from .models import Blocked,NeedsReview
from .browser import LOCATOR_SCHEMA

CRITERION_SCHEMA={'type':'object','properties':{'id':{'type':'string'},'requirement':{'type':'string'},
 'kind':{'type':'string','enum':['visible','absent','text','value','count','url','authoritative_data']},
 'locator':LOCATOR_SCHEMA,'expected':{'type':'string'},'minimum':{'type':'integer'},'maximum':{'type':'integer'}},
 'required':['id','requirement','kind','locator','expected','minimum','maximum'],'additionalProperties':False}
PLAN_SCHEMA={'type':'object','properties':{'criteria':{'type':'array','maxItems':12,'items':CRITERION_SCHEMA},
 'unverifiable':{'type':'array','items':{'type':'string'}},'suggested_steps':{'type':'string'},
 'case_review':{'type':'string','enum':['Valid','Needs Clarification','Potentially Outdated','Potentially Invalid']}},
 'required':['criteria','unverifiable','suggested_steps','case_review'],'additionalProperties':False}

def validate_criteria(criteria):
    if not isinstance(criteria,list) or not 1<=len(criteria)<=30:raise NeedsReview('Expected result has no bounded atomic criteria.')
    ids=set()
    for c in criteria:
        if not c.get('id') or c['id'] in ids or not c.get('requirement'):raise NeedsReview('Ambiguous criterion identifiers/requirements.')
        ids.add(c['id'])
        if c.get('kind') not in ('visible','absent','text','value','count','url','authoritative_data'):raise NeedsReview('Unsupported assertion kind.')
        if c['kind']=='count' and (type(c.get('minimum')) is not int or type(c.get('maximum')) is not int or c['minimum']<0 or c['maximum']<c['minimum']):
            raise NeedsReview('Invalid count assertion bounds.')
    return criteria

def explicit_criteria(case):
    if case.assertions:return validate_criteria(case.assertions),True
    text=case.expected.strip()
    try:
        data=json.loads(text)
        if isinstance(data,dict) and 'criteria' in data:return validate_criteria(data['criteria']),True
    except (json.JSONDecodeError,TypeError):pass
    # Full-string matching only: never compile one fragment and silently omit
    # the rest of an ordinary business requirement.
    m=re.fullmatch(r'Text "([^"\n]+)" is (visible|absent)\.?',text,re.I)
    if m:
        return [{'id':'C1','requirement':text,'kind':m[2].lower(),'locator':{'by':'test_id','name':'','role':''},
                 'text_locator':m[1],'expected':m[1],'minimum':0,'maximum':0}],True
    m=re.fullmatch(r'URL ends with "([^"\n]+)"\.?',text,re.I)
    if m:return [{'id':'C1','requirement':text,'kind':'url','locator':{},'expected':m[1],'minimum':0,'maximum':0}],True
    return [],False

async def verify(owner,criteria,authoritative,timeout=5000):
    from playwright.async_api import expect,TimeoutError as PWTimeout
    proof=[]
    for c in validate_criteria(criteria):
        entry={'id':c['id'],'requirement':c['requirement'],'status':'Unverified','observed':''}
        try:
            if c['kind']=='authoritative_data':raise Blocked('An authorized backend/inbox/OTP adapter is required for '+c['requirement'])
            if c['kind']=='url':
                ok=owner.page.url.split('?',1)[0].endswith(c['expected'])
                entry.update(status='Verified' if ok else 'Contradicted',observed=owner.page.url.split('?',1)[0])
            else:
                loc=owner.page.get_by_text(c['text_locator'],exact=True) if c.get('text_locator') else owner.locator(c['locator'])
                if c.get('text_locator') and c['kind']=='visible':
                    # The source asks for existence of this text, not uniqueness
                    # (e.g. a nav item and a heading may legitimately share it).
                    await expect(loc.filter(visible=True).first).to_be_visible(timeout=timeout)
                    entry.update(status='Verified',observed='Exact text visible')
                elif c['kind']=='count':
                    observed=await loc.count();ok=c['minimum']<=observed<=c['maximum']
                    entry.update(status='Verified' if ok else 'Contradicted',observed=str(observed))
                elif c['kind']=='absent':
                    await expect(loc).to_be_hidden(timeout=timeout);entry.update(status='Verified',observed='Absent/hidden')
                else:
                    count=await loc.count()
                    if count>1:raise Blocked('Assertion locator is ambiguous.')
                    if c['kind']=='visible':await expect(loc).to_be_visible(timeout=timeout);entry.update(status='Verified',observed='Visible')
                    elif c['kind']=='text':await expect(loc).to_have_text(c['expected'],timeout=timeout);entry.update(status='Verified',observed=(await loc.inner_text())[:800])
                    elif c['kind']=='value':
                        if await loc.get_attribute('type')=='password':raise Blocked('Secret values cannot be exported as assertion evidence.')
                        await expect(loc).to_have_value(c['expected'],timeout=timeout);entry.update(status='Verified',observed=(await loc.input_value())[:800])
        except AssertionError as e:
            # Exact source assertions can establish a contradicted visible/UI
            # expectation. Model-proposed assertions cannot establish app bugs.
            entry.update(status='Contradicted' if authoritative else 'Unverified',observed='Assertion did not meet expected state within the assertion timeout.')
        except Exception as e:entry.update(status='Unverified',observed=str(e)[:500])
        proof.append(entry)
    if not authoritative:return 'NeedsReview',proof
    if any(x['status']=='Unverified' for x in proof):return 'Blocked',proof
    if any(x['status']=='Contradicted' for x in proof):return 'Fail',proof
    return 'Pass',proof
