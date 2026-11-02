# Local QA Assistant — current workflow (29 October 2026)

**Correct target:** Organization cases use **https://meet2.synesisit.info:85/**
(Centralized Management). The meeting dashboard at port 443 `/home` is a different
application view. The source tab is **Test Cases**, gid **81082**. The application
has been configured with the corrected target and 385 anonymously imported cases.

## Load this update once

Refresh the old dashboard, choose **Stop local assistant**, then reopen the Desktop
shortcut. The chat footer must show **Version 2026-10-29.3**. Old processes keep old
Python code until restarted. Your imported cases/session files remain preserved.

## 1. Import without Google sign-in

- Paste a publicly accessible Google Sheet link and enter its tab name (for your
  Sheet: **Test Cases**). Click **Import public Sheet · no sign-in**.
- Or select a local **.xlsx** / **CSV** file. Excel imports the requested tab,
  finds the headings within the first 30 rows, and reads values without executing
  formulas/macros. Legacy .xls is not supported; save it as .xlsx first.
- Import is anonymous: no Google account, cookies, API key or credentials are used.
  A non-public link returns an access error rather than requesting sign-in.
- Your supplied Sheet was verified to return **385 cases anonymously** on 29 October.
- Historical Sheet results remain historical, never new test passes.

## 2. Sign in only to your QA website

Confirm the disposable QA environment and use **Open QA browser / sign in**.
The sign-in browser starts at **https://meet2.synesisit.info/**. Sign in yourself,
click **Admin Settings**, and wait for CM on port 85 to open successfully. Keep
both tabs open if a new one appears, then click **Save QA session** in the dashboard.
Tests repeat the portal → Admin Settings handoff and retain the popup/opener;
they no longer start by visiting port 85 directly. No password is entered into chat.
Session storage for BOTH origins is saved locally in addition to cookies/local storage/IndexedDB.
Older sessions that omitted sessionStorage may need one fresh manual sign-in.

The known meet2 QA backend supports background reads and the exact session-validation
POST on port 8092. A previously explicit denial remains respected. Business write
requests remain blocked. Other APIs/unsupported read methods can still block a case.

## 3. Run the selected read-only cases

Select up to five cases and click **Run / resume selected**, or type **run**.
The runner now automatically prepares, grounds and validates a read-only plan,
then executes it. **Manual plan approval is no longer required for these selected
read-only executions.** Preview plan is optional.

An explicitly specified left-navigation link can be followed when the actual page
contains one unique visible same-origin link with that accessible name. Routes are
recorded from the observed link, not invented. Arbitrary buttons/forms remain unsupported.

Pass/Fail cases are completed and skipped on resume. Blocked cases can be retried
after correcting the cause. They are not passed or counted as completed successes.
Inspect Actual Result, screenshots, trace and blocked requests for the exact reason.

## 4. Review successful flows before conversion

Review the actual evidence and full expected-result coverage, then choose
**Approve successful flow / generate test**. **Replay reviewed** executes the
generated Playwright pytest file. This human review gate remains mandatory.

## Limits

This remains a read-only implementation: no data creation/edit/deletion, uploads,
email, payments or Sheet writes. Such integrations are not made available merely
by clicking Run. Cases requiring them, unknown navigation, or backend reconciliation
must be Blocked. A 4B local model can still propose incomplete plans; mechanical
grounding and assertions prevent absent locators from being accepted as observed.
Review successful results before treating them as final business coverage.

All model inference is local. Tests against the disposable demo fixtures do not
establish that every case on your QA website works. New site validation outcomes
must be read from actual evidence rather than inferred from local test counts.
