# Ticket 221: Split god module queue context

- **ID**: ticket-221
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address the code2llm god-module report for `src/koru/queue/context.py`
(581 lines, 4 classes, 14 mutations, max CC=19) — planfile ticket PLF-039.

Split the module by responsibility, moving every function verbatim:

- `src/koru/queue/context_exclusions.py` — the non-negotiable security
  exclusion policy (names/suffixes/globs tables + `_is_excluded`).
- `src/koru/queue/context_files.py` — request-driven file selection
  (explicit lists, globs, auto-include set), safe bounded reads and the
  compact file tree.
- `src/koru/queue/context_slicing.py` — focused AST/line-window slicing
  of oversized files with target symbol/line resolution.

`src/koru/queue/context.py` keeps only the assembly pipeline
(`ContextResult`, `_context_file_sections`, `_truncate_context_text`,
`build_project_context`, `DEFAULT_MAX_CONTEXT_CHARS`) and re-exports the
moved private names with redundant aliases so every pre-split import —
including the test-facing `_is_excluded` and
`_resolve_target_symbol_and_line` — keeps working unchanged
(the `koru.scan` → `koru.scan_todo` facade pattern).

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `src/koru/queue/context.py` is reduced to the assembly facade; the three new responsibility modules hold the moved behavior.
- [x] AC-03: Behavior preserved — `tests/test_llm_context.py` passes unchanged (51 passed; the `test_cursor_llm` no-default-cap failure is pre-existing on main and untouched).
- [x] AC-04: Public import surface stable — every public and private pre-split name still imports from `koru.queue.context`; `src/koru/queue/runner.py` unmodified.
- [x] AC-05: `tests/test_queue_context_modules.py` (focused tests at the new module homes + facade stability pins) passes and `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-039 planfile handoff instructs
to split the module, keep public imports stable, add focused tests, run
local regression gates and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
