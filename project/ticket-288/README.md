# Ticket 288: Decompose ticket_scaffold in todo2code_tickets to reduce cyclomatic complexity

- **ID**: ticket-288
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Refactor `_ticket_scaffold` in `src/koru/autonomy/todo2code_tickets.py` to reduce its Cyclomatic Complexity from 20 down to <=5.

1. Extract `_build_ticket_inputs` for inputs dict creation and capability contract binding.
2. Extract `_build_source_context_evidence` for building artifact, files, and staleness check metadata.
3. Extract `_build_source_context` for structuring signal, dedupe_key, and diagnostic markers.
4. Keep `_ticket_scaffold` under CC <= 5.
5. Retain 100% backward compatibility and test coverage.

## Acceptance criteria

- [ ] AC-01: All tests in `tests/test_todo2code_modules.py` pass cleanly.
- [ ] AC-02: Cyclomatic complexity of `_ticket_scaffold` drops from 20 to <=5.
- [ ] AC-03: Ruff reports zero lint/formatting errors.
- [ ] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
