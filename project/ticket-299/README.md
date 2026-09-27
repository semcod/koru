# Ticket 299: Decompose _normalize_step in runners to reduce cyclomatic complexity

- **ID**: ticket-299
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Refactor `_normalize_step` (CC=23) in `src/koru/queue/runners.py` to reduce its Cyclomatic Complexity down to <=5.

1. Extract `_normalize_step_id`.
2. Extract `_normalize_step_name`.
3. Extract `_normalize_step_process`.
4. Extract `_normalize_step_deps`.
5. Extract `_normalize_step_params`.
6. Retain 100% backward compatibility and test coverage.

## Acceptance criteria

- [x] AC-01: All tests in `tests/test_queue_runners.py` pass cleanly.
- [x] AC-02: Cyclomatic complexity of `_normalize_step` drops to <=5.
- [x] AC-03: Ruff reports zero lint/formatting errors.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
