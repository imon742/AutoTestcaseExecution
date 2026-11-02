## Additional low-allowance run

User explicitly requested continuing below previous 20% threshold. Ran 009_013 (### then clear) and 009_015 (500-character Z search, UI layout, clear recovery). Both Pass; each was written immediately to original Sheet and read back before proceeding. PNG/JSON evidence saved. Local direct checkpoint now six Pass, two Fail, seven Blocked; 348 remaining Not Run in this checkpoint, excluding 30 historical source Pass. Browser CM tab4 was used to leave the user’s existing Synesis IT edit form in tab2 untouched. Observed new QA OM009 fixtures created externally; do not claim creating them or change them. Stop now because usage is low.

## 1 November: direct Codex testing and live Sheet checkpoints

User switched results destination to original spreadsheet 1pDgSUjcMEjJJLicpeCrwmyFVwwDT9kLhSZN6e1yfRx4, Test Cases sheetId 81082. Authorized edits: Status K, Actual Result J, Remarks S and Test Steps H when observed corrections are justified. Preserve Expected Result and historical Pass. Connected Google Drive plugin used; every completed result was written and read back. Current direct-batch results: 4 Pass, 2 Fail, 7 Blocked; 350 pending cases still Not Run (30 historical source Pass skipped).

Approved and created QA_CODEX_20261101_ORG_A on meet2 demo; approved temporary owner invitation to cogidel297@ofags.com. Count 5391 to5392, row persisted after reload; 008_016 Pass saved. User separately approved same owner for QA_CODEX_20261101_DRAFT_A. Save as Draft with required owner data returned Submission Failed; do not repeat without reconciliation. 008_017 remains Blocked because count-consistency prerequisite could not complete; failure reason unknown, possibly owner reuse constraint but unproven.

009_003 initially transient matching CODEX result was superseded: query remained visible but results reverted to 20 unrelated rows. Corrected Sheet from provisional Pass to Fail with screenshot search-codeX-final.png; clarified test step to re-observe settled rows. 009_004 exact new-owner-email search remained stable with only new ORG_A / Page1of1 and passed. Next pending case 009_005 non-owner-admin email needs a known authorized fixture. Earlier first-batch 2Pass (008_010 and015), Fail008_014 (inaccessible pencil controls), sixBlocked baseline/fixture/route gaps all written. All thirteen outcomes in live Sheet.

Stopped between cases at 24 percent remaining to preserve user's 20 percent five-hour reserve (last meter may be slightly lower after checkpoint). On explicit resume, inspect usage first; do not restart at/below20. Keep saving each case to Sheet before proceeding. User approved only the two named mutation fixtures and specific temporary owner grants; other creates/edits/deletes/uploads/payments require specific approval. Do not expose JWT URLs, session storage or mailbox passwords. Browser2 tabs1portal,2CM,3temp-mail marked handoff. If CUA says browser.user unavailable, reset only CUA JS bindings and reconnect existing tab2; session remains.

Evidence/checkpoint: artifacts/direct-codex-qa/2026-11-01/checkpoint.json and PNG/JSON evidence. No Ollama involved in this direct run. Live Sheet is authoritative for latest output cells; local batch01 report covers only the initial nine and is older.

## Session saved and WebSocket repair

User authorized saving the open CM session; confirmed local auth state exists and target is admin.convay.com. Do not open or print that auth file. Initial eight-case run 27bf229f278a44b08b65b00af577e858 hit a genuine runner bug: WebSocketRoute.connect_to_server is synchronous, so awaiting it raised TypeError. Stopped that batch, removed incorrect await, and added a real Chromium/WebSocket echo regression test (passed). New dashboard port 8784/ui4 loads corrected code and saved auth. New eight read-only-case run ac919ae37ec843948044ad931f966f25 started; inspect its actual results before claiming any success. Seven historical Pass and two mutating cases excluded. No Sheet writeback authorized.

## 30 October: scenario run diagnosis and manual sign-in

Scenario SA_RTS_008: 17 source cases, 7 Pass and 10 Not Run. Saved run 02bc4237aa1e4dfcab1fd4cc60a50578 has eight NeedsReview from unknown preconditions and two Blocked for unapproved writes; these are not application failures. Added manual sign-in + save-session buttons and a preflight that prevents an empty-auth run for login-dependent cases. Unknown read-only preconditions now permit exploration but never automatic certification; writes still stop. Two targeted tests passed. Dashboard now port 8782 (ui3 instance), scenario 17-case CSV loaded. Manual sign-in browser requested; user must enter the account, go to target page, and click Save signed-in session. This human flow is not yet verified with the real account. Do not claim tests passed or overwrite old results. Retry after session save as a new run, preserving prior evidence.

## Latest UI update

User requested an easier interface and all origins allowed. Added Allow all origins, enabled by default; restricted address list and login JSON are collapsed into optional details. Side-effect approvals remain separate. New dashboard uses port 8781 and a versioned instance lock so the updated backend opens without terminating the earlier idle dashboard. Targeted policy and Chromium UI tests: 2 passed. Ollama basic Qwen probe succeeded after user stopped other generation (12.3 seconds), but upload retry run 92c7256c016d459eb8a811596baea8d3 still timed out (Blocked). Inference issue is not fully resolved. No real QA/Sheet changes.

# Saved checkpoint — resume after laptop shutdown

## Latest resumed session

The user requested resume. Ollama and the new dashboard were started. Both models were discovered. Fresh Gemma run `7fb4f71d907e4bf5b08d594dd53b0684` completed F04/F05/F06 as Blocked (90-second model-response timeouts), with evidence saved and queue advancement working. Qwen upload run `dda08067f4894a2d9ccc757606dff790` likewise completed F06 as Blocked. A separate eight-token Qwen "Reply OK" probe timed out after 20 seconds, independently of browser automation. Ollama logs show slow ongoing generation around four tokens/sec, HTTP 500 at 90 seconds, and Vulkan memory-driven model eviction; these observations do not yet establish one root cause. Do not mark these cases Fail or Pass. No real QA/Sheet changes occurred.

Next work is local Ollama generation/queue/performance diagnosis before more browser retries. Check whether another Ollama chat/generation is consuming the runner. Do not terminate unrelated user work. The dashboard remains open. The acceptance script now checks model/service availability before allocating a disposable fixture/run. Existing 14 automated checks and earlier Qwen 5/5 remain historical verified results, not claims that the current inference problem is fixed.

User requested a safe stop and save. Do not restart tests automatically on opening this note.

## Where work is saved

Project: `C:\Users\Synesis IT\browser-testing-poc`

Desktop shortcut: **Local Ollama QA Agent**. It points to `.venv\Scripts\pythonw.exe launch_assistant.pyw` in this project. It opens the new dashboard at loopback port 8780. The new dashboard was idle and was stopped safely before shutdown. Ollama itself was left under the user's control.

Primary instructions: `AGENT-GUIDE.md`. Verification/limitations: `ACCEPTANCE.md`. File inventory: `BUILD-INVENTORY.md`. Clean source archive: `exports\Local-QA-Agent-source.zip`.

All source edits are saved on disk. The original top-level source backup is `.source-backup-20261029`. Legacy tools remain present; their old saved credentials were not opened or copied. Do not package `.private`, `.venv`, case inputs, or artifacts in a shared ZIP.

## Implemented

New `local_qa` package: import CSV/XLSX/public Sheet/OAuth; normalized source hashes and scopes; SQLite queue/checkpoints; Windows Credential Manager; deterministic portal/login/handoff and auth-state reuse; single Playwright browser owner; local-only Ollama structured actions; bounded actions and cleanup; criteria/precondition verification; evidence and reports; source-preserving result copies; optional two-column Google writeback; replay-first flow storage; reviewed pytest export and replay; isolated 12-case local fixture; local dashboard and safe source export.

Existing primary `dashboard.py` now routes the launcher into this new application. Previous dashboard source is `legacy_dashboard.py` and the historical test imports were adjusted to reference it. No real QA target is hard-coded into new source/config/docs/archive.

## Verified

- Latest new-agent suite: **14 tests passed**, JUnit `artifacts\agent-all-checks.xml`.
- Package compile check passed.
- Source-only ZIP was inspected and extracted into a temporary folder; clean package imports passed without legacy source.
- Real Qwen model run `6d8bdff25d3848cb80b0db96af5fadec`: F01–F05 all Pass (navigation, validation, create, edit, delete). Reports/evidence in `artifacts\agent-acceptance\<run-id>\`.
- Real Gemma run `d168812cdee1414b9aede22e0a0b1a42`: F01–F03 Pass, F04 NeedsReview after interrupted hang, F05 Not Run. This is incomplete acceptance, not a claimed full pass.
- Both installed model tags were detected. Qwen was CPU-only according to Ollama; GPU allocation was not forced.
- No real QA site actions or Google Sheet modifications occurred.

## Next authorized engineering steps

1. Read this note and `ACCEPTANCE.md`; preserve private runtime and previous evidence.
2. Validate Gemma again on a fresh isolated fixture, especially F04–F06. Do not resume an expired fixture server URL or repeat an uncertain write against a real site. Cleanup timeouts were added after the interrupted run.
3. Complete actual-model upload coverage for Qwen; its completed live run predates the six-case acceptance script change.
4. Current `tests\agent\live_models.py` supports model tag plus optional comma-separated IDs, e.g. `gemma4:e2b-it-q4_K_M F04,F05,F06`. Set project PYTHONPATH when invoking the file directly, or run as `python -m tests.agent.live_models`. It now defaults to six fixture cases. These are synthetic disposable fixtures only.
5. The desktop dashboard process had imported modules before the last edits, but was stopped. Reopening it loads the final saved source. Do not stop or manipulate any unrelated legacy dashboard/process.
6. Finish real-site configuration and the handoff's ten-case manually compared pilot only after the user provides local login configuration and specific disposable fixture/action approvals. Never read the old private credentials to shortcut this step.

## Remaining limits

Ordinary natural-language business cases can be explored, but require explicit source step/expected/precondition mappings before automatic certification. Unconfirmed mappings stay NeedsReview. Unknown backend/inbox/OTP/payment requirements remain Blocked/NeedsReview because those deterministic integrations are not implemented. Google OAuth/live writeback and a real user XLSX import are not demonstrated. Only fake-API writeback and generated fixture workbook preservation are tested. No full real-suite unattended success claim is warranted.

Source writes are limited to Status/Actual Result after approval. AI step improvements remain suggestions. An interrupted mutating case is not automatically repeated after recovery. Remote application side effects cannot be made transactionally exactly-once by the local SQLite queue.
