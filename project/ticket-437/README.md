# Ticket 437: Enhance unmanaged workspace check and code2llm context file resolution

- **ID**: ticket-437
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

Enhance `require_unmanaged_patch_workspace` to specifically check for `.governance/manifest.json` instead of a bare `.governance` directory (which may contain only documentation adoption such as `docs.json`).
Enhance `code2llm` ticket generation in `src/koru/scan_artifacts.py` so that high cyclomatic complexity (CC) and refactor suggestions resolve concrete source files from `calls.yaml` or module paths, avoiding fallback to `project/analysis.toon.yaml` as the sole context file when the function source can be identified.

## Acceptance criteria

- [x] AC-01: `require_unmanaged_patch_workspace` only triggers admission requirement if `.governance/manifest.json` exists in project or primary checkout.
- [x] AC-02: `_parse_high_cc_suggestions` and call graph resolution map function symbols to concrete source files, or inspect candidate source files when available.
- [x] AC-03: Governance checks and test suite pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
