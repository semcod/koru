# Ticket 351: decompose compile execution plan and extract selection module

- **ID**: ticket-351
- **Owner**: agent:Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION ("wykonaj i przetestuj, scal, popraw")

## Goal and scope

Decompose `compile_execution_plan` in `src/koru/autonomy/execution_plan.py` to reduce cyclomatic complexity and improve modularity:
1. Extract plan selection, signal collection, and execution plan assembly helper methods (`_collect_plan_signals`, `_select_plan_work`, `_select_pending_pr`, `_select_pending_worktree`, `_select_issue_or_discovery`, `_discovery_selection`, `_build_execution_plan`) into `src/koru/autonomy/execution_plan_selection.py`.
2. Keep public interface backward-compatible in `src/koru/autonomy/execution_plan.py`, re-exporting internal helpers used by existing test suites or dependents.
3. Ensure all hermetic unit tests in `tests/test_execution_plan*.py` pass.

## Acceptance criteria

- [x] AC-01: `compile_execution_plan` cyclomatic complexity is reduced below threshold.
- [x] AC-02: `src/koru/autonomy/execution_plan_selection.py` cleanly encapsulates signal collection and work selection.
- [x] AC-03: Backward compatibility preserved for test mocks and callers.
- [x] AC-04: Unit tests in `tests/test_execution_plan*.py` pass green.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
