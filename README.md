# Local QA Agent

Local QA Agent is a Windows-first, local-only test orchestration application.
It imports a public Google Sheet CSV or local CSV/XLSX, lets the user sign in in
one visible Playwright browser profile, records case-level evidence/checkpoints,
and exports factual results. Ollama is used only on `127.0.0.1` to interpret
bounded case text; it never receives credentials and it never declares a pass
without deterministic page evidence.

## Safety model

- `local_qa/` is the only active implementation. Earlier experiments are not
  part of this repository.
- A browser context has one owner: Playwright. Browser-use is optional later and
  must attach to that same context.
- Origins are default-deny. Read-only navigation needs an approved path or a
  link from a visible navigation landmark. Read-only cases abort non-GET/HEAD/
  OPTIONS requests, except explicitly configured session-auth endpoints.
- Every side-effect case requires a case ID, an allowed category, and a fixture
  ID bound to the current origin. Failed/interrupting mutations are `NeedsReview`
  and are never automatically retried.
- Passwords, cookies, tokens, browser storage, OAuth files, artifacts and local
  imports are ignored by Git. Do not add them to this repository.
- Public Google Sheets are import-only. Google write-back is disabled by default
  and must use locally stored OAuth only after a workbook copy has been proven.

## Run the local interface

Use the existing desktop launcher, or from PowerShell:

```powershell
Set-Location -LiteralPath 'C:\path\to\browser-testing-poc'
.\.venv\Scripts\python.exe -m local_qa.app
```

Choose an installed Ollama model, import a local test file or public Sheet, and
use **Open sign-in browser**. Enter credentials only in that visible browser or
the local OS-vault form—not in chat, Sheets, configuration, or source code.

## Development checks

```powershell
Set-Location -LiteralPath 'C:\path\to\browser-testing-poc'
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite uses the built-in loopback fixture. It does not open a real QA
site, a mailbox, or a Google Sheet.

## Repository hygiene

Before publishing or sharing the repository, run the privacy scan documented in
`ACCEPTANCE.md`. Removing a secret in a new commit does not remove it from Git
history; recreate the repository or rewrite history before sharing if sensitive
material was previously committed.
