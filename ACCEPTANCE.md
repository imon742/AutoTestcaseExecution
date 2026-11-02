# Acceptance checklist

Run these checks only against the built-in loopback fixture until a separate
real-environment approval is recorded.

## Security checks

- [ ] No real hostnames, workbook identifiers, email addresses, or local paths
      are present in tracked source files.
- [ ] No secret appears in chat history, reports, logs, screenshots, traces, or
      tracked source files.
- [ ] Read-only cases block mutating requests and unsafe links.
- [ ] Side-effect cases are bound to a named fixture and its origin.
- [ ] A failed Sheet sync retries only the sync, never browser actions.

## Local fixture milestones

- [ ] M1: stop/restart a three-case read-only run; each case has an action log,
      screenshot, verdict, and rationale.
- [ ] M2: export result copy, interrupt, then resume without duplicate actions.
- [ ] M3: compare local results to an approved baseline; discrepancies are
      `Blocked` or `NeedsReview`, not artificial Passes.
- [ ] M4: generate replay only from a reviewed passing flow and verify it without
      model inference.

Do not mark a real-system milestone complete based on synthetic fixture results.
