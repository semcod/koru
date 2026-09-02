# Ticket 046: Koru CI project flag, publication preflight, scan staleness

- **ID**: ticket-046
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Acceptance criteria

- [x] AC-01: `koru ci run --project .` works (project flag after subcommand).
- [x] AC-02: `dispatch_validator_merge` fails fast when PR is CONFLICTING/UNKNOWN.
- [x] AC-03: Ticket hygiene archives open tickets whose declared paths are missing.
- [x] AC-04: Non-interactive queue skips operator human tickets instead of blocking.
