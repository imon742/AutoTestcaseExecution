# Upgrade inventory — 29 October 2026

## Existing files and disposition

| File | Observed responsibility | Change |
|---|---|---|
| dashboard.py / dashboard.html | staged read-only dashboard and manually saved authentication | Preserve source backup. Make the primary launcher open the new queue/execution UI. |
| assistant_engine.py | limited plans executed through a separate blank browser-use session | Preserve as legacy; new agent uses a single Playwright-owned context with structured actions. |
| qa.py | original guard, saved-state copies, assertions and terminal approval | Preserve diagnostics; do not use its network interception or input() in normal new runs. |
| case_import.py | anonymous public Sheet CSV and basic XLSX import | Preserve; extend normalized source metadata in local_qa/importer.py. |
| simple_local.py / Start Simple QA.cmd | five-case manual-login starter | Preserve separately; not the full product. |
| launch_assistant.pyw / Start Local Assistant.cmd | existing Desktop entry point | Keep entry point; route it to the upgraded application. |
| requirements.lock.txt | old resolved environment | Keep; add explicit agent requirements and record verified versions. |
| tests/ | prior regression and fixture checks | Preserve; add independent new-agent tests without reading private auth/session files. |
| .gitignore | excludes primary private folders | Extend for new DB, OAuth exports, archive staging, backups and caches. |
| .private / artifacts / data / .venv | existing credentials, outputs and runtime | Do not inspect/copy/export legacy credentials or the venv. Preserve on disk. |

## New files

- local_qa/models.py: normalized cases, result/criterion models and run policy.
- local_qa/store.py: SQLite runs/cases/attempts/evidence/flows/writebacks/events;
  atomic commits and crash recovery.
- local_qa/importer.py: CSV/XLSX/public Sheet/OAuth Sheets inputs, mapped columns,
  original rows and source hashes; default non-Pass and scenario filters.
- local_qa/ollama.py: local discovery, structured output, optional vision, model
  selection/context/timeout tuning; no cloud fallback or forced CPU setting.
- local_qa/auth.py: Windows Credential Manager and deterministic login adapters.
- local_qa/browser.py: one context, domain boundaries, snapshots, permitted
  locator actions, traces/screenshots, no generated-code execution.
- local_qa/verifier.py: atomic criteria and mechanical assertions; coverage required.
- local_qa/supervisor.py: bounded observe/act/verify loop, isolated cases, retries,
  pause/resume, replay-first memory and factual classifications.
- local_qa/writers.py: CSV/Excel result copies, source conflict checks, OAuth-only
  mapped Sheets writeback and queued retry.
- local_qa/app.py / ui.html: import, model selection, credential setup, scope,
  exact fixture/action approvals, run/pause/resume/stop, export/evidence controls.
- local_qa/fixture.py: disposable local application for mixed-action acceptance tests.
- safe_export.py: allowlisted clean source archive; no credentials, sessions,
  traces, user input files, target URLs, or installed environments.
- tests/test_agent_*.py: acceptance, failure handling, source preservation,
  policy, credential redaction and queue/replay/writeback verification.
- AGENT-GUIDE.md / ACCEPTANCE.md: runnable Windows instructions and observed limits.

## Acceptance boundary

The handoff is the target specification, not evidence of completed work. A real
10-case mixed-action pilot requires a configured QA login and specifically approved
disposable fixtures/actions. Existing blanket access does not identify records to
delete, invitations to send, files to upload, or sandbox payments to make. No such
real side effects will be assumed approved. Google OAuth credentials are configured
locally; no key/password/token is requested in chat. The Gemma download is managed
by the user; discovery will use the exact installed tag reported by Ollama.
