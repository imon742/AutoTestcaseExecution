# Conversation and work record: Local Ollama browser testing assistant

**Date:** 28 October 2026  
**Timezone:** Asia/Dhaka  
**Original workspace:** `C:\Users\Synesis IT\OneDrive\Documents\ChatGPT\Ollama setup`  
**Application folder:** `C:\Users\Synesis IT\browser-testing-poc`

This document records the conversation, decisions, work performed, verification,
corrections, and outstanding work. User requests and assistant replies are
condensed where appropriate; this is a comprehensive conversation record, not a
verbatim export of every message, tool call, log, or screenshot.

## 1. Original request

The user requested help setting up a local browser testing workflow on Windows.
Ollama had been installed but not configured for this purpose.

The intended workflow was:

1. Read test cases from a Google Sheet.
2. Use browser-use with a local Ollama model to explore the cases.
3. Capture observed steps, screenshots, outcomes, and evidence.
4. Convert reviewed successful flows into repeatable Playwright tests.
5. Run small batches, checkpoint after each case, and resume after interruptions.
6. Report case ID, Pass/Fail/Blocked/Not Run, actual observed behavior, and evidence.
7. After first-batch review and approval, update only the Sheet's Status and Actual
   Result columns.

The user specified these boundaries:

- Inspect Windows, Python, Node.js, memory, and disk before selecting versions/model.
- Explain commands and initially obtain confirmation before making changes.
- Do not assume Ollama is installed.
- Use local models only and no paid model APIs.
- Never request passwords, Google credentials, temporary-mail passwords, API keys,
  or payment details in chat or source files. Use local ignored configuration or
  environment variables when secrets are necessary.
- Access the Sheet only after receiving its link and establishing safe access.
  Prefer a small private CSV export if integration would expose credentials.
- Start with 5–10 read-only cases in a disposable QA environment.
- Let the user sign in personally.
- Do not save/submit changes, invite users, upload files, delete records, or make
  purchases during the initial trial.
- Flag ambiguous instructions rather than guessing.
- Prefer accessible Playwright locators.
- Never claim Pass without actual execution and the expected result being met.
- Obtain specific fixture/action approval before any later side-effect test.

## 2. Conversation chronology

### 2.1 Initial inspection approvals

**Assistant:** Proposed read-only PowerShell commands to inspect Windows, CPU,
RAM, GPUs, disk space, installed runtimes, Git, and Ollama.

**User:** “ok”

**Action:** Ran the authorized read-only inspection.

**Assistant:** Reported the hardware/runtime results, tentatively selected Python
3.12 and a small Qwen model, and requested permission to verify Python 3.12,
downloaded models, and NVIDIA memory.

**User:** “ok”

**Action:** Found Python 3.12's registration was stale, confirmed existing Ollama
models, and measured 2 GB NVIDIA VRAM.

**Assistant:** Proposed checking Python 3.13 and the default Python installation.

**User:** “ok”

**Action:** Confirmed standard Python 3.13.6 and Python 3.14.4 both work. Selected
Python 3.13 for the project instead of installing another Python.

### 2.2 Setup authorization changed

**Assistant:** Showed commands to create the project outside OneDrive, create a
virtual environment, install browser-use and pytest-playwright, download Chromium,
download `qwen3:4b-instruct`, and record package versions.

**User:** “ok . and no need to asked me from now do it and show me the final runable”

**Decision:** Continued routine setup without further confirmations. Specific
approval for later QA actions that change data remained required.

### 2.3 Initial command-line proof of concept

**Action:** Built a conservative navigation/observation-only prototype with:

- CSV input.
- An isolated local Python environment.
- Local Ollama inference.
- Browser-use custom tools backed by Playwright.
- Approved-path and network restrictions.
- Screenshots, traces, reports, checkpoints, and resume behavior.
- Human review gates before generating successful flows as Playwright tests.
- A five-case disposable local demonstration website.

**Finding:** The small model initially repeated navigation rather than finishing.
The navigation tool was changed to finish after a real Playwright assertion.
The earlier attempt was retained as evidence rather than reported as successful.

**User:** “What are you doing now ? running all the cases from google sheet?”

**Assistant:** Clarified that no Sheet or QA site had been accessed. Only five
synthetic cases on a local disposable website were being used to verify setup.

### 2.4 Ollama desktop integrations error

**User:** Reported: “Couldn't load integrations.”

**Action:** Checked the local Ollama API, processes, port ownership, and relevant
application/server log errors.

**Findings:**

- The local API at `127.0.0.1:11434` responded with version 0.33.2.
- Local model execution continued working.
- Two Ollama desktop processes were present.
- Desktop logs showed repeated server startup failures.
- Server logs reported that port 11434 was already in use.
- This established a port conflict, but did not prove the exact cause of the
  integrations screen error.

**Action attempted:** A clean Ollama restart.

**Outcome:** Automatic approval review rejected that stop/restart action as
“blocked by policy.” It did not execute. No bypass was attempted and no models or
settings were removed. The user was advised to quit Ollama from the tray and
reopen it once when no tests were running. Resolution of the UI error was not
confirmed.

### 2.5 First runnable delivery

**Assistant:** Delivered `Start Demo.cmd`, README instructions, and the demo report.

**Verified at that stage:**

- Five synthetic demo cases ran and passed actual visible-heading assertions.
- Six initial workflow/integration checks passed.
- A deliberately wrong expectation correctly produced Fail.
- Completed cases were skipped when resuming.
- No demo flows were converted without human review; demo replay remained Not Run.

### 2.6 The intended interface became clear

**User:** Shared the Ollama integrations screen and asked what to select.

**Assistant:** Explained that none of those integrations was required for the
existing project; it connected directly to the local Ollama API.

**User:** Shared the command-window output and asked whether there would be no UI.

**Assistant:** Explained that the first version had an HTML report but no
interactive dashboard, and described a possible local dashboard.

**User:** Explained the expectation: open Ollama's app, continue the conversation
there, provide the Sheet link/instructions, and have it test the website.

**Assistant:** Acknowledged that the command-line prototype did not meet that
expectation and explained that a model needs a connected application to execute
browser and file tools.

**User:** “I want ‘a conversation inside Ollama’s own window.’”

**Action:** Checked Ollama's official documentation and the open desktop MCP/tool
support feature request.

**Assistant:** Explained that the official Ollama chat window did not provide a
supported connection for this browser-use workflow. Its integrations launch other
applications; selecting a model or entering a folder path does not grant browser
control or local file execution.

**User:** “what that means ?”

**Assistant:** Explained that asking Ollama to test a Sheet would produce advice
or code unless the conversation had a tool-execution connection. The prototype
ran separately from Ollama's chat window.

### 2.7 Independent local interaction

**User:** Asked how to interact with the build without returning to ChatGPT to run
the local model.

**Assistant:** Explained that the existing program already ran independently,
but used CSV files, commands, and reports. Proposed a local chat dashboard for
everyday interaction without ChatGPT.

**User:** Asked which model was downloaded.

**Assistant:** Confirmed `qwen3:4b-instruct`, approximately 2.5 GB, with CPU
inference. Existing Gemma models were retained.

**User:** Selected that model in Ollama and asked how to connect the project folder.

**Assistant:** Explained that Ollama's chat could not directly attach the project
as an executable tool environment. The project calls Ollama, rather than Ollama's
chat automatically controlling the project.

### 2.8 Sheet and target website supplied

**User provided this Google Sheet:**

<https://docs.google.com/spreadsheets/d/1pDgSUjcMEjJJLicpeCrwmyFVwwDT9kLhSZN6e1yfRx4/edit>

**User provided this QA URL:**

<https://meet2.synesisit.info/>

**Assistant initially:** Explained private CSV export, configuration, manual
sign-in, and command-line batch execution. No Sheet access or QA execution was
performed at that point.

### 2.9 Expectation reset

**User clarified the original ChatGPT workflow:**

> Give a Google Sheet link containing the test cases, open a browser where the
> user logs in, execute cases, record Status and Actual Result, verify/rewrite steps
> if needed, and avoid exhausting token limits while attempting the whole suite.
> The question was whether that experience could be free or local and resumable.

**Assistant:** Acknowledged the mismatch and apologized for building a narrower
command-line prototype before clarifying the interface. Explained:

- Local inference can avoid paid model API fees and cloud token quotas.
- Ollama supplies the model, not the entire testing assistant.
- Small batches and per-case checkpoints avoid keeping the entire suite/history
  in one conversation.
- A small local model's reliability on the real suite remained unproven.
- The design target was a conversational assistant managing the work, not the
  user manually operating CSV transformations and test scripts.

**User:** “Yes”

**Assistant:** Proposed a separate local conversational application, retaining the
useful prototype components. The first milestone would be a complete small
read-only QA batch after manual login and review.

**User:** “do it give me a final result with less token use as possible”

**Decision:** Build the local chat dashboard and keep user-facing updates concise.

### 2.10 Inspect the actual Test Cases tab

**User:** Stated they would provide a Sheet link containing steps and asked to
check the tab called “test cases.”

**Action:** Used the connected Google Drive tools read-only, following the Google
Drive/Sheets skills. No credentials were requested in chat.

**Verified spreadsheet metadata:**

- Spreadsheet title: **Dummy of SA_Organization Management**.
- Target tab: **Test Cases**.
- Target tab `sheetId` / `gid`: **81082**.
- The supplied `gid=0` link points to Sheet1, not the Test Cases tab; metadata
  identified the correct tab.
- Read range: **`'Test Cases'!A1:S12`** — headers and the first 11 cases only.
- The configured 800-row grid is capacity, not a verified count of populated cases.

**Columns observed:**

Scenario ID; Test Scenario; Test Case ID; Execution Type; Test Case; Precondition;
Test Data; Test Steps; Expected Result; Actual Result; Status; V2 Automation Remarks;
V2 Automation Coverage Status; Remarks (Automation); Exec. Time (Min.); Priority;
Defect Source; Bug Reference; Remarks.

**Cases observed in that preview:**

| Case ID suffix | Subject |
| --- | --- |
| `008_001` | Open Organizations through navigation and inspect the directory |
| `008_002` | Total Organizations summary count |
| `008_003` | Total Users summary count |
| `008_004` | Actively Using summary count |
| `008_005` | Summary cards after reload |
| `008_006` | Organization table headers |
| `008_007` | Active/Inactive status badges |
| `008_008` | First-page row count and pagination |
| `008_009` | About values against stored organization details |
| `008_010` | Users values against organization membership data |
| `008_011` | Company links and correct organization details |

The full IDs begin with `SA_RTC_`. Several rows already contained historical Pass
or Not Run statuses. These were not treated as new executions. Checks requiring
authoritative backend or membership reconciliation cannot be passed merely from
visible numbers or controls.

### 2.11 Local dashboard delivered

**Action:** Built and opened **Local QA Assistant**, a separate browser-based
application running on the user's PC.

**Included:**

- Local conversation with `qwen3:4b-instruct`.
- Natural-language intent routing and explicit controls for prepare/run/resume/
  pause/login/report.
- Prefilled Sheet link, Test Cases gid, and target website.
- Read-only authenticated Sheet CSV export using a browser where the user signs
  in personally; private CSV import as fallback.
- A saved first-11-case Sheet preview clearly labeled as incomplete.
- Separate manual QA login and locally stored session state.
- Explicit approval of the read-only starting path.
- Selection of small case batches.
- Local-model proposed plans grounded in a current accessibility snapshot.
- Coverage/unverifiable criteria and suggested rewrites for review.
- Human approval before executing read-only plans.
- Browser-use execution of the reviewed plan with Playwright assertions.
- Screenshots, traces, observed checks, results, and per-case checkpoints.
- Human review of successful actual flows before Playwright test generation.
- Generated pytest execution, replay evidence, and JUnit results.
- Archiving of prior evidence for deliberate retries.
- A desktop shortcut, single-instance reopen behavior, and a dashboard stop control.

**User-facing final delivery:** The dashboard was opened, the desktop shortcut
was created, an 11-case preview was loaded, and instructions were provided for
Google import, manual QA sign-in, plan review, and running a first batch.

### 2.12 This documentation request

**User:** “create a markdown file for the total chat what we are done here total chat”

**Action:** Created this document to preserve the whole conversation's substance,
work history, verification, limitations, and next steps.

## 3. PC inspection results

| Item | Observed result |
| --- | --- |
| OS | Windows 11 Pro, 64-bit, build 10.0.26300 |
| CPU | Intel Core i7-1165G7, 4 cores / 8 logical processors |
| RAM | 31.8 GB total; 11.6 GB available at the initial check |
| C: free space | 55.2 GB before setup |
| D: free space | 11.9 GB before setup |
| NVIDIA GPU | GeForce MX330, 2048 MiB VRAM |
| NVIDIA driver | 516.40 as reported by nvidia-smi |
| Other graphics | Intel Iris Xe |
| Python selected | Standard Python 3.13.6 |
| Other working Python | 3.14.4 |
| Python 3.12 | Registered executable missing; not used |
| Node.js | 24.14.1, unchanged |
| npm | 11.11.0, unchanged |
| Git | 2.45.1, unchanged |
| Ollama | 0.33.2, already installed |

A separate free-threaded Python 3.13 registration was also listed; the project
uses the standard Python 3.13 installation.

## 4. Installed model and environment

- New model: **`qwen3:4b-instruct`**.
- Download size: approximately **2.5 GB**.
- Observed Ollama digest: `0edcdef34593`.
- CPU inference selected because the NVIDIA GPU has only 2 GB VRAM.
- An early run with 8192-token context showed roughly 3.9 GB loaded model memory.
- The newer local assistant generally uses a 4096-token context with bounded
  output, short per-case prompts, and cached plans.
- Existing `gemma4:e4b` and `gemma4-cpu:latest` models were retained.
- Isolated virtual environment: `.venv` inside the application folder.
- browser-use: **0.13.14**.
- pytest-playwright: **0.10.0**.
- Playwright Chromium, headless shell, and FFmpeg downloaded through its installer.
- Exact installed Python packages recorded in `requirements.lock.txt`.
- `pip check` reported no broken requirements.
- No global Python, Node.js, npm, or Git replacement was performed.
- No paid model API or cloud model fallback was configured.

Local inference avoids paid API/token quotas, but uses the PC's time, memory,
electricity, and storage. Google/website access still needs internet. CPU planning
can take minutes and is not guaranteed to match a frontier cloud model.

## 5. Important files and entry points

All paths below are relative to `C:\Users\Synesis IT\browser-testing-poc`.

| Path | Purpose |
| --- | --- |
| `Start Local Assistant.cmd` | Launch the conversational dashboard |
| `launch_assistant.pyw` | Background launcher with native error reporting |
| `dashboard.py` | Local authenticated server, chat routing, import, jobs, review and replay |
| `dashboard.html` | Browser interface |
| `assistant_engine.py` | Local planning, validated actions, browser-use execution and assertions |
| `LOCAL-ASSISTANT.md` | Everyday dashboard instructions and limitations |
| `qa.py` | Original conservative command-line engine |
| `Start Demo.cmd` | Original five-case local demo launcher |
| `demo_run.py` | Owns the disposable fixture while running/resuming demo commands |
| `demo/server.py` | Loopback-only disposable demo website |
| `demo/cases.csv` | Five synthetic navigation/heading cases |
| `config.example.json` | Original CLI configuration example |
| `config.local.json` | Ignored original CLI configuration |
| `requirements.lock.txt` | Installed dependency versions |
| `pytest.ini` | Test configuration |
| `tests/test_boundaries.py` | Original URL, request, review and resume checks |
| `tests/test_demo_pipeline.py` | Real original Playwright pipeline verification |
| `tests/test_local_assistant.py` | Dashboard/import/security/generation verification |
| `tests/smoke_local_model.py` | Opt-in real Ollama/browser-use/replay smoke fixture |
| `data/sheet-preview.json` | Ignored first-11-case preview; not the full live Sheet |
| `.private/dashboard.json` | Local dashboard settings and conversation state |
| `.private/dashboard-runtime.json` | Per-launch local access token/runtime details; do not share |
| `.private/google-auth.json` | Local Google browser session if the user saves one |
| `.private/*-auth.json` | Locally saved QA session state keyed to origin |
| `artifacts/assistant/` | Dashboard case plans, reviews, results and evidence |
| `tests/assistant_generated/` | Generated dashboard Playwright pytest files |
| `artifacts/assistant-checks.xml` | Eleven-check verification report |
| `artifacts/assistant-smoke/` | Real local-model synthetic smoke evidence |
| `artifacts/a6384e50a4b404e0/report.html` | Original five-case demo report |
| `PC-CHECK.md` | Hardware and runtime inspection record |
| `VERIFICATION.md` | Verification notes across implementation stages |
| `README.md` | Main project entry documentation |

The Desktop shortcut is named **Local QA Assistant**. The dashboard listens on
**`127.0.0.1:8766`** and requires its per-launch token. Use the shortcut instead of
copying private runtime tokens. The model endpoint is **`127.0.0.1:11434`**.

## 6. Verification and corrections

### Verified successful work

- Initial original workflow: six checks passed.
- Five original synthetic demo cases actually ran and passed their heading checks.
- Demo resume skipped already completed cases.
- Original generation/replay refused unreviewed flows.
- Final dashboard verification: **11 checks passed**.
- Real Chromium UI test confirmed CSV import, source-status isolation, interface
  behavior, and request boundaries.
- Generated dashboard pytest code actually ran against a disposable fixture.
- Changing its reviewed result caused it to reject stale approval.
- A real local-model smoke test prepared a plan, ran it through browser-use, and
  passed Playwright replay against the local Help heading fixture.
- After the last small UI change, the dashboard browser test passed again.
- Python compilation checks passed.

### Problems found and corrected

1. **Stale Python 3.12 registration:** switched to working standard Python 3.13.
2. **Initial interface mismatch:** acknowledged explicitly; built the local chat
   dashboard instead of presenting CLI operation as the requested experience.
3. **Small-model navigation completion loop:** bounded the original navigation
   case with an actual terminal assertion and retained the interrupted attempt.
4. **New planner output issues:** early outputs were malformed or omitted required
   fields. They failed validation, not passed. Shortened the prompt, added an
   explicit example, tightened the schema, and then passed the real smoke check.
5. **Generated-test fixture collection on Windows:** an external temporary test
   triggered broad pytest ancestor collection and an inaccessible temp entry.
   The test harness was corrected to use explicit project configuration and a
   bounded conftest discovery path; the generated-test check then passed.
6. **Ollama desktop port conflict:** diagnosed but not automatically restarted,
   because that action was rejected by policy. Its UI resolution remains unverified.

Earlier notes saying “no Sheet was read” describe the initial setup stage. They
were superseded when the user later authorized read-only inspection of Test Cases.
At the end of this conversation, the Sheet had been read but had not been written.

## 7. Current capability boundaries

### Implemented

- A separate local conversational application using Ollama.
- Private Sheet import code using manual Google browser sign-in and CSV export.
- Private local CSV fallback.
- Read-only page observations and reviewed assertions.
- Exact accessible role/name or visible-text checks.
- Visible element counts, numeric display checks, reloads, and specifically
  approved navigation paths/links.
- Review gates, case checkpoints, resume, evidence, reports, and generated pytest
  replay for reviewed successful flows.

### Not established or not enabled

- The Google browser export path has **not been verified with the user's account**.
  This chat's connected Google access is separate from the local application's
  browser login. No credentials were transferred between them.
- No manual QA login was completed as part of this conversation.
- No test was executed against `meet2.synesisit.info`.
- The full Test Cases tab was not read during setup; only the first 11 cases and
  headers were previewed. The full suite's size and coverage are not established.
- No user QA case has a newly verified Pass/Fail outcome from this work.
- No Sheet cells, statuses, steps, or expected results were changed.
- Sheet write-back is not enabled. A later explicitly approved step is needed to
  implement/update only Status and Actual Result.
- No generic arbitrary clicking, typing, form submissions, or mutation tools.
- No create/edit/delete/upload/invite/email/payment testing.
- No automatic authoritative backend/membership reconciliation.
- No integration of this application into Ollama's official chat window.
- No claim that the 4B local model can reliably execute the complete real suite.

Pass in the dashboard means the **human-reviewed plan ran and all of that plan's
assertions passed**. A mistakenly weakened or incomplete plan does not establish
the full original requirement; reviewing plan coverage is necessary. Unverifiable
criteria should stay Blocked rather than be silently removed.

## 8. Privacy and safety decisions

- Application/model traffic uses loopback endpoints for local inference/UI.
- Dashboard API access requires a random per-launch token and exact Host/Origin
  checks; evidence access is constrained to the artifacts directory.
- No arbitrary model-generated Python or shell command is executed.
- Original data, browser session credentials, chat state, reports, screenshots,
  traces, and generated artifacts are excluded from Git where configured.
- Local browser state contains session credentials and is not automatically
  encrypted by this application. Do not share `.private/`, data, or evidence.
- The test browser blocks mutation HTTP methods, third-party requests, unapproved
  navigation, service workers, WebSockets, popups, and downloads as configured.
- These restrictions can block legitimate read-only POST/GraphQL/external-resource
  applications. Such cases need review, not silent weakening of guards.
- GET requests can still have server-side effects. Only approve paths already
  known to be read-only in the disposable QA environment.
- Sign-in browsers are manually controlled to allow normal authentication/SSO;
  do not use them to perform unapproved QA mutations.
- Historical Sheet results remain separate from new local test outcomes.
- Suggested rewrites are review proposals, not automatic Sheet edits.

## 9. What the user should do next

1. Keep Ollama running. There is no need to choose an Ollama Apps integration.
2. Open **Local QA Assistant** from the Desktop shortcut.
3. For current full Sheet data, click **Google sign-in / import**, sign in personally,
   and click **Finish Google sign-in / import**. If Google blocks that browser,
   privately export the tab to CSV and use the local import control. Do not make
   the Sheet public or paste credentials.
4. Confirm the target is a disposable QA environment.
5. Click **Open QA browser / sign in**, sign in personally, and manually open the
   read-only Organizations page. Click **Save QA session** in the dashboard.
6. Select up to five appropriate read-only cases and type **run**. Missing plans
   are prepared first. Review their full expected-result coverage before approval.
7. Run approved plans. Inspect actual observations and evidence.
8. Approve only successful fully reviewed flows for generated Playwright tests,
   then use **Replay reviewed**.
9. Use **pause** / **resume** for small batches and **Download report** for results.
10. Use **Stop local assistant** to stop its background server when idle.

Do not treat the preview's old Sheet Pass statuses or the synthetic demo's Pass
results as evidence that the real QA website has been tested.

## 10. Sources consulted during the conversation

- [Browser-use quickstart](https://docs.browser-use.com/open-source/quickstart)
- [Browser-use Ollama example](https://github.com/browser-use/browser-use/blob/main/examples/models/ollama.py)
- [Browser-use project requirements](https://github.com/browser-use/browser-use/blob/main/pyproject.toml)
- [Playwright Python installation](https://playwright.dev/python/docs/intro)
- [pytest-playwright package](https://pypi.org/project/pytest-playwright/)
- [Qwen3 4B Instruct model](https://ollama.com/library/qwen3:4b-instruct)
- [Ollama Windows documentation](https://docs.ollama.com/windows)
- [Ollama integrations](https://docs.ollama.com/integrations)
- [Ollama API tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama desktop MCP/tool support feature request](https://github.com/ollama/ollama/issues/11603)
- The supplied Google Sheet, read-only through the connected Google Drive tools.

Product feature observations describe what was checked during this conversation;
they are not guarantees about later Ollama versions.
