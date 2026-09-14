# Ticket 124: Pin mcp<2 in root extras

- **ID**: ticket-124
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-13

## Goal and scope

Pin `mcp>=1.0` -> `mcp>=1.0,<2` in root pyproject extras (integration workstream).

## Acceptance criteria

- [x] AC-01: Scope is approved by the owner through the execution request.
- [x] AC-02: Both root MCP constraints are bounded to `<2` and `uv.lock` is current.
- [ ] AC-03: Governance, stack checks and protected exact-head merge pass.

## Validation evidence

- `uv lock --check`: passed.
- `./project/governance-check.sh --base origin/main --head HEAD --actor agent`: passed.
- `PYTHONPATH=. uv run pytest -q tests/test_mcp_server.py tests/test_queue_cli_helpers.py tests/test_planfile_queue.py`: 108 passed.
- Full suite: 4066 passed, 29 skipped, 162 deselected; three failures are reproduced
  unchanged on clean `origin/main` (`test_ide_doctor_treats_auto_instance_as_selected_ide`
  and two stale `test_pyproject_metadata` expectations), so they are baseline failures.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
