# Verification — 28 October 2026

## Real runtime-error cause confirmed — 29 October 2026

The latest guarded run had blocked twelve GET navigations to CM /login during SSO.
Permitted that specific handoff route while bootstrap is active and waited for the
callback to settle. A real saved-session diagnosis then revealed the runtime
overlay's exact text: "WebSocket disabled in read-only trial". That exception was
thrown by our injected constructor override, not evidence of a broken user login.

Removed the throwing override and blocked socket transport through Playwright's
WebSocket routing instead. No socket connects to a server or sends application
messages. Known webpack development sockets are optional. Firebase remains blocked
but is classified as optional only for Organization checks that do not require chat.
Unknown/chat-required connections remain essential and blocked.

The real saved-session handoff was rerun and returned Ready. The resulting CM
dashboard screenshot (artifacts/handoff-diagnostic/page-2.png) showed the actual
Organizations navigation and no runtime overlay. This is a real navigation result,
not a case Pass. Diagnostic details are in artifacts/handoff-diagnostic/result.json.
Version 2026-10-29.3 contains the fix. The browser regression now creates a WebSocket
during the callback, verifying that construction does not synchronously crash the app.

## Portal handoff correction — 29 October 2026

The user clarified that entry must start at the meeting site and go through Admin
Settings to CM on port 85; direct CM navigation reportedly produces a runtime error.
Updated version 2026-10-29.2 separates the sign-in origin from the CM destination,
captures/restores both origins' sessionStorage, and repeats the observed fixed
Admin Settings navigation during planning/execution/replay. Popups are permitted
only from the configured portal to the configured CM origin; other popup/write
restrictions remain. No direct-CM fallback is used after a failed handoff.

Seventeen checks passed. A real two-origin Chromium fixture deliberately showed
a runtime error on direct CM access and then successfully loaded Organizations
through an Admin Settings popup with opener/postMessage and both restored sessions.
This verifies the mechanism on a local fixture, not the real site's runtime-error
cause or successful execution of its Organization cases. A fresh manual portal →
CM sign-in/save and real-site validation are still required after loading the update.

## Update — 29 October 2026

- Public Google Sheets import was verified without cookies or credentials: 385
  cases from the supplied Test Cases tab. Added bounded local .xlsx/CSV import.
- Run now automatically prepares/grounds/executes selected supported read-only
  cases. It no longer requires manual plan approval for that trial. Successful
  flow review is still required before Playwright conversion/replay.
- Added read-only execution authorization records without falsely labeling them
  human plan reviews, sessionStorage persistence, retry of Blocked cases, and
  navigation from an actually observed same-origin left-navigation link.
- Sixteen automated checks passed, including Excel/public import, a one-click
  real Playwright fixture execution with no manual plan gate, mutation blocking
  and resume behavior.
- A real saved-session attempt at the previously configured /home opened the
  meeting dashboard. The required Organizations left-navigation link was absent;
  the case was Blocked, not passed. Added an early specific error for this mismatch.
- The user supplied the correct CM URL: https://meet2.synesisit.info:85/.
  Anonymous front-page read returned HTTP 200. Configured that origin, retained
  previous settings and session files, and started dashboard version 2026-10-29.1
  (the earlier server was no longer reachable, so no stop/restart was performed).
- The CM manual sign-in flow was requested. No credentials were entered by
  automation and no successful CM case execution has yet been established.

## Follow-up: saved login but no execution

Local saved state now confirms successful live Google import of 385 cases and a
saved QA session at /home. Preparation had loaded only a spinner because the guard
blocked port-8092 backend reads/session validation. Added explicit backend-access
approval, fail-closed preplanning checks, locator grounding, and visible preparation
errors. Thirteen automated checks passed. Updated site behavior remains unverified
until the user restarts the dashboard and approves the network/session settings.
See TROUBLESHOOTING-SESSION.md. This supersedes the earlier import-unverified state.

## Local chat dashboard

- Added dashboard.py / dashboard.html and the Local QA Assistant desktop shortcut.
- Eleven automated checks passed, including a real Chromium UI/import check,
  request authentication/origin/path boundaries, historical-result isolation,
  approval invalidation, checkpoint resume and generated-test replay behavior.
  The dashboard's generated pytest file was executed against a local fixture;
  changing its reviewed result correctly caused that generated test to reject stale approval.
  JUnit results: artifacts/assistant-checks.xml.
- A real local Ollama smoke test passed after tightening the planning schema and
  shortening the prompt: local qwen3:4b-instruct proposed a heading check;
  browser-use executed the reviewed synthetic plan; Playwright replay passed.
  Evidence: artifacts/assistant-smoke/. Earlier planning attempts correctly failed
  validation rather than producing Pass. Only the disposable local fixture was tested.
- The connected Google Drive tools verified the Test Cases tab (gid 81082) and read
  A1:S12. A local first-11-case preview was saved in ignored data/. Historical Sheet
  statuses were retained as source information only, not new test results.
- Standalone authenticated Google browser CSV import is implemented but has not
  been verified with the user's Google account. Manual local sign-in is required;
  private CSV import is the fallback. No OAuth keys or credentials were copied
  from ChatGPT to the local application.
- No Sheet writes or tests against meet2.synesisit.info were performed.

- Installed environment: `pip check` passed (no broken requirements).
- Python compilation passed for qa.py, demo_run.py and demo/server.py.
- Six pytest checks passed, recorded in artifacts/setup-checks.xml. These include
  URL/method/origin restrictions, duplicate IDs, review invalidation, checkpoint
  resume, and a real Chromium generation/replay integration check against a
  disposable local HTTP fixture. A deliberately absent heading correctly produced
  Fail in that integration check. Synthetic approval existed only in pytest's
  temporary directory; no user cases were approved.
- Five synthetic demo cases ran through browser-use 0.13.14 with local
  qwen3:4b-instruct. All five navigated and met exact visible-heading assertions.
  Evidence and report: artifacts/a6384e50a4b404e0/report.html.
- Re-running demo_run.py explore skipped completed cases and retained results.
- generate created zero tests for the demo cases because human review is pending;
  replay correctly refused to run unreviewed cases. Their replay status is Not Run.
- An earlier local-model completion-loop attempt was interrupted and retained
  under DEMO-001-initial-attempt. The final navigation tool ends the case after
  an actual assertion, avoiding that loop. This is a navigation-only proof of
  concept, not a verified general-purpose UI exploration agent.
- No Google Sheet or user QA site was read, changed or tested.

## Ollama desktop issue observed during setup

The local API at 127.0.0.1:11434 responded with version 0.33.2 while the app showed
"Couldn't load integrations." Two Ollama desktop processes were present, and app
logs repeatedly reported a server startup failure. Server logs reported that
127.0.0.1:11434 was already bound. The running local server remained functional.
This identifies a port conflict; it does not prove the precise cause of the
integrations screen error. An attempted clean restart was rejected by automatic
approval review as "blocked by policy" and did not execute. No model/settings
removal or other workaround was attempted. If the desktop message persists, quit
Ollama from its tray icons and reopen it once when no tests are running.
