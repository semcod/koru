# Ticket 287: enable-auto-runnable-finish-steps-and-infer-ticket-id-for-autonomous-merge

- **ID**: ticket-287
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Enable auto-runnable execution for `finish_pr`, `finish_worktree`, and profile `publish` steps under green test verification, closing the autonomy loop so Koru does not stall waiting for manual intervention. Additionally, make `--ticket` optional in `koru work finish` by inferring the ticket id from the active work branch or existing PR.

## Acceptance criteria

- [x] AC-01: `finish_pr` and `finish_worktree` steps in `src/koru/autonomy/execution_plan_steps.py` are `auto_runnable=True`.
- [x] AC-02: `publish` step in `src/koru/autonomy/task_profiles.yaml` is `auto: true` for automated workflow execution.
- [x] AC-03: `cli_work.py` allows `--ticket` to be omitted when `--pr` is provided or active branch encodes ticket ID.
- [x] AC-04: `finish_work` in `src/koru/work/lifecycle.py` infers ticket ID if omitted or empty.
- [x] AC-05: Unit test suites pass with 100% clean assertions.
- [x] AC-06: `./project/governance-check.sh` passes with 0 errors and 0 warnings (GOV-PASS).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
