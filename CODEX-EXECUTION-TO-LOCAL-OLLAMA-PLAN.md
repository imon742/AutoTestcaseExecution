# Local QA Agent implementation plan

This repository contains no customer hostnames, workbook identifiers, email
addresses, browser session URLs, or local user paths. Configure those only in
ignored local configuration through the application UI.

The intended flow is:

1. Import public CSV or a local spreadsheet.
2. Open one visible Playwright browser and sign in manually.
3. Run a bounded case through fixed host-written actions.
4. Capture evidence and determine a deterministic verdict.
5. Commit the case locally, then optionally sync only approved result fields.
6. Generate Playwright replay only from reviewed, verified passing cases.

The model is a constrained local planner. It never receives secrets, executes
code, controls the browser directly, or creates a pass result by itself.

For external environment-specific notes, keep a separate local, ignored handoff
document outside this repository.
