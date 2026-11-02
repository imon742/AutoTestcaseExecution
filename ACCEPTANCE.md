# Acceptance record — 29 October 2026

## Environment and completed checks

Windows 11 Pro (10.0.26300), Python 3.13.6, Node 24.14.1. Approximately 31.8 GB total RAM and 59 GB free disk at inspection. No system version replacement was needed. Ollama discovered both installed local tags: `qwen3:4b-instruct` and `gemma4:e2b-it-q4_K_M`. Its observed Qwen allocation was CPU-only (`size_vram: 0`); the agent did not force CPU allocation.

`python -m pytest tests/agent -q --junitxml=artifacts/agent-all-checks.xml`: **14 passed**. `compileall` passed for the new package.

Tests exercise real Playwright browsers against an isolated local HTTP fixture, with a deterministic model-protocol test double unless explicitly identified as real-model runs. They cover:

- Seven source cases/two historical Pass: default five selected; include-Pass seven.
- CSV/XLSX import, preserved original workbook, other tab, formula, formatting, and result-copy.
- SQLite recovery, atomic commits, no duplicate completed execution, and no repeated uncertain write after a crash.
- Exact fixture/category approval, domain boundary, local-only model checks, redaction.
- Login, form validation, create/edit/delete, upload, select/check, modal, session expiry/relogin.
- An observed application contradiction gives Fail; missing locator and simulated model timeout give Blocked. Remaining cases continue.
- The 12-case fixture queue produces nine Pass, one Fail, two Blocked with the protocol test double. Those outcomes test classification, not actual-model intelligence.
- Unmapped business prose and unproven preconditions never receive an automatic Pass.
- Google writeback is tested against a fake API session: exactly the mapped two cells, RAW values, changed-source rejection, and readback. No real Google Sheet was written.
- A saved successful flow exports to pytest and actually replays with Playwright without model inference.
- Dashboard import/model/scope controls render in Chromium; unauthorized local API requests are rejected.
- Clean source packaging excludes private state, environment, source cases, artifacts, and legacy files.

Live model outcomes and exact per-case evidence are under `artifacts/agent-acceptance/`; the final summary below records completed live runs separately from protocol-double tests.

### Live local model checkpoint before shutdown

- Qwen `qwen3:4b-instruct`: run `6d8bdff25d3848cb80b0db96af5fadec` completed **5/5 Pass**: records navigation, required-field validation, disposable creation, edit, deletion. Screenshots/traces/report are saved. Upload was not included in this run.
- Gemma `gemma4:e2b-it-q4_K_M`: run `d168812cdee1414b9aede22e0a0b1a42` observed **3 Pass** (navigation, validation, creation). The edit case hung and the test process was interrupted; recovery records it as NeedsReview, not Pass. Deletion was Not Run. This is not a completed Gemma acceptance run.
- Both runs used only the synthetic local fixture. Screenshot/trace/browser cleanup now has explicit time limits; the interrupted Gemma path still needs a fresh acceptance run to validate that correction.
- User requested a safe stop before laptop shutdown. The new dashboard was idle and was closed. No more tests were started after that request.

## Not demonstrated / remaining setup

### Resumed local validation

Fresh Gemma run `7fb4f71d907e4bf5b08d594dd53b0684` completed its queue: F04 edit, F05 deletion, F06 upload were all **Blocked** by the 90-second Ollama response timeout. Each result/evidence was saved and the runner advanced without hanging. This validates bounded failure handling, not successful Gemma execution. No real application defect is established by these timeouts. Model installation alone does not establish usability for this workflow.

The acceptance script now validates Ollama availability before creating a fixture or run, avoiding an empty queue when the service is stopped.

Qwen upload run `dda08067f4894a2d9ccc757606dff790` also completed F06 as Blocked by model timeout. A separate tiny eight-token Qwen generation probe timed out at 20 seconds without browser automation. Ollama logs showed active slow generation (~4 tokens/sec), 90-second HTTP 500 chat responses, and Vulkan memory-driven eviction. Root cause remains unresolved; do not interpret these as website failures. Current blockers concern local inference responsiveness. The earlier Qwen five-case pass remains valid historical evidence.

The handoff's real-site pilot of ten mixed QA cases with manual comparison has **not** been performed. No real QA credentials, legacy session files, or private OAuth files were opened. No real site records, uploads, messages, payments, or Google Sheet cells were changed.

Real-site setup still needs exact allowed origins, deterministic login/handoff locators, local vault credentials or new authorized auth state, specific disposable fixture approvals, and mappings for complex source steps/criteria/preconditions. These are application-specific inputs, not an installation step that a model can safely invent.

Authoritative backend, mailbox/OTP, and payment adapters are not implemented. Such criteria remain Blocked/NeedsReview. Natural-language plans are suggestions until their source coverage is established. The app does not prove that arbitrary test prose is valid, nor automatically rewrite source Test Steps.

Google OAuth authorization and live writeback remain unverified with the user's account. There is a check/write race if another editor changes a Sheet after its source check; avoid concurrent row edits during sync. Spreadsheet writeback failure retains the result locally and does not replay browser actions.

Authentication snapshots, screenshots, and traces can contain private app data and remain ignored local runtime files. The deliverable is source-only. The previous uploaded archive reportedly contained saved sessions; invalidate any sessions that were exposed through that archive.

The existing legacy tools are preserved. The new primary dashboard is on port 8780 and does not use browser-use's separate blank browser. A single Playwright owner executes bounded structured actions using local Ollama, as permitted by the handoff.
