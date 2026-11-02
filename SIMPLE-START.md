# Simple local QA

Double-click **Simple Local QA** on your Desktop, or **Start Simple QA.cmd** here.

1. A browser and a small control window open. Sign in at the meeting site yourself.
2. Click **Admin Settings**. Keep the successfully opened CM tab in THAT browser.
3. Click **Run new batch** in the control window.
4. Click **Open report** for actual results and screenshots. **Pause after case**
   and **Resume** preserve completed work. **Run new batch** intentionally reruns
   the checks and preserves the earlier report separately.

The SAME browser stays alive throughout login and testing. There is no session
export/import, AI planner, injected WebSocket override, or network guard. Only
established read-only UI actions/assertions are implemented. Your website's normal
background connections behave like a normal manual browser session.

This focused starter supports five cases only: SA_RTC_008_001, 005, 006, 008 and
002. It imports the public Sheet without Google login. It compares current expected
results with the established expectations and blocks changed cases for review.
002 intentionally remains Blocked without an authoritative metric/reference dataset;
displaying a count alone cannot prove business correctness. Other cases are not
executed. Nothing is written to Google Sheets and no QA records are modified.

No ChatGPT or Ollama is needed to run these checks. Broader case review/AI enrichment
and full-suite automation are NOT claimed by this starter. Add those only after
this exact live flow has been demonstrated reliably.

Results/checkpoints are under ignored `artifacts/simple/`; the dedicated browser
profile is under ignored `.private/simple-browser/`. These contain private QA
content/session credentials: do not share or commit them. No passwords go in the
Sheet, chat, or source. Closing the control window closes this dedicated QA browser.

Use this launcher instead of the older Local QA Assistant dashboard. It is a
separate, simpler entry point and does not require restarting that dashboard.
