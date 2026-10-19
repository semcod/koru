# Ticket 462: Stamp expect_files_changed on file-scoped scan tickets and allow autopilot on waiting llm-ready tickets when idle-only is set

- **ID**: ticket-462
- **Owner**: agent:agy
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

1. When `koru.scan_ticket_emission.create_ticket` creates a ticket from a scan suggestion with non-empty `suggestion.files`, include `"inputs": {"expect_files_changed": True, "patch_mode": True}` in the scaffold so `llm` queue execution satisfies `_llm_completion_scope_gap` regardless of whether the suggestion carries a `refactor` label (e.g. `code2llm` `code-smell` or `vallm` `validation` tickets).
2. In `koru.autonomy.cycle.cycle_skip_conditions._check_autopilot_skip_conditions`, when `autopilot_on_idle_only` is enabled and `queue_result.last_status != "idle"`, allow autopilot to proceed when `_is_waiting_llm_ready_ticket(queue_result=queue_result, project=project)` is true so `waiting_input` tickets tagged `llm-ready` do not deadlock behind `idle_only`.

## Acceptance criteria

- [x] AC-01: File-scoped scan tickets created via `create_nl_task` carry `inputs.expect_files_changed=True` and `inputs.patch_mode=True`.
- [x] AC-02: `_check_autopilot_skip_conditions` with `autopilot_on_idle_only=True` does not skip `waiting_input` tickets that carry the `llm-ready` label.
- [x] AC-03: Unit tests in `tests/test_autonomous.py` and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
