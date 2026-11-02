"""Five established read-only checks in ONE manually authenticated browser session."""
import asyncio
import csv
import json
import queue
import re
import threading
import time
import traceback
import webbrowser
from datetime import datetime,timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from urllib.parse import urlsplit
import case_import
import qa

ROOT=Path(__file__).resolve().parent
PORTAL='https://meet2.synesisit.info/'
CM='https://meet2.synesisit.info:85'
SHEET='https://docs.google.com/spreadsheets/d/1pDgSUjcMEjJJLicpeCrwmyFVwwDT9kLhSZN6e1yfRx4/edit'
CASES={
'SA_RTC_008_001':'Organization page loads with visible title, subtitle, summary, search, Filters, Create and organization rows.',
'SA_RTC_008_005':'Total Organizations, Total Users and Actively Using reload without missing cards, duplicate cards or indefinite skeletons.',
'SA_RTC_008_006':'Header columns are Company, Created On, Status, Users, About and Actions.',
'SA_RTC_008_008':'Populated first page shows at most 20 organization rows, with valid pagination controls.',
'SA_RTC_008_002':'Total Organizations card displays a numeric, organization-scoped number of organizations; comparative percentage is valid when shown; no hard-coded total is expected.'}
LABELS=['Total Organizations','Total Users','Actively Using']
HEADERS=['Company','Created On','Status','Users','About','Actions']

def normalize(text):return ' '.join(text.split()).casefold()

async def ready(page):
    from playwright.async_api import expect
    await expect(page.get_by_role('heading',name='Organization',exact=True)).to_be_visible(timeout=25000)
    await page.get_by_text('Loading...',exact=True).wait_for(state='hidden',timeout=25000)
    await expect(page.get_by_role('table').get_by_role('row').nth(1)).to_be_visible(timeout=25000)

async def cards(page):
    from playwright.async_api import expect
    result={}
    for label in LABELS:
        text=page.get_by_text(label,exact=True)
        await expect(text).to_have_count(1)
        await expect(text).to_be_visible()
        parent=text
        for _ in range(4):
            parent=parent.locator('..')
            headings=parent.get_by_role('heading')
            if await headings.count()==1:
                value=(await headings.inner_text()).strip()
                assert re.fullmatch(r'\d[\d,]*',value),f'{label} is not a nonnegative integer: {value}'
                result[label]=value
                break
        else:raise ValueError('Cannot uniquely identify count for '+label+'; markup needs inspection.')
    return result

async def perform_case(page,case_id):
    from playwright.async_api import expect
    await ready(page)
    if case_id.endswith('_001'):
        await expect(page.get_by_text('Manage Organizations',exact=True)).to_be_visible()
        await expect(page.get_by_role('searchbox')).to_be_visible()
        await expect(page.get_by_role('button',name='Filters',exact=True)).to_be_visible()
        await expect(page.get_by_role('link',name='Create',exact=True)).to_be_visible()
        values=await cards(page)
        n=await page.get_by_role('table').get_by_role('row').count()-1
        assert n>0,'No organization rows loaded.'
        return 'Pass',f'Organization heading, subtitle, three summary cards, search, Filters and Create link visible; {n} rows loaded. Counts: {values}.'
    if case_id.endswith('_005'):
        before=await cards(page)
        await page.reload(wait_until='domcontentloaded')
        await ready(page)
        after=await cards(page)
        return 'Pass',f'Reloaded successfully; each summary label appears once with a numeric value and no indefinite loading. Before: {before}. After: {after}. Live values are recorded, not hard-coded.'
    if case_id.endswith('_006'):
        actual=[x.strip() for x in await page.get_by_role('table').get_by_role('columnheader').all_text_contents()]
        assert actual==HEADERS,f'Expected {HEADERS}; observed {actual}.'
        return 'Pass','Observed headers in exact order: '+', '.join(actual)+'.'
    if case_id.endswith('_008'):
        n=await page.get_by_role('table').get_by_role('row').count()-1
        assert 1<=n<=20,f'Expected 1–20 populated rows; observed {n}.'
        match=re.search(r'Page\s+(\d+)\s+of\s+(\d+)',await page.locator('body').inner_text())
        assert match,'Pager label missing.'
        current,total=map(int,match.groups())
        assert current==1 and total>=1,f'Unexpected first-page state: {current}/{total}.'
        assert not await page.get_by_role('button',name='Previous',exact=True).is_enabled(),'Previous should be disabled on page 1.'
        assert await page.get_by_role('button',name='Next',exact=True).is_enabled()==(total>1),'Next enabled state does not match total pages.'
        return 'Pass',f'{n} data rows; page {current} of {total}; Previous disabled and Next state correct. Page transitions were not tested.'
    if case_id.endswith('_002'):
        values=await cards(page)
        return 'Blocked',f'UI count observed: {values["Total Organizations"]}. Authoritative data and prior-period baseline are unavailable, so metric scope/correctness and percentage validity were not verified. Split display and reconciliation cases.'
    raise ValueError('This starter has no established check for '+case_id)

def write_report(folder,results):
    folder.mkdir(parents=True,exist_ok=True)
    qa.save(folder/'checkpoint.json',results)
    with (folder/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['Case ID','Status','Actual Result','Evidence'])
        writer.writeheader();writer.writerows(results)
    import html
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ['Case ID','Status','Actual Result','Evidence'])+'</tr>' for r in results)
    (folder/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Local QA results</title><style>body{font:15px system-ui;margin:30px}td,th{border:1px solid #ccc;padding:12px;text-align:left}table{border-collapse:collapse}</style><h1>Actual local results</h1><p>Five established read-only cases. No Google Sheet writes. Full metric reconciliation is not claimed.</p><table><tr><th>Case ID</th><th>Status</th><th>Actual Result</th><th>Evidence</th></tr>'+rows+'</table>',encoding='utf-8')

class LocalApp:
    def __init__(self):
        self.root=tk.Tk();self.root.title('Simple Local QA — same browser session');self.root.geometry('820x580')
        self.commands=queue.Queue();self.events=queue.Queue();self.pause=threading.Event();self.busy=False;self.folder=None
        ttk.Label(self.root,text='One browser. You sign in. Five read-only checks.',font=('Segoe UI',16,'bold')).pack(pady=14)
        ttk.Label(self.root,text='1. Sign in in the browser that opens.  2. Click Admin Settings and keep CM open.\n3. Click Run new batch here. No Ollama, ChatGPT or paid API is needed.',justify='left').pack(pady=8)
        bar=ttk.Frame(self.root);bar.pack(pady=10)
        self.run_button=ttk.Button(bar,text='Run new batch',command=lambda:self.start('new'));self.run_button.pack(side='left',padx=5)
        self.resume_button=ttk.Button(bar,text='Resume',command=lambda:self.start('resume'));self.resume_button.pack(side='left',padx=5)
        ttk.Button(bar,text='Pause after case',command=self.pause.set).pack(side='left',padx=5)
        ttk.Button(bar,text='Open report',command=self.open_report).pack(side='left',padx=5)
        self.log=tk.Text(self.root,wrap='word',state='disabled');self.log.pack(fill='both',expand=True,padx=18,pady=10)
        ttk.Label(self.root,text='Scope: 008_001, 005, 006, 008, 002 only. Existing Sheet results are not reused. Closing this window closes its QA browser.').pack(pady=8)
        self.thread=threading.Thread(target=lambda:asyncio.run(self.worker()),daemon=True);self.thread.start()
        self.root.protocol('WM_DELETE_WINDOW',self.close);self.root.after(150,self.poll)
    def start(self,kind):
        if self.busy:return
        self.busy=True;self.pause.clear();self.run_button.config(state='disabled');self.resume_button.config(state='disabled');self.commands.put(kind)
    def poll(self):
        while not self.events.empty():
            text=self.events.get()
            if text=='__IDLE__':
                self.busy=False;self.run_button.config(state='normal');self.resume_button.config(state='normal');continue
            self.log.config(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.config(state='disabled')
        self.root.after(150,self.poll)
    def open_report(self):
        if self.folder and (self.folder/'report.html').exists():webbrowser.open((self.folder/'report.html').as_uri())
        else:messagebox.showinfo('Report','Run a batch first. The report is saved after each case.')
    def close(self):
        self.pause.set();self.commands.put('stop')
        self.run_button.config(state='disabled');self.resume_button.config(state='disabled')
        self.wait_close()
    def wait_close(self):
        if self.thread.is_alive():self.root.after(200,self.wait_close)
        else:self.root.destroy()
    async def worker(self):
        from playwright.async_api import async_playwright
        try:
            async with async_playwright() as p:
                context=await p.chromium.launch_persistent_context(str(ROOT/'.private'/'simple-browser'),headless=False,accept_downloads=False)
                page=await context.new_page();await page.goto(PORTAL,wait_until='domcontentloaded')
                self.events.put('Browser ready. Sign in yourself, then click Admin Settings. Keep that CM tab open.')
                while True:
                    if self.commands.empty():await asyncio.sleep(.2);continue
                    cmd=self.commands.get()
                    if cmd=='stop':break
                    try:await self.run_batch(context,cmd)
                    except Exception as e:self.events.put('Blocked: '+str(e))
                    finally:self.events.put('__IDLE__')
                await context.close()
        except Exception as e:self.events.put('Browser error: '+str(e));self.events.put('__IDLE__')
    async def run_batch(self,context,kind):
        tabs=[x for x in context.pages if urlsplit(x.url).netloc==urlsplit(CM).netloc and urlsplit(x.url).path!='/login']
        if len(tabs)!=1:raise ValueError('Keep exactly one successfully opened CM tab after clicking Admin Settings. Do not enter port 85 directly.')
        page=tabs[0]
        self.events.put('Reading the public Test Cases tab anonymously…')
        records=await asyncio.to_thread(case_import.public_sheet,SHEET,'Test Cases',81082)
        selected={r.get('Test Case ID',''):r for r in records if r.get('Test Case ID') in CASES}
        key=qa.digest(selected)[:16];pointer=ROOT/'.private'/'simple-last-run.json'
        previous=json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else {}
        base=(ROOT/'artifacts'/'simple').resolve()
        candidate=(ROOT/previous.get('folder','')).resolve()
        valid=candidate.is_relative_to(base) and previous.get('source_hash')==key and candidate.is_dir()
        self.folder=candidate if kind=='resume' and valid else base/(key+'-'+str(time.time_ns()))
        self.folder.mkdir(parents=True,exist_ok=True)
        qa.save(pointer,{'source_hash':key,'folder':str(self.folder.relative_to(ROOT))})
        qa.save(self.folder/'source-cases.json',selected)
        cp=self.folder/'checkpoint.json';results=json.loads(cp.read_text(encoding='utf-8')) if cp.exists() else []
        done={x['Case ID'] for x in results}
        for case_id,contract in CASES.items():
            if self.pause.is_set():self.events.put('Paused. Resume continues from the last finished case.');break
            if case_id in done:continue
            self.events.put('Running '+case_id+' in your existing CM tab…')
            status='Blocked';actual='';f=self.folder/case_id;f.mkdir(exist_ok=True)
            try:
                source=selected.get(case_id)
                if not source:raise ValueError('Case missing from the current Sheet.')
                if normalize(source.get('Expected Result',''))!=normalize(contract):
                    raise ValueError('Expected Result changed. The established assertion needs review; not passed automatically.')
                if not urlsplit(page.url).path.startswith('/organization'):
                    link=page.locator('a[href="/organization"],a[href="'+CM+'/organization"]')
                    if await link.count()!=1:raise ValueError('Cannot uniquely locate the observed Organization navigation link.')
                    await link.click(timeout=15000)
                status,actual=await perform_case(page,case_id)
            except AssertionError as e:status='Fail';actual=str(e)
            except Exception as e:status='Blocked';actual=str(e)
            try:await page.screenshot(path=str(f/'observed.png'),full_page=True)
            except Exception:pass
            result={'Case ID':case_id,'Status':status,'Actual Result':actual,'Evidence':str(f)}
            qa.save(f/'result.json',{**result,'recorded_at':datetime.now(timezone.utc).isoformat()})
            results.append(result);write_report(self.folder,results)
            self.events.put(case_id+': '+status+' — '+actual)
        self.events.put('Saved report: '+str(self.folder/'report.html')+'\nThis batch does not update your Sheet or certify the full suite.')

if __name__=='__main__':
    try:LocalApp().root.mainloop()
    except Exception:
        (ROOT/'.private').mkdir(exist_ok=True)
        (ROOT/'.private'/'simple-error.log').write_text(traceback.format_exc(),encoding='utf-8')
        messagebox.showerror('Local QA','Could not start. See .private/simple-error.log in the project folder.')
