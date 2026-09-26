# Ticket 248: Address code smell: God Function: compile_execution_plan

- **ID**: ticket-248
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell in the `compile_execution_plan` execution planning pipeline in `src/koru/autonomy/execution_plan.py`:
1. Extract `_select_pending_pr`, `_select_pending_worktree`, and `_select_issue_or_discovery` from `_select_plan_work` into dedicated helper functions.
2. Reduce the cyclomatic complexity of `_select_plan_work` from 9 to 4 using a strategy-agnostic selector dispatch map.
3. Export the new helper functions in `__all__` for compatibility and provide full test coverage.
4. Verify that all 32 unit tests pass and governance gates pass with 0 errors.

## Acceptance criteria

- [x] AC-01: Extract `_select_pending_pr`, `_select_pending_worktree`, and `_select_issue_or_discovery` from `_select_plan_work`.
- [x] AC-02: Cyclomatic complexity of `_select_plan_work` reduced to <= 4.
- [x] AC-03: All tests in `tests/test_execution_plan.py`, `tests/test_execution_plan_profiles.py`, and `tests/test_task_execution_strategies.py` pass.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
