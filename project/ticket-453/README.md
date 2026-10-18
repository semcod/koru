# Ticket 453: fix(queue): only retry VERIFY_BASELINE_FAILED on incomplete multi-file patches

- **ID**: ticket-453
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: user requests autonomous execution to prevent single-file VERIFY_BASELINE_FAILED outcomes from triggering wasted LLM verify retries.

## Goal and scope

1. In `src/koru/queue/patch_retry.py` (`_AttemptState.advance`), only treat `VERIFY_BASELINE_FAILED` as retryable via `verify_remaining` when the ticket has multiple declared target files (`len(declared) > 1`) and the previous diff left at least one declared target file untouched.
2. Add regression test in `tests/test_queue_verification_sandbox.py`.

## Acceptance criteria

- [x] AC-01: Single-file or already-complete `VERIFY_BASELINE_FAILED` outcomes terminate immediately in `_AttemptState.advance` without spending a verify retry, even when pytest elapsed timings differ between `Before:` and `After:`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
