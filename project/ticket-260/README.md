# Ticket 260: Resolve remaining ruff lint errors across codebase

- **ID**: ticket-260
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Resolve all remaining ruff lint errors across `src` and `tests` so that `post_run_verify` in `koru.yaml` passes cleanly without failing or reopening tickets in the autonomous queue.

1. Reorganize imports in `src/koru/queue/runner.py`, `src/koru/queue/runners.py`, `tests/test_queue_runners.py`, and `tests/test_dashboard_terminals.py`.
2. Break long lines (>120 chars) in `tests/test_dashboard_terminals.py`, `tests/test_scan_todo_rust.py`, and `tests/test_todo2code_modules.py`.
3. Remove unused imports in `tests/test_multi_agent.py`, `tests/test_scan_todo_rust.py`, and `tests/test_todo2code_modules.py`.

## Acceptance criteria

- [ ] AC-01: `ruff check src tests` reports zero findings repo-wide.
- [ ] AC-02: Pytest passes cleanly on all modified test suites.
- [ ] AC-03: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
