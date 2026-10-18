# Ticket 452: fix(queue): skip verify retries on baseline failure and prepend project venv in sandbox

- **ID**: ticket-452
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: user requests autonomous execution to diagnose and fix Koru verification sandbox PATH resolution and skip wasted verify retries on unrecoverable baseline failures.

## Goal and scope

1. Prepend project `.venv/bin`, `venv/bin`, and `node_modules/.bin` (plus the parent primary checkout's equivalents when running inside `.worktrees/<slug>`) to `PATH` inside `src/koru/queue/verification_sandbox.py`, and omit `-o cache_dir=...` from `PYTEST_ADDOPTS` when `no:cacheprovider` is present in the verification command.
2. Skip verification retries in `src/koru/queue/patch_retry.py` (`_is_verify_failure`) when `VERIFY_BASELINE_FAILED` is caused by unrecoverable baseline/environment errors (`no tests ran`, `ModuleNotFoundError`, `No module named `, `command not found`, `verification_sandbox_unavailable`) or identical `Before:` / `After:` output.
3. Add regression tests in `tests/test_queue_verification_sandbox.py`.

## Acceptance criteria

- [x] AC-01: `verification_sandbox.py` prepends project and parent worktree `.venv/bin` / `node_modules/.bin` to `PATH` and avoids setting `cache_dir` when `no:cacheprovider` is passed; `patch_retry.py` skips retries on unrecoverable `VERIFY_BASELINE_FAILED` outcomes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
