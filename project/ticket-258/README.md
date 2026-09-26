# Ticket 258: Fix post-run verify test and ruff lint failures

- **ID**: ticket-258
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Fix blockers preventing autonomous loop post-run verification (`queue.post_run_verify` in `koru.yaml`):
1. Update `tests/test_autonomy_strategy.py` assertion from `accordion_detail_to_general` to `in_flight_first` matching the default strategy set in ticket-240.
2. Fix all 27 ruff errors across `src` and `tests` (unused imports, long lines, unformatted import blocks).
3. Verify that `ruff check src tests` passes cleanly with 0 errors.
4. Verify that `pytest tests/test_autonomy_strategy.py` passes cleanly.

## Acceptance criteria

- [x] AC-01: Update `tests/test_autonomy_strategy.py` to expect `in_flight_first`.
- [x] AC-02: Fix 27 ruff errors in `src` and `tests`.
- [x] AC-03: `ruff check src tests` reports 0 errors.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
