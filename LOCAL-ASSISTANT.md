# Your local testing assistant

**Updated 29 October 2026:** follow [QUICK-START.md](QUICK-START.md).
Public Sheet/Excel import needs no Google sign-in, and Run now prepares/validates
selected read-only cases automatically. The older staged instructions below are
retained as historical notes and are superseded by the current quick start.

Double-click **Local QA Assistant** on your Desktop, or **Start Local Assistant.cmd**
in this folder. It opens a local browser dashboard. Ollama must be running; select
no integration in Ollama. No ChatGPT session or paid model API is needed.

1. Your Sheet link, Test Cases tab gid **81082**, and QA URL are prefilled.
   Click **Google sign-in / import**. Sign in yourself in the opened Google browser,
   then click **Finish Google sign-in / import** in the dashboard. The app reads a
   CSV export of that tab without changing the Sheet or its sharing permissions.
   If Google blocks the automated browser, export the tab privately to CSV and use
   **Other import options → Import a private CSV export**. Do not publish the Sheet.
2. Confirm that the target is your disposable QA environment. Click **Open QA
   browser / sign in**, sign in yourself, and manually open the Organizations page
   (or another approved read-only starting page). Click **Save QA session** in the
   dashboard. This explicitly approves that page path for navigation.
3. Select five read-only cases and type **run**. Missing plans are prepared first.
   Read each proposed plan against ALL original steps and expected results, then
   **Approve read-only plan** only if the checks fully cover them. Unverifiable
   criteria remain Blocked; do not approve a weaker expectation to make it pass.
4. Type **run** again. Observe live progress, local screenshots, exact checks and
   results. Type **pause** to stop after the current case. **Resume** retains all
   completed results and moves to pending cases. Work stays in small batches.
5. Review a successful case's actual evidence. **Approve successful flow / generate
   test** creates a Playwright pytest file. **Replay reviewed** runs those generated
   tests through pytest and records screenshots, traces, JUnit XML and results.

You can ask ordinary questions in the chat, paste the Sheet link, or request a
small batch in plain language. Explicit commands and workspace buttons are the
most predictable controls. Chat uses the local qwen3:4b-instruct model. Intent
routing cannot execute arbitrary shell commands or use a cloud model.

## Scope and cost

The current tools support inspecting visible text/accessibility roles, counting
visible elements, checking nonnegative numeric display, reloading, and following
explicitly approved read-only navigation paths/links. Browser-use executes only a
human-reviewed plan, and Playwright performs actual assertions. Model preparation
uses the current DOM snapshot; it does not discover every possible UI interaction.
Typing/filter forms, arbitrary buttons, create/edit/delete/upload/invite/email/
payment actions are unavailable. Backend/data reconciliation and ambiguous steps
are Blocked unless the supported checks can verify the entire expected result.

The model's interpretation still requires review, especially on a 4B local model.
Pass means the reviewed plan actually ran and its assertions passed; it does not
certify criteria omitted from a wrongly approved plan. Prior Sheet Status/Actual
Result cells are displayed only as historical information and never imported as
new Pass results. Suggested rewrites remain proposals and do not edit the source.

No Sheet write-back is enabled. First-batch review and explicit approval are
required before adding a controlled update of only Status and Actual Result.
The Google sign-in export path must be verified with your account; it has not
been claimed to work merely because this chat's connector can read the Sheet.

All inference runs locally at 127.0.0.1:11434. There are no paid APIs or token quotas;
CPU inference can take several minutes per plan on this PC. Requests are bounded,
plans are cached, each case uses its own context, and full chat history is never
sent with every case. The website and Google access still require internet.

## Privacy and recovery

The dashboard listens only on 127.0.0.1:8766 and requires a random per-launch token.
It rejects foreign-origin requests. Session state, imported data and chat history
are in ignored `.private/` / `data/`; evidence is in ignored `artifacts/assistant/`.
Browser cookies are local session credentials: don't share or commit these folders.
No password, API key, Google client secret, or payment detail is needed in chat.

Use **Preserve evidence and retry case** for a deliberate retry; it archives the
previous attempt, invalidates approvals, and requires a new reviewed plan. A
shutdown or interruption leaves unfinished cases resumable. Relaunching the
desktop shortcut opens an already-running assistant instead of starting a second.
Use **Stop local assistant** to shut down its background server when idle. Closing
the browser tab alone leaves the assistant running so it can be reopened quickly.

Original command-line demo and its reports remain available separately. The saved
Sheet preview contains only the first 11 cases read on 28 October 2026, not the full
test suite. Import the live Sheet to read all current cases. The local QA site has
not been tested until you sign in and approve a batch.
