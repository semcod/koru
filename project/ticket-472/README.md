# Ticket 472: fix(queue): include blocked in scan history dedupe, set GIT_CEILING_DIRECTORIES, and clean staging worktrees

- **ID**: ticket-472
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Scope

- Include `"blocked"` and `"failed"` in `existing_scan_history_keys` in `src/koru/scan_dedupe_policy.py` so archived blocked/failed tickets for the same `artifact.sha256` are not endlessly cloned by `koru scan --apply`.
- Add `"GIT_CEILING_DIRECTORIES": str(scratch)` in `src/koru/queue/verification_sandbox.py` so tests in `TMPDIR` never walk up into `<project>/.git`.
- Ignore `.koru/` observability files in `_remove_unchanged_staging` (`src/koru/queue/workspace.py`) and revert the staged unified diff after non-branch verification passes (`src/koru/queue/transaction/staging.py`) so verified staging worktrees are cleanly removed.

## Acceptance

- [x] AC-01: `pytest -q tests/test_scan_split.py tests/test_queue_workspace_retention.py tests/test_queue_verification_sandbox.py` and `./project/governance-check.sh` pass.
