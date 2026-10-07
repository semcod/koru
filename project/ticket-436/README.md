# Ticket 436: normalize analysis toon path and fix split hunk headers in diff repair

- **ID**: ticket-436
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

Normalize commonly hallucinated `project/analysis/toon.yaml` paths back to `project/analysis.toon.yaml` and repair split hunk headers (`@@ -\n...`) in `src/koru/queue/diff_repair.py`.

## Acceptance criteria

- [x] AC-01: `extract_unified_diff` heals split hunk headers where `@@ -` is followed by a newline and numbers.
- [x] AC-02: `extract_unified_diff` repairs paths referencing `project/analysis/toon.yaml` to `project/analysis.toon.yaml`.
- [x] AC-03: Regression tests and governance check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
