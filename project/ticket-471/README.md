# Ticket 471: fix(queue): redirect ruff and mypy caches in verification sandbox and clean up empty scratch dirs

- **ID**: ticket-471
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience and prevention repairs in `semcod/koru` to fix verification sandbox cache redirection and staging worktree cleanup.

## Goal and scope

Redirect `RUFF_CACHE_DIR` and `MYPY_CACHE_DIR` into the writable `scratch/cache` directory inside the bubblewrap verification sandbox (`src/koru/queue/verification_sandbox.py`), prune empty `.subactor/cache/koru-verification` directories after verification completes, and reverse the staged unified diff when `VERIFY_BASELINE_FAILED` occurs (`src/koru/queue/transaction/staging.py`) so failed baseline runs do not leak dirty detached-HEAD worktrees.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_queue_verification_sandbox.py tests/test_queue_workspace_retention.py tests/test_planfile_queue.py -q` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
