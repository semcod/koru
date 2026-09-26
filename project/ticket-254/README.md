# Ticket 254: reduce cyclomatic complexity in task strategies by decomposing pending worktree and pr finders

- **ID**: ticket-254
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Reduce cyclomatic complexity in `src/koru/autonomy/task_strategies.py`:
1. `find_pending_worktrees` (CC=24 -> <=6): Decompose into porcelain parser (`_parse_worktrees_porcelain`), runner-filter helper (`_is_runner_worktree`), and single worktree state inspector (`_inspect_worktree_state`).
2. `find_pending_prs` (CC=18 -> <=5): Decompose into item mapper (`_parse_pending_pr_item`) and check status roll-up parser (`_parse_check_statuses`).
3. Ensure 100% backward compatibility of all exports and verify that all tests in `tests/test_task_execution_strategies.py` pass.

## Acceptance criteria

- [x] AC-01: Decompose `find_pending_worktrees` and `find_pending_prs` in `src/koru/autonomy/task_strategies.py` so CC <= 6.
- [x] AC-02: All existing tests in `tests/test_task_execution_strategies.py` pass without modification.
- [x] AC-03: `ruff check` and `ruff format` report 0 findings.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
