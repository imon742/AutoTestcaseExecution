"""Read-only diagnosis of the configured saved-session portal handoff; not a QA test pass."""
import asyncio
from pathlib import Path
from urllib.parse import urlsplit
import dashboard
import qa

async def main():
    from playwright.async_api import async_playwright
    c=dashboard.settings()
    assert c.get('bootstrap_label')=='Admin Settings'
    out=Path(__file__).resolve().parents[1]/'artifacts'/'handoff-diagnostic'
    out.mkdir(parents=True,exist_ok=True)
    blocked=[]
    result={'started':qa.now(),'outcome':'Blocked','note':'Handoff diagnosis only; no QA case outcome is claimed.'}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False)
        context=await qa.context_options(browser,c)
        await qa.guard(context,c,blocked)
        try:
            page,_=await qa.open_start_page(context,c)
            result.update(outcome='Ready',observed_path=urlsplit(page.url).path)
        except Exception as e:
            result['error']=str(e)
        finally:
            for i,page in enumerate(context.pages):
                try:await page.screenshot(path=str(out/f'page-{i+1}.png'),full_page=True)
                except Exception:pass
            result['blocked']=[{'method':b['method'],'origin':urlsplit(b['url']).netloc,
                               'path':urlsplit(b['url']).path,'reason':b['reason'],'essential':b.get('essential',True)} for b in blocked]
            result['finished']=qa.now()
            qa.save(out/'result.json',result)
            print('Handoff:',result['outcome'],flush=True)
            if result.get('error'):print(result['error'].encode('ascii','replace').decode(),flush=True)
            print('Essential blocked routes:',[(b['method'],b['origin'],b['path']) for b in result['blocked'] if b['essential']],flush=True)
            await browser.close()

if __name__=='__main__':asyncio.run(main())
