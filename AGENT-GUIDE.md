# Local QA Agent

This is the primary dashboard for the existing project. It runs on your Windows PC at loopback port 8784. Ollama performs inference locally; the QA website and Google Sheet still require their normal network access. No paid model/API service or cloud fallback is used.

## Open on this PC

Double-click **Start Local Assistant.cmd** in this folder, or the existing **Local QA Assistant** desktop shortcut. It opens the dashboard in your regular browser. Choose an installed model and save configuration. Both model names are discovered from Ollama, not hard-coded. Keep Ollama running.

The dashboard is separate from Ollama's own chat window: Ollama supplies the model; this dashboard supplies the browser tools, queue, evidence, and reports. Pasting a folder into Ollama chat does not connect these tools.

## Safe first run

1. Select your installed model. Use a 4096 context initially on a memory-constrained PC; increase model timeout if needed.
2. Click **Load isolated local acceptance fixture** and accept its specific disposable actions. This changes configuration to a temporary local website with random credentials. It never connects to your real QA application.
3. Choose **All / include Pass** for all 12 fixture cases, or leave the default non-Pass scope for 10 cases. Run matching cases.
4. Open the report and evidence. F09 intentionally contradicts its expected UI result, F10 intentionally has a missing control. F12 simulates a timeout only in the automated test double; with a real model it is an ordinary records case. Results depend on actual execution; they are not pre-filled.
5. A fixture server is temporary. After restarting the app, load a new fixture rather than resuming its expired address.

## Use your own test cases

Import a public Google Sheet anonymously by link and exact tab name, or upload CSV/XLSX. Required headers: Test Case ID, Test Steps, Expected Result. Optional: Scenario ID, Test Case, Precondition, Test Data, Status, Actual Result, Safety Category, Fixture ID, Assertions. Public reads do not request Google credentials. Duplicate IDs or ambiguous headers are rejected.

Enter the portal start URL. Allow all origins is enabled at your request; there is no address list to maintain. To restrict navigation later, uncheck it and list exact website/API origins, including ports. Save a deterministic login adapter and an explicit logged-in ready locator. Store the account using the local dashboard's Windows Credential Manager form; never put passwords into cases, JSON configuration, chat, or source. The credential name is only a vault reference.

Example login adapter (replace locator names with the actual accessible names):

```json
{"auth":{"mode":"password","credential_name":"qa-default","ready_locator":{"by":"test_id","role":"","name":"dashboard"},"login_locator":{"by":"label","role":"","name":"Password"},"steps":[{"kind":"fill","locator":{"by":"label","role":"","name":"Email"},"credential":"username"},{"kind":"fill","locator":{"by":"label","role":"","name":"Password"},"credential":"password"},{"kind":"click","locator":{"by":"role","role":"button","name":"Sign in"}}]}}
```

For portal-to-admin handoff, add a `handoff` object alongside `auth`: `locator` for the observed Admin Settings control, `destination_origin`, and `ready_locator`. The same Playwright context follows the link/popup. Do not configure a copied JWT login URL as the start URL. Test login stores new auth state only under `.private/agent/auth/`. MFA/CAPTCHA blocks with AuthRequired; it is not bypassed.

## What a result proves

The model suggests permitted structured actions; Playwright executes them. It never executes model-generated Python/JavaScript/shell. Each run proceeds one case at a time, commits to SQLite after every case, and advances after failures/blocks. There is no five- or ten-case cap. Default scope excludes source Pass rows; other scopes and checked IDs are available.

An automatic Pass requires coverage of the source steps and all authoritative expected-result criteria. Explicit JSON action lists or a reviewed source-hash contract supply step coverage. Expected criteria can use the Assertions column or JSON `{"criteria":[...]}`. Simple exact text/URL expectations also compile deterministically. Ordinary business prose can be explored and receive suggested steps/criteria, but its unconfirmed mapping is **NeedsReview**. This prevents a model from silently replacing your expected behavior with an easier check. A source mismatch is not automatically proof that a test is invalid.

Contracts in Advanced configuration are keyed by the displayed `source_hash` and contain `actions` and `criteria`. A changed source invalidates the contract. Use the isolated fixture's action lists as concrete examples. Review a mapping once; normal execution does not pause for a per-case plan approval.

Supported actions: navigate, click, fill, select, check/uncheck, key press, scroll, upload a named fixture, wait, extract, switch tab, close dialog, and verify. Locators prefer exact accessible role/name, label, placeholder, or test ID. Ambiguous/missing controls block rather than guess.

Create/edit/delete/upload/email/payment need explicit categories, exact case IDs, and disposable fixture IDs. Uploads stay within the approved fixture directory. Sensitive field entry belongs in deterministic adapters. Real email delivery, OTP, authoritative backend data, and payment sandbox adapters are **not implemented**; requirements needing them remain Blocked/NeedsReview. Do not approve real payment credentials or production data.

## Results, resume, and replay

SQLite queue/config: `.private/agent/agent.sqlite3`. Reports/screenshots/traces: `artifacts/agent/<run-id>/`. Auth/OAuth state and imports remain local and ignored; treat evidence as private because your application may display personal data.

Pause finishes the active case; Stop records the interrupted case and stops. After restarting, select a saved real-site run and Resume saved queue. Completed cases are not rerun. A crash during a mutating case can leave the external action applied without a local result: the case is marked NeedsReview and is not automatically repeated. Reconcile that fixture before an explicit new run; arbitrary remote actions cannot be made transactionally exactly-once by this app.

Exports produce reports plus a result-copy of CSV/XLSX, preserving the original. Other XLSX tabs/formulas/styles are retained where openpyxl supports them. The app does not support macro/legacy XLS files.

Google writeback needs your own local Google OAuth desktop client and authorization, plus the reviewed first-batch approval checkbox. Only existing mapped Status and Actual Result cells are written using RAW values. Row ID/source hash are rechecked immediately before writing and both cells read back. Concurrent edits between the check and write remain a Google API race; avoid editing those rows during sync. Failed sync retries do not rerun the browser.

After reviewing successful source-covered flows, export Playwright tests. The generated pytest file reuses deterministic browser tools and saved local run configuration, without model inference. Inspect it before running: approved writes can be repeated. From this folder:

```powershell
.venv\Scripts\python.exe -m pytest artifacts\agent\YOUR_RUN_ID\test_verified_flows.py -v
```

## Install the clean source on another Windows PC

These commands create a project-local Python environment, install the pinned dependencies, and download Playwright Chromium. Use an installed compatible Python (this build was checked with the existing Python environment); no system Python/Node replacement is required.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-agent.txt
.venv\Scripts\python.exe -m playwright install chromium
& '.\Start Local Assistant.cmd'
```

This PC uses Python 3.13.6. If Python 3.13 is unavailable, select an installed supported Python version first. Ollama and a local model are separate prerequisites; this installer does not install/download a model. Node.js is not needed for this Python runner.

The source-only ZIP excludes credentials, browser sessions, OAuth clients/tokens, case data, reports, old source, and `.venv`. Keep your private runtime folder out of shared archives/cloud sync.

Manual sign-in: use Open browser to sign in, navigate to the target page yourself, then Save signed-in session. Authentication state stays in the ignored local folder. Read-only exploration may proceed with unresolved preconditions, but results remain NeedsReview until source coverage is established.
