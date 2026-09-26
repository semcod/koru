# Antigravity plan

## Problem

`compile_execution_plan` and its private orchestrator `_select_plan_work` in
`src/koru/autonomy/execution_plan.py` had a combined cyclomatic complexity of
CC=12 (CC=3 + CC=9) after the ticket-245 module decomposition. The remaining
complexity lives in `_select_plan_work`, which mixed strategy dispatch with
three inline selection handlers.

## Approach

1. Extract three focused selectors from `_select_plan_work`:
   - `_select_pending_pr` — handles the `pending_prs` target.
   - `_select_pending_worktree` — handles the `pending_worktrees` target.
   - `_select_issue_or_discovery` — handles the `issues` target, including the
     fallback to discovery when no tickets are open.
2. Replace the inline `if target == ...` chains with a selector dispatch map
   so the loop body is strategy-agnostic.
3. Add unit tests for each new selector function.
4. Verify CC of `_select_plan_work` drops from 9 → 4.
