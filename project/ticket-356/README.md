# Ticket 356: Fix executed ticket status for mock queue loop result

- **ID**: ticket-356
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

Use `getattr` with safe fallback when reading `completed`, `failed`, `waiting`, and `last_ticket_id` in `_executed_ticket_status` inside `src/koru/autonomy/cycle/cycle_post_drive.py`. This ensures test mocks (such as `SimpleNamespace` in `test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message`) that do not declare all fields of `QueueLoopResult` do not raise `AttributeError`.

## Acceptance criteria

- [ ] AC-01: `src/koru/autonomy/cycle/cycle_post_drive.py` safely inspects `completed`, `failed`, `waiting`, and `last_ticket_id` on `queue_result`.
- [ ] AC-02: `test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message` passes.
- [ ] AC-03: `ruff check src tests` passes cleanly.

## Authorization

- Session execution authorization: user requested continuation of pilot test and autonomous delivery.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
