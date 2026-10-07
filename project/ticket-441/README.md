# Ticket 441: Repair diff paths missing src prefix in diff repair

- **ID**: ticket-441
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

Enhance `extract_unified_diff` in `diff_repair.py` to optionally accept `known_files` or `project` root path so that model diffs omitting the `src/` prefix for files located under `src/` are cleanly normalized before git apply.

## Acceptance criteria

- [x] AC-01: `extract_unified_diff` normalizes missing `src/` prefix when matching `known_files` or existing files under `project/src/`.
- [x] AC-02: Unit tests in `test_planfile_queue.py` pass and all existing `TestPatchMode` tests pass.
- [x] AC-03: Governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
