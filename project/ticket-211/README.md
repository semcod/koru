# Ticket 211: Decompose god function context file sections

- **ID**: ticket-211
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: `God Function: _context_file_sections` in
`src/koru/queue/context.py:431` (PLF-029).

Extract the oversized-file slicing block into `_focused_file_slice` returning a
`_FocusedSlice` NamedTuple, and make `_resolve_target_symbol_and_line`,
`_extract_python_symbol_slice` and `_extract_line_slice` return NamedTuples
(`_TargetRef`, `_CodeSlice`) so callers use attribute access instead of tuple
unpacking. Preserve identical slicing decisions, header notes and section
formatting.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-029 queue handoff).
- [x] AC-02: `_context_file_sections` metrics fall under the god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6); new helper stays under too.
- [x] AC-03: `pytest -q tests/test_llm_context.py tests/test_cursor_llm.py` passes unchanged plus a new regression test for the `target_line` fallback path.
- [x] AC-04: code2llm mutation analysis of the changed file reports no function above the god-function mutation threshold introduced by this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
