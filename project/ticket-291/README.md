# Ticket 291: Decompose instance_status and session_ticket in opencode_terminals to reduce cyclomatic complexity

- **ID**: ticket-291
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Refactor `instance_status` (CC=22) and `_session_ticket` (CC=18) in `src/koruapi/opencode_terminals.py` to reduce their Cyclomatic Complexity down to <=6.

1. Extract `_find_ticket_in_session_messages` from `_session_ticket`.
2. Extract `_format_session_row` from `instance_status`.
3. Extract `_scan_active_ticket` from `instance_status`.
4. Extract `_extract_instance_models` from `instance_status`.
5. Retain 100% backward compatibility and test coverage.

## Acceptance criteria

- [x] AC-01: All tests in `tests/test_dashboard_terminals.py` pass cleanly.
- [x] AC-02: Cyclomatic complexity of `instance_status` and `_session_ticket` drops to <=6.
- [x] AC-03: Ruff reports zero lint/formatting errors.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
