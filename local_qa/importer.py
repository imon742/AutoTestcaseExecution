import csv,io,json,re
from pathlib import Path
from .models import Case,Blocked,redact

ALIASES={
 'scenarioid':'scenario_id','testscenarioid':'scenario_id','testcaseid':'case_id','caseid':'case_id',
 'testcase':'title','title':'title','precondition':'preconditions','preconditions':'preconditions',
 'testdata':'test_data','steps':'steps','teststeps':'steps','instructions':'steps',
 'expected':'expected','expectedresult':'expected','expectedresults':'expected',
 'status':'source_status','actualresult':'source_actual','safetycategory':'categories',
 'categories':'categories','fixtureid':'fixture_id','assertions':'assertions'}
OUTPUT_HEADERS={'status','actualresult','evidence','runid','executiontime','suggestedteststeps'}

def infer_categories(steps):
    categories=set()
    for line in str(steps).splitlines():
        line=re.sub(r'^\s*\d+[.)]\s*','',line).lower()
        if re.match(r'^(inspect|verify|check|read|observe|count|compare|wait)\b',line):continue
        for pattern,category in [(r'\b(delete|remove record|purge)\b','delete'),(r'\b(create|register)\b','create'),
                                 (r'\b(edit|update|save|fill|enter|select option|check checkbox)\b','edit'),
                                 (r'\b(upload|attach file)\b','upload'),(r'\b(send|invite|email)\b','email'),
                                 (r'\b(pay|purchase|checkout)\b','payment')]:
            if re.search(pattern,line):categories.add(category)
    return sorted(categories) or ['read']

def normalize_grid(grid,sheet='Test Cases'):
    header=None;mapping={}
    for i,row in enumerate(grid[:30]):
        names=[ALIASES.get(re.sub(r'[^a-z0-9]','',str(v or '').lower())) for v in row]
        if {'case_id','steps','expected'}.issubset(names):
            for col,name in enumerate(names):
                if name:
                    if name in mapping:raise Blocked('Duplicate source column mapping: '+name)
                    mapping[name]=col
            header=i;break
    if header is None:raise Blocked('Required columns: Test Case ID, Test Steps, Expected Result.')
    cases=[];seen=set()
    for n,row in enumerate(grid[header+1:],header+2):
        values={k:str(row[c] if c<len(row) and row[c] is not None else '') for k,c in mapping.items()}
        id=values.get('case_id','').strip()
        if not id:continue
        if id in seen or not re.fullmatch(r'[\w.-]{1,100}',id):raise Blocked('Duplicate or unsafe case ID at row '+str(n))
        seen.add(id)
        # Preserve source data locally, but never send credential strings to a model.
        categories=[x.strip().lower() for x in values.pop('categories','').split(',') if x.strip()]
        if not categories:categories=infer_categories(values.get('steps',''))
        raw_assertions=values.pop('assertions','')
        try:assertions=json.loads(raw_assertions) if raw_assertions.strip() else []
        except Exception:raise Blocked('Assertions column is not valid JSON at row '+str(n))
        if not isinstance(assertions,list):raise Blocked('Assertions must be a JSON list.')
        case=Case(**values,categories=categories,assertions=assertions,source_row=n,source_sheet=sheet).seal()
        cases.append(case)
    if not cases:raise Blocked('No populated test cases found.')
    return cases,{'mapping':mapping,'header_row':header+1,'sheet':sheet}

def load_file(path,sheet='Test Cases'):
    path=Path(path).resolve()
    if not path.is_file() or path.stat().st_size>30_000_000:raise Blocked('Source is missing or exceeds 30 MB.')
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:grid=list(csv.reader(f))
        cases,meta=normalize_grid(grid,sheet)
        meta.update(kind='csv',path=str(path))
    elif path.suffix.lower()=='.xlsx':
        import openpyxl
        book=openpyxl.load_workbook(path,read_only=True,data_only=False)
        actual=next((n for n in book.sheetnames if n.casefold()==sheet.casefold()),None)
        if not actual:raise Blocked('Select an existing tab: '+', '.join(book.sheetnames))
        ws=book[actual]
        if ws.max_row>30000 or ws.max_column>200:raise Blocked('Workbook range exceeds import limit.')
        grid=[[c.value for c in row] for row in ws.iter_rows()]
        if any(isinstance(v,str) and v.startswith('=') for row in grid for v in row):
            # Formulas are preserved in exports, but executable case inputs must
            # not be mistaken for their displayed/cached values.
            pass
        cases,meta=normalize_grid(grid,actual);book.close()
        meta.update(kind='xlsx',path=str(path))
    else:raise Blocked('Use CSV or XLSX; legacy XLS/macro workbooks are not accepted.')
    return cases,meta

def load_public(url,sheet='Test Cases'):
    import urllib.parse,urllib.request
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or parsed.hostname!='docs.google.com' or parsed.username or parsed.password:
        raise Blocked('Use a public Google Sheets link or import CSV/XLSX.')
    match=re.fullmatch(r'/spreadsheets/d/([A-Za-z0-9_-]+)(?:/edit)?/?',parsed.path)
    if not match:raise Blocked('Use the standard spreadsheet edit link.')
    export='https://docs.google.com/spreadsheets/d/'+match.group(1)+'/gviz/tq?'+urllib.parse.urlencode({'tqx':'out:csv','sheet':sheet})
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            dest=urllib.parse.urlsplit(newurl)
            if dest.scheme!='https' or not (dest.hostname=='docs.google.com' or (dest.hostname or '').endswith('.googleusercontent.com')):
                raise Blocked('Anonymous export unavailable. Import CSV/XLSX; no Google login was attempted.')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    try:
        with urllib.request.build_opener(Redirect()).open(export,timeout=30) as response:raw=response.read(30_000_001)
    except Exception as e:raise Blocked('Anonymous Sheet export failed. Import CSV/XLSX instead.') from e
    if len(raw)>30_000_000:raise Blocked('Sheet exceeds the import limit.')
    text=raw.decode('utf-8-sig')
    if '<html' in text[:500].lower() or '<!doctype' in text[:500].lower():raise Blocked('Google returned a web page, not public CSV.')
    grid=list(csv.reader(io.StringIO(text)))
    cases,meta=normalize_grid(grid,sheet)
    meta.update(kind='public_sheet',url=url)
    return cases,meta

def load_oauth(client,spreadsheet_id,sheet='Test Cases'):
    grid=client.read(spreadsheet_id,sheet+'!A1:GR30000')
    cases,meta=normalize_grid(grid,sheet)
    meta.update(kind='google',spreadsheet_id=spreadsheet_id)
    return cases,meta
