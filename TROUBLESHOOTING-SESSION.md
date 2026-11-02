# Logged in, but tests did not run — 28 October 2026

## Observed from local saved state

- Live Google browser import succeeded: 385 cases loaded from Test Cases.
- QA environment confirmation was saved, as was a local QA browser session.
- The saved starting path was `/home`, not a confirmed Organizations directory.
- SA_RTC_008_001 was selected.
- Preparation blocked requests to the site's same-host backend on port 8092,
  including background session validation and user/organization reads.
- The preparation screenshot showed a loading spinner.
- The small model nevertheless proposed Organization-page locators that were
  not grounded in that screenshot. The resulting plan remained unapproved and
  no successful case execution was established.

## Fixes saved

- Explicit, opt-in QA backend settings: GET/HEAD/OPTIONS reads on the same host at
  port 8092 and only XHR/fetch POST session validation at
  `/services/dashboard/api/authenticate`.
- Other mutation methods/paths and navigation to unapproved origins remain blocked.
- Known analytics/font/cookie/IP-geolocation hosts remain blocked. With backend
  access explicitly approved, those blocked optional requests do not themselves
  invalidate these reviewed UI checks. Requests and evidence remain recorded.
- Wait briefly for SPA content before taking the planning snapshot.
- Stop before invoking the model when required requests were blocked or the page
  is blank/loading. Do not generate a plan from that incomplete page.
- Reject proposed current-page locators that are absent or ambiguous.
- Display preparation problems as Blocked without claiming a test ran.
- A policy-version change separates the old invalid plans/results from fresh work;
  older artifacts and saved login remain preserved.
- Thirteen automated checks passed, including backend read/auth exceptions,
  continued mutation blocking, and visible preparation-error handling.

## Load the fixes

Automatic approval review rejected the attempted idle-dashboard restart as
"blocked by policy". It did not execute; no alternate restart was attempted.

1. Refresh the dashboard, click **Stop local assistant**, and reopen the Desktop
   **Local QA Assistant** shortcut.
2. Review **Backend access · explicit approval**, approve the described QA reads
   and session validation if appropriate, then click **Save settings**.
3. Click **Open QA browser / sign in**, navigate manually to the actual read-only
   Organizations directory, and click **Save QA session**. A saved `/home` login
   alone does not establish that the Organization checks can run there.
4. Prepare the selected case again, review its observed-page plan, approve it only
   if it covers the original requirements, then run it.

No QA actions were started during this diagnosis. The updated network integration
has not yet been validated against the user's site; the passing checks used local
fixtures/simulated requests. No Sheet cells were modified.
