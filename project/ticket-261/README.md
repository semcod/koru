# Ticket 261: Decompose resolve_target_symbol_and_line in context_slicing to reduce cyclomatic complexity

- **ID**: ticket-261
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Refactor `_resolve_target_symbol_and_line` in `src/koru/queue/context_slicing.py` to reduce its Cyclomatic Complexity from 19 down to <=5.

1. Extract `_resolve_target_from_request_meta` to check direct request fields `target_symbol` and `target_line`.
2. Extract `_extract_line_from_corpus` to match `filename:line` patterns in text corpus.
3. Extract `_extract_symbol_from_corpus` to match code smell / method patterns in text corpus.
4. Keep `_resolve_target_symbol_and_line` compact, readable, and under CC <= 5.
5. Retain 100% backward compatibility.

## Acceptance criteria

- [ ] AC-01: All tests in `tests/test_queue_context_modules.py` pass cleanly.
- [ ] AC-02: Cyclomatic complexity of `_resolve_target_symbol_and_line` drops from 19 to <=5.
- [ ] AC-03: Ruff reports zero lint/formatting errors.
- [ ] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
