# Ticket 303: Decompose _promote_todo2code_ticket in code change autonomy to reduce cyclomatic complexity

- **ID**: ticket-303
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Refactor `_promote_todo2code_ticket` (CC=19) in `src/koru/autonomy/code_change_autonomy.py` to reduce its Cyclomatic Complexity down to <=5.

1. Extract `_is_promotable_ticket_status`.
2. Extract `_is_todo2code_named_or_sourced`.
3. Extract `_is_already_automatic_llm`.
4. Extract `_filter_useful_code_paths`.
5. Retain 100% backward compatibility and test coverage.

## Acceptance criteria

- [x] AC-01: All tests in `tests/test_code_change_autonomy.py` pass cleanly.
- [x] AC-02: Cyclomatic complexity of `_promote_todo2code_ticket` drops to <=5.
- [x] AC-03: Ruff reports zero lint/formatting errors.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
