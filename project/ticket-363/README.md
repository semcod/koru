# Ticket 363: Stop GitHub issue-list sync before preflight refusal and report its errors (STARTER-603)

- **ID**: ticket-363
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

STARTER-603 (semcod/koru#176): `_sync_primary_planfile` ran
`planfile sync github --direction both` before the workspace preflight and
again after a stopped loop, ignored the return code and swallowed
exceptions. The issue-list run must now:

- verify the workspace (branch `main`, clean directory) before the first
  mutating sync; a refused preflight produces zero sync attempts,
- scope the sync to local tickets bound to the selected issue URLs
  (`--ticket`), never the unapproved backlog,
- skip the post-loop sync after a `stopped` result,
- treat a nonzero exit or timeout of the required sync as a run-stopping
  failure persisted in the durable result instead of reporting success.

## Acceptance criteria

- [x] AC-1: Preflight refusal, dry-run, empty list and stopped runs invoke
  zero backlog syncs.
- [x] AC-2: Sync is scoped to selected issues; nonzero exit and timeout stop
  the run with a persisted diagnostic.
- [ ] AC-3: Independent OneDev/Validator publication of the exact head.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
