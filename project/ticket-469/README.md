# Ticket 469: fix(scan,discovery): exclude .worktrees in code2llm runs and resolve high-CC refactor files

- **ID**: ticket-469
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous resilience and prevention repairs in `semcod/koru` and `dockuri/willops` to prevent stale worktree scanning and targetless `code2llm_refactor` tickets.

## Goal and scope

Exclude `.worktrees` and `worktrees` in `code2llm` discovery runs (`DEFAULT_EXCLUDES`, `DEFAULT_SOURCE_SKIP_DIRS`, and `_code2llm_regenerate_command`) so linked worktrees do not pollute `analysis.toon.yaml`, and populate located high-CC file paths onto `code2llm_refactor` (`split N high-CC methods`) suggestions so they are never created with `files: []`.

## Acceptance criteria

- [x] AC-01: `pytest tests/test_code2llm_discovery.py tests/test_diff_repair_and_refactor.py -q` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
