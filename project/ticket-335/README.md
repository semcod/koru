# Ticket 335: Fix test queue concurrency mock protocol instantiation

- **ID**: ticket-335
- **Owner**: agent:koru
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

Fix `test_next_tickets_or_result_fallback` in `tests/test_queue_concurrency.py`:
`CommandResult` is a `typing.Protocol` and cannot be instantiated directly with `CommandResult(0, ...)`. Replace with a mock object conforming to the protocol interface (`returncode`, `stdout`, `stderr`).

## Acceptance criteria

- [x] AC-01: `tests/test_queue_concurrency.py` passes all unit tests without `TypeError`.
- [x] AC-02: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
