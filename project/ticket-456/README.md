# Ticket 456: Ensure run.end footer is written on early exit and interruption in queue CLI

- **ID**: ticket-456
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: User authorized fixing orphaned `run.start`-only queue logs in `semcod/koru`.

## Goal and scope

1. In `src/koru/queue_cli_helpers.py`, ensure `run_queue_loop_mode` and `run_queue_single_mode` always write a `run.end` footer via `run_log.write_footer(...)` when returning early (invalid `--ticket --loop` args or `early_exit` from `queue_manager_start`) or when interrupted by an exception/signal.
2. Add regression tests in `tests/test_run_log_early_exit.py`.

## Acceptance criteria

- [x] AC-01: `run_queue_single_mode` and `run_queue_loop_mode` write a `run.end` footer to `run_log` on `queue_manager_start` early exit, invalid CLI argument early return, and unhandled interruption (`KeyboardInterrupt` / exception).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
