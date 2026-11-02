# Today's QA work and the local chat-agent goal

Date: 1 November 2026, Asia/Dhaka.

## What you want

You want to chat with a local QA assistant in ordinary language: give it a test-case Sheet, sign into a disposable QA environment, ask it to run cases that are not Pass, and let it execute, verify, save evidence, and update the Sheet after every case. It must resume after interruptions without depending on ChatGPT's usage window.

That requires **a local model plus an application that gives it browser, verification, checkpoint, and spreadsheet tools**. A downloaded model by itself cannot operate the browser or your project folder. No model was trained or fine-tuned today.

## What actually executed today's tests

Codex directly inspected and operated the signed-in test browser, interpreted the case instructions, compared visible outcomes with expected results, and wrote results through the connected Google Drive/Sheets tools. Today's successful direct workflow did **not** use Ollama to choose the actions.

The browser session followed your demo portal into Centralized Management. Credentials were entered by you in the browser. We did not paste account passwords into chat, source, or this document. Login/JWT URLs and authentication state must not be copied into prompts, reports, or shared archives.

Do not assume the local Ollama runner can already reproduce today's complete workflow. It has useful components, but local inference, free-text case interpretation, authentication handoff, and live Google authorization still need end-to-end validation.

## Cases and results

The starting source contained 393 cases: 30 historical Pass cases were skipped and 363 cases entered the pending queue. You later authorized editing the original working copy, titled **Dummy of SA_Organization Management**, in its **Test Cases** tab. The earlier copy was used for initial inspection; it is not the current writeback destination.

Our checkpoint now records **15 cases investigated: 6 Pass, 2 Fail, 7 Blocked**. **348 cases remain Not Run** in this checkpoint. These counts exclude the 30 historical Pass cases and do not describe any independent edits or tests performed by others.

| Case ID | Status | Actual observation / limitation |
|---|---|---|
| SA_RTC_008_002 | Blocked | Total Organizations displayed 5,391 and 40% versus last month. No authoritative count/scope/prior-month baseline was available to certify the full expectation. |
| SA_RTC_008_003 | Blocked | Total Users displayed 9,596 and 10%. Full count and percentage reconciliation remained unverified. |
| SA_RTC_008_004 | Blocked | Actively Using displayed 6,493 and 20%. Full scope/baseline reconciliation remained unverified. |
| SA_RTC_008_009 | Blocked | One populated About cell matched its saved organization type/location. The case required two populated fixtures; the first 40 rows exposed only one at that time. |
| SA_RTC_008_010 | Pass | Five directory Users values of 1 matched the same organizations' loaded User List views, each with one member and no further member page. |
| SA_RTC_008_011 | Blocked | Company names were plain text, not selectable links. Details opened through the Actions pencil, which is a different route from the specified Company-cell action. |
| SA_RTC_008_014 | Fail | Edit pencils were visible, but were SPAN controls without native keyboard focus, button/link semantics, or accessible names. This contradicted the accessibility requirement. |
| SA_RTC_008_015 | Pass | All 20 first-page rows and displayed cell values remained identical after refresh. This verdict covers the observed first page; visible rows did not expose record IDs. |
| SA_RTC_008_016 | Pass | Approved organization QA_CODEX_20261101_ORG_A was created once. Success modal appeared; after reload its row persisted and Total Organizations increased from 5,391 to 5,392. Total Users increased to 9,597; Actively Using remained 6,493. |
| SA_RTC_008_017 | Blocked | Name-only Draft save was rejected for missing owner data. After separate owner-fixture approval, the completed Draft save returned “Submission Failed: Failed to create organization draft. Please try again.” Count-consistency testing could not complete. Root cause was not established. |
| SA_RTC_008_018 | Blocked | A controlled Draft's loaded name matched its directory row. The Draft editor lacked a User List tab, preventing the full status/member cross-view verification. |
| SA_RTC_009_003 | Fail | Plain CODEX search briefly returned the correct single organization, then reverted to unrelated first-page rows while CODEX remained visible. An initial provisional Pass was corrected in the Sheet when the later evidence contradicted it. |
| SA_RTC_009_004 | Pass | Exact approved temporary owner-email search remained on the correct single organization, with Page 1 of 1 across follow-up observations. Invitation delivery or acceptance was not certified. |
| SA_RTC_009_013 | Pass | ### settled to “No organizations available” without a visible crash/error. Clearing the query restored 20 normal rows. Result was saved before starting the next case. |
| SA_RTC_009_015 | Pass | A 500-character nonmatching search settled to the no-results state. No visible server-error UI/crash appeared; search and navigation controls remained within the viewport. Clearing the input succeeded. Private backend logs were not inspected. |

Counts are point-in-time observations. Later screenshots showed totals changing as other QA fixtures appeared; those externally created records were not claimed as our work.

## What changed in the application

- You approved creating **QA_CODEX_20261101_ORG_A** and attempting **QA_CODEX_20261101_DRAFT_A**.
- The create form disclosed an automatic organization super-admin/owner invitation. We obtained separate confirmation for that access grant to the temporary mailbox you authorized.
- The organization was created and its persisted count change verified.
- You separately approved reusing that owner fixture for the named Draft. The Draft submission failed; it must not be retried blindly or represented as successfully created.
- No deletion, upload, payment, or unrelated record edit was performed in these direct batches.
- Other application records and the user’s existing organization edit form were left untouched. The last two read-only cases used a separate browser tab.

The mailbox address is not needed in a shared implementation guide. The authorized recipient/fixture details remain in the private execution checkpoint and the application's test record. Never store temporary-mail passwords or invitation tokens in this document.

## What changed in the Sheet

For each completed case, the workflow matched the case ID and source content, wrote the result, and read it back before advancing.

| Column | Use |
|---|---|
| Actual Result (J) | Factual observations, including incomplete verification and errors. |
| Status (K) | Pass, Fail, or Blocked based on the observed result. |
| Remarks (S) | Evidence filenames, fixture gaps, qualifications, and corrections. Existing remarks were preserved. |
| Test Steps (H) | Only justified clarifications: explicit keyboard/name/role checks; required Draft owner fields; checking that search results do not revert after loading. |

Expected Result, case IDs, historical Pass results, unrelated columns, and sheet layout were not intentionally changed. A step correction must never weaken an expected result merely to obtain Pass. The failed search's earlier provisional Pass was explicitly superseded, not hidden.

## How the execution loop worked

1. Read the Sheet and select a small pending case/batch.
2. Check authentication and the case's prerequisites.
3. Inspect the current rendered page; choose controls from observed labels, roles, or DOM attributes.
4. Perform the required action in the same signed-in browser context.
5. Wait for the relevant loaded state. Do not treat a transient result or a loading row as final data.
6. Compare every expected obligation with observable evidence. Follow up through the same organization's details/member view where needed.
7. Save a screenshot or DOM/text evidence, then checkpoint the outcome locally.
8. Write Status, Actual Result and Remarks to the matched Sheet row; apply justified step corrections separately.
9. Read back the written cells. If sync fails, retry sync only, not the browser side effects.
10. Check usage and choose the next case. Preserve the next-case pointer and unresolved fixture requirements before stopping.

For readable UI controls, prefer accessible locators. The observed edit pencils lacked these semantics, so their actual DOM control was inspected and the accessibility defect recorded rather than inventing a working accessible locator.

## Classification rules

- **Pass:** the executed scope met all required, verifiable criteria.
- **Fail:** observed behavior contradicted a required result; preserve the evidence and the original requirement.
- **Blocked:** a prerequisite, fixture, authority/baseline, browser/model capability, or required prior action prevented a complete verdict. It does not mean the application passed or failed the unexecuted checks.
- **Not Run:** no case verdict has been established through execution.
- **NeedsReview:** useful for the local engine's unresolved interpretation proposals; do not silently turn a model's suggestion into a certified Pass.

A visible numeric summary alone does not prove counting correctness. A success modal alone does not establish persistence: the create-count case also checked the row and count after reload. Missing screenshots do not justify fabricated evidence; DOM/text observations can be recorded with that limitation.

## Local system that would reproduce this conversation and execution

Build a **local chat-based QA application**, rather than requiring interaction through Ollama's own plain chat window. Reuse the existing project instead of starting another disconnected demo.

### Components

1. **Chat UI:** accepts requests such as “run non-Pass cases,” shows the proposed scope, lets you sign in manually, displays approvals and results, and answers “what is running?” from stored state.
2. **Local inference adapter:** discovers installed Ollama models and submits one case plus a bounded current-page observation. The installed Qwen and Gemma tags are candidates to validate, not a promise of Codex-equivalent performance.
3. **Supervisor:** owns queue selection, prerequisites, budgets, approvals, verification, checkpoint commits, and progress. The model cannot override these controls.
4. **One Playwright browser owner:** executes approved structured actions in the intended signed-in context. Avoid opening a second blank agent browser.
5. **Deterministic verifier:** performs locator/text/value/count/URL checks and authorized cross-view or fixture comparisons. More complex business requirements need grounded coverage mappings or an authorized data adapter.
6. **Result writer:** local SQLite plus evidence files; CSV/XLSX result copies; direct Google Sheets updates through a locally authorized official Google OAuth integration.
7. **Replay store:** reviewed, successful flows become repeatable Playwright tests, so subsequent runs can avoid inference. Failed replays must not automatically repeat already-applied business side effects.

Codex's connected Google tools and in-app browser APIs do not become available to Ollama merely by copying a prompt. A standalone local application needs its own browser executor and Google authorization. Anonymous public Sheet reading does not provide permission to write it.

### Model input and output contract

Give the model the current case, expected obligations, approved fixture references, current visible controls, and a few recent actions. Do not send passwords, cookies, hidden tokens, entire mailbox histories, or the complete suite in every prompt.

The model returns a bounded structured proposal, for example:

```json
{
  "case_id": "CASE-ID",
  "kind": "fill",
  "locator": {"by": "role", "role": "searchbox", "name": ""},
  "value": "approved known search text",
  "category": "read",
  "reason": "Perform the case's search step"
}
```

The host validates that the locator matches the observed page, the action category is permitted, and any write uses the specifically approved fixture. It executes deterministic browser code; it must not execute model-generated Python, JavaScript or shell commands. It then returns an observation to the model and runs the independent verifier.

The example is an interface illustration, not a ready-to-run browser selector. Real controls must be grounded from the actual page.

### Conversation commands to support

| User message | Local app behavior |
|---|---|
| “Use this Sheet and run cases not Pass” | Import, identify pending IDs and execution scope, and display prerequisites. |
| “I signed in” | Verify a logged-in ready state in the correct browser; do not equate the message alone with a saved session. |
| “Approve this fixture/action” | Store a specific, reviewable approval for that action and fixture. |
| “What happened?” | Read the last committed result and evidence; do not invent progress. |
| “Pause/stop” | Stop safely, commit current evidence, and expose any uncertain side effect. |
| “Resume” | Continue pending work without rerunning committed cases or unresolved writes. |
| “Correct the case steps” | Propose grounded clarifications, preserve expected behavior and record the reason. |

## Existing project and proven limits

Project folder: `C:\Users\Synesis IT\browser-testing-poc`.

The existing `local_qa` package already contains importer, Ollama, browser owner, verifier, SQLite store, authentication, writer, replay and dashboard modules. It does **not** yet demonstrate the full standalone conversational workflow described above.

Earlier fixture acceptance recorded 14 automated checks passing, a five-case real-Qwen success, and incomplete or timed-out Gemma/live-upload runs. Later targeted UI/origin tests, read-only-precondition behavior checks and a real WebSocket echo regression also passed individually. Do not describe this as a freshly rerun complete test suite after every subsequent change.

Earlier actual-site runs exposed authentication setup gaps, overly early precondition stopping, and a runner WebSocket bug. The WebSocket bug was fixed: Playwright's `WebSocketRoute.connect_to_server()` is synchronous and must not be awaited. The new echo regression exercised a real browser connection.

Local model responses sometimes timed out even though the installed model was detected. Stopping a competing generation allowed a tiny prompt to respond, but did not resolve every long action/planning timeout. Model installation, a tiny prompt response, or a fixture-only pass is insufficient evidence of reliable whole-suite operation.

The current local dashboard is primarily form-based; the desired natural-language chat orchestrator is remaining work. Avoid claiming that today's direct Codex reasoning has already been transferred into it.

## Next implementation and validation steps

1. Add a local conversation UI on top of the existing supervisor and persistent queue.
2. Make sign-in and saved-session state explicit. Show whether the target page is authenticated, whether the session is saved, and what to do if it expires. Avoid silent timeout/false-ready states.
3. Ground free-text step, precondition and expected-result interpretation before certification. Read-only exploration can collect evidence while unresolved requirements remain reviewable; business writes must not proceed on assumed prerequisites.
4. Validate local model output and latency on one real read-only case, then a small mixed batch against manually compared outcomes. Require no false Pass before expanding.
5. Implement and validate local Google OAuth writeback with precise row mapping, changed-source checks and full readback. Do not read legacy saved credentials to bypass setup.
6. Reconcile the failed Draft attempt and email reuse rules before any retry. A new recipient/access grant needs the relevant approval.
7. Turn successful reviewed flows into deterministic replays and compare model-free results with the original evidence.
8. Resume pending tests in batches. Some remaining cases require known non-owner admins, regular members, Unicode fixtures, subscription baselines, uploads, mailbox verification, or sandbox payment adapters; mark missing prerequisites honestly.

## Checkpoints, evidence and usage

Primary private execution checkpoint:

`C:\Users\Synesis IT\browser-testing-poc\artifacts\direct-codex-qa\2026-11-01\checkpoint.json`

Evidence is in the same folder. Relevant files include:

- `organization-before.json`, `organization-after.json`, `membership-comparison.json`
- `organization-directory-ready.png`
- `approved-org-created.png`, `approved-org-count-after-refresh.json`
- `draft-required-owner-validation.png`, `draft-submission-failed.png`, `draft-post-check.json`
- `search-codeX-final.png`, `search-substring.json`, `search-substring-underscore.json`
- `owner-email-search.png`, `owner-email-search.json`
- `search-symbols.png`, `search-symbols.json`
- `search-500-characters.png`, `search-500-characters.json`

The original batch-01 HTML/CSV report covers only the first nine cases. The live Sheet and latest JSON checkpoint contain later corrections; do not treat the older report as the final total.

You requested saving after every case to survive usage exhaustion. We initially stopped starting new cases at 24% remaining, and the final checkpoint brought the meter to 19%. You explicitly requested continuing with about 18% remaining; two additional read-only cases were executed and synced individually. The last reported meter was 5% remaining. Do not treat that historical percentage as the current account balance; check the live meter before another run.

A local Ollama application does not consume Codex's chat allowance for its inference. It still has RAM/CPU/GPU, model-context, latency and external-service limits. Keep the queue and evidence outside the model's conversation context so resumability does not depend on a long chat history.

## Resume request for a future assistant

“Read this handoff and the latest checkpoint. Check current usage and the destination Sheet. Continue only cases not already Pass, preserve all results and evidence, and sync each completed case before proceeding. Use the signed-in meet2 demo through its normal portal-to-CM handoff. Do not repeat the failed Draft creation blindly, disclose tokens, or make unapproved record changes. Build the local conversational executor as a separate validated milestone; do not claim it already reproduces Codex's direct execution.”
