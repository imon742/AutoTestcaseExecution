import csv,html,json,shutil,urllib.parse
from pathlib import Path
from .models import Blocked,Case,redact
from .importer import load_file,normalize_grid,OUTPUT_HEADERS

def safe_cell(value):
    value=str(value)
    return "'"+value if value.startswith(('=','+','-','@')) else value

def export_results(store,run_id,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=[]
    for r in store.results(run_id):
        details=json.loads(r.get('details') or '{}')
        records.append({'Case ID':r['case_id'],'Status':r.get('status') or 'Not Run',
            'Actual Result':r.get('actual') or 'Not executed.','Run ID':run_id,
            'Execution Time':round(r['finished']-r['started'],2) if r.get('finished') else '',
            'Evidence':str(out/r['attempt_id']) if r.get('attempt_id') else '',
            'Suggested Test Steps':details.get('suggested_steps',''),
            'Case Review':details.get('case_review','')})
    with (out/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]) if records else ['Case ID','Status','Actual Result'])
        writer.writeheader();writer.writerows({k:safe_cell(v) for k,v in r.items()} for r in records)
    cells=lambda r:''.join('<td>'+html.escape(str(v))+'</td>' for v in r.values())
    headers=''.join('<th>'+html.escape(k)+'</th>' for k in records[0]) if records else ''
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>QA results</title><style>body{font:14px system-ui;margin:28px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:10px;vertical-align:top}th{background:#edf5f2}</style><h1>Factual local QA results</h1><p>Pass requires source step coverage and all authoritative assertions. AI proposals alone are not proof.</p><table><tr>'+headers+'</tr>'+''.join('<tr>'+cells(r)+'</tr>' for r in records)+'</table>',encoding='utf-8')
    return records

def result_copy(store,run_id,out):
    run=store.run(run_id);source=run['source'];records=export_results(store,run_id,out)
    if source.get('kind') not in ('csv','xlsx'):return Path(out)/'results.csv'
    current,meta=load_file(source['path'],source.get('sheet','Test Cases'))
    live={c.case_id:c for c in current};original={r['case_id']:Case.from_dict(json.loads(r['data'])) for r in store.results(run_id)}
    for id,c in original.items():
        if id not in live or live[id].source_hash!=c.source_hash:raise Blocked('Source changed before result-copy: '+id)
    mapping=meta['mapping'];source_path=Path(source['path'])
    target=Path(out)/(source_path.stem+'-results'+source_path.suffix)
    updates={r['Case ID']:r for r in records}
    if source_path.suffix.lower()=='.xlsx':
        import openpyxl
        book=openpyxl.load_workbook(source_path);ws=book[meta['sheet']]
        status=mapping.get('source_status');actual=mapping.get('source_actual')
        if status is None:status=ws.max_column;ws.cell(meta['header_row'],status+1,'Status')
        if actual is None:actual=ws.max_column;ws.cell(meta['header_row'],actual+1,'Actual Result')
        for id,r in updates.items():
            row=live[id].source_row;ws.cell(row,status+1,safe_cell(r['Status']));ws.cell(row,actual+1,safe_cell(r['Actual Result']))
        book.save(target);book.close()
    else:
        with source_path.open(encoding='utf-8-sig',newline='') as f:grid=list(csv.reader(f))
        heads=grid[meta['header_row']-1]
        for key,title in [('source_status','Status'),('source_actual','Actual Result')]:
            if key not in mapping:mapping[key]=len(heads);heads.append(title)
        for id,r in updates.items():
            row=grid[live[id].source_row-1];row.extend(['']*max(0,len(heads)-len(row)))
            row[mapping['source_status']]=safe_cell(r['Status']);row[mapping['source_actual']]=safe_cell(r['Actual Result'])
        with target.open('w',encoding='utf-8-sig',newline='') as f:csv.writer(f).writerows(grid)
    return target

class SheetsOAuth:
    def __init__(self,client_file,token_file):self.client_file=Path(client_file);self.token_file=Path(token_file)
    def connect(self,interactive=False):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        scopes=['https://www.googleapis.com/auth/spreadsheets']
        creds=Credentials.from_authorized_user_file(str(self.token_file),scopes) if self.token_file.exists() else None
        if creds and creds.expired and creds.refresh_token:creds.refresh(Request())
        if not creds or not creds.valid:
            if not interactive:raise Blocked('Google OAuth connection requires local user setup; no write attempted.')
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow=InstalledAppFlow.from_client_secrets_file(str(self.client_file),scopes)
            creds=flow.run_local_server(port=0,open_browser=True)
        self.token_file.parent.mkdir(parents=True,exist_ok=True)
        self.token_file.write_text(creds.to_json(),encoding='utf-8')
        from google.auth.transport.requests import AuthorizedSession
        self.session=AuthorizedSession(creds)
        return self
    def read(self,id,range):
        url='https://sheets.googleapis.com/v4/spreadsheets/'+urllib.parse.quote(id,safe='')+'/values/'+urllib.parse.quote(range,safe='')
        r=self.session.get(url,timeout=30);r.raise_for_status();return r.json().get('values',[])
    def write_checked(self,id,source,case,result):
        sheet=source['sheet'];quoted="'"+sheet.replace("'","''")+"'"
        grid=self.read(id,quoted+'!A1:GR30000');cases,meta=normalize_grid(grid,sheet)
        matches=[c for c in cases if c.case_id==case.case_id]
        if len(matches)!=1 or matches[0].source_hash!=case.source_hash:raise Blocked('Sheet row/source changed; writeback needs review.')
        current=matches[0];mapping=meta['mapping']
        if 'source_status' not in mapping or 'source_actual' not in mapping:raise Blocked('Map existing Status and Actual Result columns before writeback.')
        def column(i):
            out='';i+=1
            while i:i,n=divmod(i-1,26);out=chr(65+n)+out
            return out
        data=[{'range':quoted+'!'+column(mapping[k])+str(current.source_row),'values':[[result[v]]]} for k,v in [('source_status','status'),('source_actual','actual')]]
        # RAW prevents formula execution and restricts writes to these two cells.
        r=self.session.post('https://sheets.googleapis.com/v4/spreadsheets/'+id+'/values:batchUpdate',
             json={'valueInputOption':'RAW','data':data},timeout=30);r.raise_for_status()
        for item in data:
            if self.read(id,item['range'])!=item['values']:
                raise Blocked('Writeback readback did not match; local result retained.')

def flush_writebacks(store,run_id):
    run=store.run(run_id);source=run['source'];cfg=run['config']
    if not cfg['policy'].get('allow_writeback'):raise Blocked('Sheet writeback was not approved.')
    if source.get('kind')!='google':
        for job in store.pending_writebacks(run_id):store.writeback_state(job['id'],'NeedsReview','Source writeback requires a connected OAuth Google Sheet; local export is separate.')
        return
    oauth=cfg.get('google',{})
    try:client=SheetsOAuth(oauth['client_file'],oauth['token_file']).connect()
    except Exception as e:
        for job in store.pending_writebacks(run_id):store.writeback_state(job['id'],'Pending',str(e))
        return
    cases={r['case_id']:Case.from_dict(json.loads(r['data'])) for r in store.results(run_id)}
    for job in store.pending_writebacks(run_id):
        try:
            client.write_checked(source['spreadsheet_id'],source,cases[job['case_id']],json.loads(job['payload']))
            store.writeback_state(job['id'],'Done')
        except Exception as e:store.writeback_state(job['id'],'Pending',str(e))
