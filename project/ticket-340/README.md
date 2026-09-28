# Ticket 340: optimize context tree traversal and align mcp test assertions

- **ID**: ticket-340
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

Optimize `_read_file_tree` in `src/koru/queue/context_files.py` by replacing unbounded `sorted(project.rglob("*"))` with an `os.walk` that prunes excluded directory subtrees in-place, reducing file traversal from ~22 seconds down to <100 milliseconds for projects with large virtual environments or git histories.
Also align `test_mcp_server.py` test assertion with `regix review` to restore clean suite passes.

## Acceptance criteria

- [x] AC-01: `_read_file_tree` uses `os.walk` with directory pruning for `_ALWAYS_EXCLUDED_NAMES` and `_is_excluded` paths, avoiding traversing into ignored subtrees.
- [x] AC-02: `test_mcp_server.py` verifies the updated `regix review` gate command.
- [x] AC-03: All unit tests in `tests/test_queue_context_modules.py` and `tests/test_mcp_server.py` pass without regression.
- [x] AC-04: Full governance check passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
