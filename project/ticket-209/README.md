# Ticket 209: Atomize scan todo markers engine

- **ID**: ticket-209
- **Owner**: gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Extract and atomize the TODO marker scanning engine from `src/koru/scan.py` into a dedicated, clean, standalone module `src/koru/scan_todo.py` with pure logic separation (comment tokenization, regex matching, .koruignore pattern parsing, and file-tree scanning) suitable for future Rust/PyO3 migration. Re-export `scan_todo_markers` in `src/koru/scan.py` for 100% backward compatibility. Add dedicated unit tests in `tests/test_scan_todo.py` while ensuring existing tests in `tests/test_scan.py` pass without regression.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `src/koru/scan_todo.py` is extracted with pure helper functions (`count_todo_markers`, `load_koruignore_patterns`, `is_koruignored`, `scan_todo_markers`) and clean interface.
- [x] AC-03: `src/koru/scan.py` re-exports `scan_todo_markers` preserving identical behavior and signatures.
- [x] AC-04: Unit tests in `tests/test_scan_todo.py` and `tests/test_scan.py` pass cleanly.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
