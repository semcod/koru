# Ticket 245: decompose god module execution plan by extracting task profile matcher and step generators

- **ID**: ticket-245
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Decompose the oversized `src/koru/autonomy/execution_plan.py` (715 lines) into cohesive modules:
1. `src/koru/autonomy/execution_plan_profiles.py`: Task profile loading and matching (`_load_task_profiles`, `_ticket_labels`, `_ticket_signal`, `_ticket_name`, `_profile_labels_match`, `_ticket_matches_profile`, `_profile_matches`, `_profile_order`, `_fallback_profile_id`, `_select_profile`).
2. `src/koru/autonomy/execution_plan_steps.py`: Execution step builders and runner (`_format_command`, `_workflow_steps`, `_queued_ticket_steps`, `_pr_steps`, `_worktree_steps`, `_discovery_steps`, `run_auto_steps`).
3. `src/koru/autonomy/execution_plan.py`: Plan data models (`ExecutionStep`, `ExecutionPlan`), ticket repository resolution, signals collection, and compilation orchestration (`compile_execution_plan`) with explicit re-exports of all extracted symbols to guarantee 100% backward compatibility.

## Acceptance criteria

- [x] AC-01: Extract task profile loading and matching to `src/koru/autonomy/execution_plan_profiles.py`.
- [x] AC-02: Extract workflow step builders and runner to `src/koru/autonomy/execution_plan_steps.py`.
- [x] AC-03: `src/koru/autonomy/execution_plan.py` re-exports all extracted symbols with `# noqa: F401`.
- [x] AC-04: All existing tests in `tests/test_execution_plan.py`, `tests/test_execution_profile_matching.py`, `tests/test_queued_execution_steps.py`, and `tests/test_task_execution_strategies.py` pass without regression.
- [x] AC-05: Unit tests in `tests/test_execution_plan_profiles.py` verify extracted functionality.
- [x] AC-06: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
