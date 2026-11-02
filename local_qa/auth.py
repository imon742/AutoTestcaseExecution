"""Deterministic authentication; passwords only in the OS vault and login fields."""
import asyncio,ctypes,json,os
from ctypes import wintypes
from urllib.parse import urlsplit
from .models import AuthRequired,Blocked

class WindowsVault:
    def __init__(self):
        if os.name!='nt':raise Blocked('Windows Credential Manager is required on this platform.')
        class CREDENTIAL(ctypes.Structure):
            _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
                ('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),
                ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
                ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]
        self.C=CREDENTIAL;self.api=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
        self.api.CredWriteW.argtypes=[ctypes.POINTER(CREDENTIAL),wintypes.DWORD];self.api.CredWriteW.restype=wintypes.BOOL
        self.api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
        self.api.CredReadW.restype=wintypes.BOOL;self.api.CredFree.argtypes=[ctypes.c_void_p]
    def save(self,name,username,password):
        blob=password.encode('utf-16-le');buf=(ctypes.c_ubyte*len(blob)).from_buffer_copy(blob)
        c=self.C();c.Type=1;c.TargetName='LocalQA/'+name;c.UserName=username;c.Persist=2
        c.CredentialBlobSize=len(blob);c.CredentialBlob=ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))
        if not self.api.CredWriteW(ctypes.byref(c),0):raise Blocked('Windows Credential Manager could not save this credential.')
    def get(self,name):
        ptr=ctypes.POINTER(self.C)()
        if not self.api.CredReadW('LocalQA/'+name,1,0,ctypes.byref(ptr)):raise AuthRequired('No local OS-vault credential configured.')
        try:
            c=ptr.contents
            return {'username':c.UserName or '', 'password':ctypes.string_at(c.CredentialBlob,c.CredentialBlobSize).decode('utf-16-le')}
        finally:self.api.CredFree(ptr)

class LocalVault:
    """Use Windows Credential Manager when available, otherwise keyring.

    The fallback stores only OS-managed credential references; it never writes a
    password into project configuration, SQLite, or a report.
    """
    def __init__(self):
        self.windows = WindowsVault() if os.name == 'nt' else None
    def save(self,name,username,password):
        if self.windows:return self.windows.save(name,username,password)
        try:
            import keyring
            keyring.set_password('LocalQA/'+name, 'username', username)
            keyring.set_password('LocalQA/'+name, 'password', password)
        except Exception as e:raise Blocked('OS credential vault/keyring could not save this credential.') from e
    def get(self,name):
        if self.windows:return self.windows.get(name)
        try:
            import keyring
            username=keyring.get_password('LocalQA/'+name, 'username')
            password=keyring.get_password('LocalQA/'+name, 'password')
        except Exception as e:raise AuthRequired('No local OS-vault credential configured.') from e
        if username is None or password is None:raise AuthRequired('No local OS-vault credential configured.')
        return {'username':username,'password':password}

async def authenticate(owner,config,vault):
    """Run only configured login steps. No credential values reach the model/log."""
    auth=config.get('auth',{})
    if not auth or auth.get('mode')=='none':return
    page=owner.page
    ready=auth.get('ready_locator')
    if ready:
        try:
            if await owner.locator(ready).is_visible():return
        except Exception:pass
    if await page.get_by_text('CAPTCHA',exact=False).count() or await page.locator('input[autocomplete="one-time-code"]').count():
        raise AuthRequired('MFA/CAPTCHA requires the user; no bypass was attempted.')
    credential=vault.get(auth.get('credential_name','default'))
    try:
        for step in auth.get('steps',[]):
            loc=owner.locator(step['locator'])
            if step['kind']=='fill':
                reference=step.get('credential')
                if reference not in ('username','password'):raise AuthRequired('Invalid deterministic login credential reference.')
                await loc.fill(credential[reference],timeout=10000)
            elif step['kind']=='click':await loc.click(timeout=10000)
            else:raise AuthRequired('Unsupported deterministic login step.')
        if ready:await owner.locator(ready).wait_for(state='visible',timeout=15000)
        else:raise AuthRequired('Configure an explicit logged-in ready locator.')
    except AuthRequired:raise
    except Exception as e:raise AuthRequired('Ordinary login did not reach its configured ready state; inspect MFA, credential expiry or selectors.') from e
    finally:credential.clear()

async def bootstrap(owner,config,vault):
    start=config['start_url'];owner.policy.check_origin(start)
    await owner.page.goto(start,wait_until='domcontentloaded',timeout=25000)
    await authenticate(owner,config,vault)
    handoff=config.get('handoff',{})
    if handoff:
        loc=owner.locator(handoff['locator']);before=set(owner.context.pages)
        await loc.click(timeout=10000)
        destination=handoff['destination_origin']
        for _ in range(60):
            candidates=[p for p in owner.context.pages if (p is owner.page or p not in before)
                        and f'{urlsplit(p.url).scheme}://{urlsplit(p.url).netloc}'==destination]
            if candidates:
                owner.page=candidates[-1]
                if urlsplit(owner.page.url).path.rstrip('/')!='/login':break
            await asyncio.sleep(.5)
        else:raise AuthRequired('Portal handoff did not complete; human authentication may be required.')
        await owner.page.wait_for_load_state('domcontentloaded',timeout=20000)
        if handoff.get('ready_locator'):await owner.locator(handoff['ready_locator']).wait_for(state='visible',timeout=15000)
