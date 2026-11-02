from dataclasses import dataclass,field,asdict
import hashlib,json,re
from urllib.parse import urlsplit,urlunsplit

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def clean_url(url):
    try:
        u=urlsplit(str(url));return urlunsplit((u.scheme,u.netloc,u.path,'',''))
    except Exception:return '[invalid URL]'

SECRET_RE=re.compile(r'(?i)(?:bearer\s+\S+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|(?:password|access_token|refresh_token|api_key|jwt)\s*[:=]\s*[^\s,;]+)')
def redact(text):
    text=re.sub(r'(?i)(["\']?(?:password|access_token|refresh_token|api_key|jwt|secret)["\']?\s*[:=]\s*)["\']?[^\s,;}"\']+',r'\1[REDACTED]',str(text))
    text=SECRET_RE.sub('[REDACTED]',text)
    return re.sub(r'https?://[^\s<>"\']+',lambda m:clean_url(m.group()),text)

@dataclass
class Case:
    case_id:str
    scenario_id:str=''
    title:str=''
    preconditions:str=''
    test_data:str=''
    steps:str=''
    expected:str=''
    source_status:str=''
    source_actual:str=''
    source_row:int=0
    source_sheet:str=''
    source_hash:str=''
    categories:list[str]=field(default_factory=lambda:['read'])
    fixture_id:str=''
    assertions:list=field(default_factory=list)
    def inputs(self):
        return {k:getattr(self,k) for k in ('case_id','scenario_id','title','preconditions','test_data','steps','expected','categories','fixture_id','assertions')}
    def seal(self):self.source_hash=fingerprint(self.inputs());return self
    def dict(self):return asdict(self)
    @classmethod
    def from_dict(cls,d):return cls(**{k:v for k,v in d.items() if k in cls.__dataclass_fields__})

def select_scope(cases,scope='non_pass',scenario='',selected=None):
    allowed={'non_pass','all','failed','blocked','selected'}
    if scope not in allowed:raise ValueError('Unknown case scope.')
    ids=set(selected or [])
    out=[]
    for c in cases:
        status=c.source_status.strip().casefold()
        if scenario and c.scenario_id!=scenario:continue
        if scope=='non_pass' and status=='pass':continue
        if scope=='failed' and status not in ('fail','failed'):continue
        if scope=='blocked' and status not in ('blocked','needsreview','needs review'):continue
        if scope=='selected' and c.case_id not in ids:continue
        out.append(c)
    return out

@dataclass
class Policy:
    origins:list[str]
    categories:list[str]=field(default_factory=lambda:['read'])
    write_case_ids:list[str]=field(default_factory=list)
    # Fixture IDs are intentionally bound to an origin.  A label alone must
    # never authorize a mutation against a different QA environment.
    fixture_ids:dict[str,str]=field(default_factory=dict)
    upload_root:str=''
    allow_writeback:bool=False
    allow_all_origins:bool=False
    approved_read_paths:list[str]=field(default_factory=list)
    session_auth_urls:list[str]=field(default_factory=list)
    def __post_init__(self):
        # Old local configs used a list.  Keep them readable but deliberately
        # unusable for writes until the user supplies an origin-bound mapping.
        if isinstance(self.fixture_ids,list):self.fixture_ids={x:'' for x in self.fixture_ids}
    def check_case(self,case):
        writes=set(case.categories)-{'read'}
        origin=f'{urlsplit(case.start_url if hasattr(case,"start_url") else "").scheme}://{urlsplit(case.start_url if hasattr(case,"start_url") else "").netloc}'
        # Cases normally inherit their run start URL; callers may attach an
        # explicit start_url only for fixture-specific runs.
        if not origin or origin=='://':origin=''
        fixture_origin=self.fixture_ids.get(case.fixture_id)
        if writes and (not writes.issubset(self.categories) or case.case_id not in self.write_case_ids
                       or not case.fixture_id or case.fixture_id not in self.fixture_ids
                       or not fixture_origin):
            raise PermissionError('Specific case, fixture and action categories are not approved for side effects.')
        if writes and origin and fixture_origin!=origin:
            raise PermissionError('Approved fixture is bound to a different origin.')
    def check_origin(self,url):
        u=urlsplit(url)
        if u.scheme not in ('http','https') or u.username or u.password:
            raise PermissionError('Invalid navigation destination.')
        if not self.allow_all_origins and f'{u.scheme}://{u.netloc}' not in self.origins:
            raise PermissionError('Destination is outside the approved origins.')
    def approved_read_url(self,url,observed_landmarks=()):
        self.check_origin(url)
        u=urlsplit(url)
        origin=f'{u.scheme}://{u.netloc}'
        if origin not in self.origins:return False
        if url in observed_landmarks:return True
        return u.path in self.approved_read_paths
    def session_auth_allowed(self,url):
        return clean_url(url) in {clean_url(x) for x in self.session_auth_urls}
    def check_fixture_origin(self,case,url):
        if set(case.categories)-{'read'}:
            origin=f'{urlsplit(url).scheme}://{urlsplit(url).netloc}'
            if self.fixture_ids.get(case.fixture_id)!=origin:
                raise PermissionError('Approved fixture is not valid for the current origin.')
    def check_action(self,case,action,readonly_field=False):
        self.check_case(case)
        category=action.get('category','read')
        if category!='read':
            if category not in case.categories or category not in self.categories:
                raise PermissionError('Action category is not approved for this case.')
            if case.case_id not in self.write_case_ids or case.fixture_id not in self.fixture_ids:
                raise PermissionError('Action lacks a specific approved fixture.')
        if action.get('kind') in ('fill','select','check','uncheck','upload_fixture') and not readonly_field and category=='read':
            raise PermissionError('A business field change cannot be labeled read-only.')
        if action.get('kind')=='upload_fixture' and category!='upload':
            raise PermissionError('Upload category approval is required.')
        name=action.get('locator',{}).get('name','')
        if action.get('kind')=='click' and category=='read':
            if re.search(r'\b(create|save|submit|delete|remove|send|invite|pay|purchase|confirm|update|register)\b',name,re.I):
                raise PermissionError('This click is not a read-only navigation action.')

@dataclass
class Budget:
    max_actions:int=20
    case_seconds:int=240
    model_seconds:int=90
    action_ms:int=10000
    locator_retries:int=1

class Blocked(Exception):pass
class NeedsReview(Blocked):pass
class AuthRequired(Blocked):pass
