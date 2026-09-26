# Ticket 231: reduce-cyclomatic-complexity-in-extract-python-comments

- **ID**: ticket-231
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

code2llm reports `packages.koru-scan-todo.src.extract_python_comments` at
`packages/koru-scan-todo/src/lib.rs:86` with cyclomatic complexity 38 (limit
15). Decompose the five-state comment/string lexer loop into per-state helper
functions (`lex_normal`, `skip_quoted_string`, `skip_triple_quoted_string`,
`is_triple_quote`, `comment_line_end`, `push_comment`, `quote_byte`) so the
public function only drives the state machine. The public API and every
extracted comment stay byte-identical. Planfile ticket PLF-039. Base:
origin/main `ae342592`.

SESSION_EXECUTION_AUTHORIZATION: the planfile handoff for PLF-039 asks to
execute this refactor autonomously and close it with `planfile ticket done`.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-039 handoff).
- [x] AC-02: `cargo test --manifest-path packages/koru-scan-todo/Cargo.toml`
  passes unchanged (no test edits).
- [x] AC-03: `python3 -m pytest -p no:wellmanifest_governance
  tests/test_scan_todo_rust.py` passes unchanged.
- [x] AC-04: code2llm reports CC <= 15 for `extract_python_comments` and no
  new complexity smell in `packages/koru-scan-todo`.
- [x] AC-05: `project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
