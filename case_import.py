"""Anonymous Google Sheets reads and bounded local Excel/CSV imports. No login cookies."""
import csv
import io
import posixpath
import re
import urllib.parse
import urllib.request
import urllib.error
import zipfile
from xml.etree import ElementTree as ET

MAX_BYTES=5_000_000

def records_from_grid(grid):
    aliases={'testcaseid':'Test Case ID','caseid':'Test Case ID','id':'Test Case ID',
             'teststeps':'Test Steps','steps':'Test Steps','instructions':'Test Steps',
             'expectedresult':'Expected Result','expectedresults':'Expected Result','expected':'Expected Result',
             'testcase':'Test Case','title':'Test Case','precondition':'Precondition',
             'preconditions':'Precondition','status':'Status','actualresult':'Actual Result'}
    for i,row in enumerate(grid[:30]):
        headers=[aliases.get(re.sub(r'[^a-z0-9]','',str(v).lower()),str(v).strip()) for v in row]
        if {'Test Case ID','Test Steps','Expected Result'}.issubset(headers):
            if len([x for x in headers if x])!=len(set(x for x in headers if x)):
                raise ValueError('Duplicate column headings are ambiguous.')
            return [dict(zip(headers,list(r)+['']*max(0,len(headers)-len(r)))) for r in grid[i+1:] if any(str(x).strip() for x in r)]
    raise ValueError('Could not find Case ID, Test Steps and Expected Result headings in the first 30 rows.')

def csv_records(data):
    if len(data)>MAX_BYTES:
        raise ValueError('File exceeds the 5 MB import limit.')
    text=data.decode('utf-8-sig')
    if '<html' in text[:500].lower() or '<!doctype html' in text[:500].lower():
        raise ValueError('Google returned a login/web page, not public case data. Use an accessible Sheet or upload Excel/CSV; no login will be requested.')
    try:
        dialect=csv.Sniffer().sniff(text[:8000],delimiters=',;\t')
    except csv.Error:
        dialect=csv.excel
    return records_from_grid(list(csv.reader(io.StringIO(text),dialect)))

class GoogleOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        u=urllib.parse.urlsplit(newurl)
        if u.scheme!='https' or not (u.hostname=='docs.google.com' or (u.hostname or '').endswith('.googleusercontent.com')):
            raise ValueError('Public import redirected outside Google export hosts. No sign-in was attempted.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def public_sheet(url,tab='Test Cases',gid=None):
    url=re.sub(r'^http://docs\.google\.com/', 'https://docs.google.com/',url.strip())
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname!='docs.google.com' or u.username or u.password:
        raise ValueError('Enter a public https://docs.google.com/spreadsheets/... link.')
    match=re.fullmatch(r'/spreadsheets/d/([A-Za-z0-9_-]+)(?:/edit)?/?',u.path)
    published=re.fullmatch(r'/spreadsheets/d/e/([A-Za-z0-9_-]+)/pubhtml',u.path)
    if match:
        # Prefer the requested tab's actual name over the edit URL's stale gid=0.
        query={'tqx':'out:csv','sheet':tab} if tab else {'tqx':'out:csv','gid':str(int(gid or 0))}
        export='https://docs.google.com/spreadsheets/d/'+match.group(1)+'/gviz/tq?'+urllib.parse.urlencode(query)
    elif published:
        export='https://docs.google.com/spreadsheets/d/e/'+published.group(1)+'/pub?'+urllib.parse.urlencode({'output':'csv','gid':str(int(gid or 0))})
    else:
        raise ValueError('Use a standard Google Sheet edit link or a published pubhtml link.')
    # A fresh opener has no Google cookies or credentials.
    opener=urllib.request.build_opener(GoogleOnlyRedirect())
    try:
        with opener.open(urllib.request.Request(export,headers={'User-Agent':'Local-QA-ReadOnly/1.0'}),timeout=30) as response:
            raw=response.read(MAX_BYTES+1)
    except urllib.error.HTTPError as e:
        raise ValueError(f'Anonymous Sheet access returned HTTP {e.code}. Import your accessible Excel/CSV instead. No Google sign-in was requested.') from e
    return csv_records(raw)

def excel_records(data,tab='Test Cases'):
    if len(data)>MAX_BYTES:
        raise ValueError('Excel file exceeds the 5 MB import limit.')
    try:
        z=zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError('Use an .xlsx file, not legacy .xls or a renamed CSV.') from e
    with z:
        info=z.infolist()
        if len(info)>2000 or sum(x.file_size for x in info)>25_000_000:
            raise ValueError('Expanded Excel workbook is too large to import safely.')
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            strings=[''.join(x.itertext()) for x in root.findall('s:si',ns)]
        book=ET.fromstring(z.read('xl/workbook.xml'))
        sheets=book.findall('s:sheets/s:sheet',ns)
        chosen=next((s for s in sheets if s.get('name','').casefold()==tab.casefold()),None)
        if chosen is None:
            if len(sheets)==1:chosen=sheets[0]
            else:raise ValueError('Tab not found. Available Excel tabs: '+', '.join(s.get('name','') for s in sheets))
        rid=chosen.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relation=next((r for r in rels if r.get('Id')==rid),None)
        if relation is None or relation.get('TargetMode')=='External':
            raise ValueError('Workbook worksheet relationship is invalid.')
        target=relation.get('Target','')
        path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        if not path.startswith('xl/worksheets/') or '..' in path.split('/'):
            raise ValueError('Invalid worksheet path.')
        root=ET.fromstring(z.read(path));grid=[]
        for row in root.findall('s:sheetData/s:row',ns):
            values={}
            for cell in row.findall('s:c',ns):
                ref=cell.get('r','A1');col=0
                for letter in re.match(r'[A-Z]+',ref).group():col=col*26+ord(letter)-64
                if col>200:continue
                v=cell.find('s:v',ns);text=v.text or '' if v is not None else ''
                if cell.get('t')=='s':text=strings[int(text)] if text else ''
                elif cell.get('t')=='inlineStr':text=''.join(cell.find('s:is',ns).itertext())
                values[col-1]=text
            if values:grid.append([values.get(i,'') for i in range(max(values)+1)])
            if len(grid)>20000:raise ValueError('Too many worksheet rows.')
        return records_from_grid(grid)
