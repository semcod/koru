# Ticket 302: integrate-taskand-operational-profile-and-twinerd-sandbox-in-koru

- **ID**: ticket-302
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Integrate operational task routing and zero-copy digital twin sandboxing into Koru:
1. Add `taskand_operational` task profile in `src/koru/autonomy/task_profiles.yaml` matching `operational`, `sandbox`, `taskand`, and `twinerd` labels/signals.
2. Update `profile_order` in `src/koru/autonomy/execution_plan_profiles.py` to prioritize `taskand_operational` before fallback profiles.
3. Add Twinerd digital twin sandbox integration (`create_twinerd_sandbox`, `_find_twinerd_cli`) in `src/koru/queue/runners.py` enabling fast, zero-copy CoW execution for tickets requesting sandboxed runs.
4. Add unit test suites in `tests/test_execution_plan_profiles.py` and `tests/test_taskand_operational_profile.py`.

## Acceptance criteria

- [x] AC-01: `task_profiles.yaml` and `execution_plan_profiles.py` define and route `taskand_operational`.
- [x] AC-02: `src/koru/queue/runners.py` provides `create_twinerd_sandbox` and sandboxed execution path with CC <= 6.
- [x] AC-03: `tests/test_execution_plan_profiles.py` and `tests/test_taskand_operational_profile.py` pass 100%.
- [x] AC-04: `./project/governance-check.sh` reports GOV-PASS with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
