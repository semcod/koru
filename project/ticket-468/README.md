# Ticket 468: fix(queue): bind patch promotion branch to governed ticket pattern and pass no-verify on run branches

- **ID**: ticket-468
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience and prevention repairs in `semcod/koru` observed while delegating tickets through `willman` / `willops`.

## Goal and scope

Bind patch promotion branch to governed ticket pattern (`ticket/{tnum}-run-{plan.run_id}`) and pass `--no-verify` on intermediate worktree run branches when `KORU_GOVERNED_WORKTREE_OK` is set, eliminating `GOV-AGENT-HOST-001` pre-commit rejections during patch promotion.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_planfile_queue.py -k 'test_commit_worktree or test_promotion'` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
