# Ticket 473: fix(queue): reverse unified diff after non-branch staging verification so staging worktrees are removed

- **ID**: ticket-473
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Scope

- Reverse the applied unified diff in `staged` after non-branch verification succeeds in `src/koru/queue/transaction/staging.py` so `staging_worktree` removes the temporary worktree instead of preserving a dirty detached-HEAD checkout.
- Add unit test in `tests/test_queue_workspace_retention.py`.

## Acceptance

- [x] AC-01: `pytest -q tests/test_queue_workspace_retention.py tests/test_queue_transaction_phases.py` and `./project/governance-check.sh` pass.
