# Local browser testing proof of concept

**Interactive interface:** double-click **Local QA Assistant** on your Desktop or
**Start Local Assistant.cmd** in this folder. See [LOCAL-ASSISTANT.md](LOCAL-ASSISTANT.md)
for Sheet import, local chat, manual sign-in, review, execution and Playwright replay.
The command-line demo below remains available as a separate setup check.

Windows project: `C:\Users\Synesis IT\browser-testing-poc` (outside OneDrive).
Python 3.13 virtual environment, browser-use, Playwright/pytest, local Ollama.
No paid API or cloud model is used. Package/browser/model downloads need internet;
your QA website can also need internet. Model requests go to `127.0.0.1:11434` only.

## Run the demo

Double-click `Start Demo.cmd` to start the local fixture, explore/resume the five
demo cases, and stop the fixture when finished. Or run the helper directly:

```powershell
Set-Location -LiteralPath 'C:\Users\Synesis IT\browser-testing-poc'
.\.venv\Scripts\python.exe demo_run.py explore
```

For replay after reviewing and generating demo tests, use `demo_run.py replay`.
The helper refuses to run if config.local.json points to your QA site.
The manual two-window alternative follows.

Open two PowerShell windows. Commands below use the venv interpreter directly;
no PowerShell execution policy changes or environment activation are required.

First window: start the disposable read-only fixture (Ctrl+C stops it):

```powershell
Set-Location -LiteralPath 'C:\Users\Synesis IT\browser-testing-poc'
.\.venv\Scripts\python.exe demo\server.py
```

Second window: explore five cases through browser-use and the local model:

```powershell
Set-Location -LiteralPath 'C:\Users\Synesis IT\browser-testing-poc'
.\.venv\Scripts\python.exe qa.py explore --csv demo/cases.csv --batch 5
```

Repeat the exploration command to resume. Finished cases, including Fail/Blocked,
are skipped. An unfinished case is retried; completed cases are not repeated.
If a process was forcibly terminated, first verify it has stopped, then remove
the stale `.private/run.lock` file before resuming. Do not run batches concurrently.

Each case has `result.json`, step screenshots, agent history/conversation, and
`trace.zip` when browser startup succeeded. The dataset directory under `artifacts/`
contains `checkpoint.json`, `report.html`, and `report.csv`. Dataset identity includes
the entire CSV and config, so changing either starts a separate result set.

## Review and convert

Open the reported folder, inspect the screenshots and observed steps, and compare
them with the original case. Use Playwright's local trace viewer if useful:

```powershell
.\.venv\Scripts\python.exe -m playwright show-trace 'artifacts\DATASET\DEMO-001\trace.zip'
```

Record your review for each successful case (this prompts for `APPROVE DEMO-001`):

```powershell
.\.venv\Scripts\python.exe qa.py review --case DEMO-001
```

Generate tests only for reviewed successful cases, then replay up to five:

```powershell
.\.venv\Scripts\python.exe qa.py generate
.\.venv\Scripts\python.exe qa.py replay --batch 5
.\.venv\Scripts\python.exe qa.py report
```

Generated Python tests are under `tests/generated/DATASET/`. They replay the actual
observed paths and use exact accessible role/name assertions. They do not execute
model-generated Python. Approval hashes bind each test to the reviewed result and
configuration; editing a result invalidates approval. Each replay gets its own
status, screenshot, trace, and JUnit XML. Exploration Pass and replay Pass are separate.

Completed replays are skipped. To intentionally retry one, preserve its evidence
first, then remove only that case's `replay.json`. To retry a finished exploration,
preserve its evidence and remove that case's result/review/replay files; re-review
the new result before generation. Never treat an old replay as validating a new flow.

## Use your QA site and Google Sheet

1. Provide the Sheet link in chat when ready; no Sheet has been accessed yet.
2. Initially export only 5–10 read-only cases yourself: Google Sheets > File >
   Download > Comma-separated values. Save locally under ignored `data/`. Do not
   publish the Sheet publicly, create a service-account key, or paste credentials.
3. Map the export to the columns in `demo/cases.csv`:
   `Case ID,Instructions,Start Path,Expected Role,Expected Name,Read Only Approved`.
   Case IDs must be unique letters/numbers/hyphens/underscores. Set approval to
   `yes` only after reviewing that the case is a single navigation/visible-element
   check and the endpoint is read-only. Do not mark multi-step, click, form, or
   ambiguous cases approved for this limited proof of concept.
4. Edit ignored `config.local.json`: set `base_url` to your disposable QA origin,
   and `approved_read_paths` to explicitly approved read-only relative paths.
   Do not put credentials or tokens in URLs or CSV. An ordinary visible heading
   is a useful first expected role/name. Unclear instructions need human review.
5. Sign in yourself in a dedicated browser opened by this command:

```powershell
.\.venv\Scripts\python.exe qa.py login
```

After signing in, press Enter in the terminal. Local browser session state is
stored under ignored `.private/`, keyed to the QA origin. The login browser is
manually controlled and does not apply exploration request restrictions, allowing
SSO. The agent never receives a password or a tool for typing one. Delete the
origin's auth JSON to forget the saved session. If auth uses unsupported browser
storage, exploration will block or show the login page; do not paste credentials.

Then explore your exported cases:

```powershell
.\.venv\Scripts\python.exe qa.py explore --csv data/cases.csv --batch 5
.\.venv\Scripts\python.exe qa.py report --csv data/cases.csv
.\.venv\Scripts\python.exe qa.py review --csv data/cases.csv --case YOUR-CASE-ID
.\.venv\Scripts\python.exe qa.py generate --csv data/cases.csv
.\.venv\Scripts\python.exe qa.py replay --csv data/cases.csv --batch 5
```

## First-trial boundary

This proof of concept supports **navigation and observation**, not unrestricted
click/typing exploration. browser-use has only `visit_page`, `observe_page`, and
`done`; all its default action tools are removed. The real test browser is managed
by Playwright behind these restricted tools. browser-use also uses an inert local
blank browser for its internal DOM lifecycle. Vision is off for the small text model;
screenshots are still captured locally for review.

The test browser blocks mutation HTTP methods, third-party requests, unapproved
navigation, service workers, WebSockets, popups, and downloads. Some read-only
applications use POST/GraphQL, external resources, or SSO redirects; these will be
Blocked for review. Do not weaken guards merely to get a green result. GET endpoints
can have side effects too: only approve paths whose behavior you have verified.
This is a conservative trial boundary, not a guarantee about arbitrary server code.

For a navigation-only case, the custom visit tool automatically captures page
text and a screenshot, checks the exact expected accessible element, and returns
a terminal result. This avoids small-model completion loops. The runner independently
checks the element again before recording Pass. More general exploration needs
additional reviewed tools and is intentionally outside this initial runnable scope.

Do not include create/edit/delete/invite/upload/email/payment cases. Those require
an explicit explanation and approval of the specific fixture and action before
extending the tools. Generic setup authorization is not approval for such tests.

## Result semantics and privacy

- Pass: the local agent actually navigated successfully and Playwright independently
  observed the exact expected accessible element. Human review is still required
  before conversion. This does not prove requirements beyond that assertion.
- Fail: execution reached the expected-result assertion and it failed.
- Blocked: missing/ambiguous data, disallowed operation/request, local-model error,
  timeout, unavailable login, interruption, or another execution problem.
- Not Run: no execution recorded. The full dataset appears in the report, including
  cases outside the current batch.

All session state, data, reports, screenshots, traces and model conversations stay
local and are ignored by Git. They can contain sensitive QA content: do not upload
or commit them. No Google credentials, API keys, or payment details are needed.
Application access/session state is local, not automatically encrypted by this tool.
Existing Ollama settings are not changed. The runner selects only the configured
local model at a hard-coded loopback endpoint and disables browser-use telemetry
and cloud sync for its process. Cloud provider dependencies installed by browser-use
do not select a cloud model.

No Sheet write-back implementation is enabled. After your first-batch review and
explicit approval, a separate controlled step can update only `Status` and
`Actual Result`, matched by unique case ID. The local report is not a Sheet update.

## Reproduce the environment

Installed versions are recorded in `requirements.lock.txt` after verification:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m playwright install chromium
ollama pull qwen3:4b-instruct
```

CPU inference (`num_gpu: 0`) is the default because this PC has only 2 GB NVIDIA
VRAM. Context is capped at 8192 and cases run sequentially. Close memory-heavy
applications if Ollama runs out of RAM. An Ollama failure becomes Blocked; there
is no cloud fallback. Keep Ollama running locally; `ollama serve` is needed only
if its desktop app/server is not already running.
