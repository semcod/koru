# Ticket 246: fix queued ticket execution step resolution and plan summary in execution plan

- **ID**: ticket-246
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Fix queued ticket execution step resolution and plan summary in `src/koru/autonomy/execution_plan.py`:
1. Implement `_queued_ticket_steps` in `src/koru/autonomy/execution_plan.py` resolving module-level functions (`_select_profile`, `_workflow_steps`, `_load_task_profiles`, `_fallback_profile_id`, `resolve_ticket_repo`, `_ticket_name`) so that tests and callers monkeypatching or overriding these functions receive the intended dispatch.
2. In `_select_plan_work`, format `summary` for `planfile_queue` phase to include `profile={profile}` so plan summaries accurately reflect the chosen task profile.
3. Verify that all 5 tests in `tests/test_queued_execution_steps.py` pass without regressions.

## Acceptance criteria

- [x] AC-01: Implement `_queued_ticket_steps` in `src/koru/autonomy/execution_plan.py` using module namespace.
- [x] AC-02: Format `planfile_queue` summary to include profile id.
- [x] AC-03: All tests in `tests/test_queued_execution_steps.py` and `tests/test_execution_plan.py` pass.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
