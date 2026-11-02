"""Native double-click launcher; show an actionable error without opening a terminal."""
import ctypes
import traceback
from pathlib import Path
try:
    import dashboard
    dashboard.main()
except Exception as e:
    root=Path(__file__).resolve().parent
    (root/'.private').mkdir(exist_ok=True)
    (root/'.private'/'launch-error.log').write_text(traceback.format_exc(),encoding='utf-8')
    ctypes.windll.user32.MessageBoxW(None,'The local assistant could not start: '+str(e)+'\n\nDetails: '+str(root/'.private'/'launch-error.log'),'Local QA Assistant',0x10)
