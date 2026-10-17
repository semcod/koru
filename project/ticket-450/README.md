# Ticket 450: Upgrade diff repair, search-replace synthesis, governed workspace support, and scan artifact filtering

- **ID**: ticket-450
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-16

SESSION_EXECUTION_AUTHORIZATION: user requests autonomous execution to upgrade diff repair, search/replace diff synthesis, governed ticket worktree support, scan artifact filtering, context slicing for module refactors, and verification gate auto-detection.

## Goal and scope

Upgrade `koru` patch mode and refactoring pipeline so module splitting, deduplication, and governed ticket worktree execution succeed reliably:
1. Add `synthesize_diff_from_search_replace` and fuzzy hunk repair in `src/koru/queue/diff_repair.py`, plus fixes for fenced blocks, new/deleted file `/dev/null` headers, and inner `--- ` comment preservation.
2. Wire `project` and `known_files` into `extract_unified_diff` across `patch_mode.py`, `transaction/preflight.py`, and `patch_retry.py`.
3. Support admitted governed ticket worktrees (`_is_admitted_ticket_worktree`) and `ticket-` staging worktree prefixes in `src/koru/queue/workspace.py`.
4. Stop scan artifacts (`analysis.toon.yaml`, `duplication.toon.yaml`, etc.) from polluting target `files` in `src/koru/scan_artifacts.py`, `src/koru/queue/context_files.py`, and `src/koru/queue/patch_retry.py`, and add `duplication.toon.yaml` parsing.
5. Prevent destructive AST truncation on module-split/refactor prompts in `src/koru/queue/context_slicing.py`.
6. Auto-detect safe fallback verification gates (`pytest`, `cargo test`, `npm test`) in `src/koru/queue/verify/legacy.py`.
7. Add unit tests in `tests/test_diff_repair_and_refactor.py`.

## Acceptance criteria

- [x] AC-01: `diff_repair.py` synthesizes unified diffs from search/replace and new-file blocks, repairs fuzzy hunks against disk, emits `/dev/null` headers for added/deleted files, and preserves valid removed `--- ` lines inside hunks.
- [x] AC-02: `patch_mode.py`, `transaction/preflight.py`, and `patch_retry.py` pass `project` and `known_files` to `extract_unified_diff`.
- [x] AC-03: `workspace.py` admits governed ticket worktrees via `_is_admitted_ticket_worktree` and prefixes staging worktrees with `ticket-`.
- [x] AC-04: `scan_artifacts.py`, `context_files.py`, and `patch_retry.py` exclude read-only scan artifacts from target files and parse `duplication.toon.yaml`.
- [x] AC-05: `context_slicing.py` avoids false-positive English symbol extraction and bypasses AST slicing for refactor/split prompts up to 64,000 chars.
- [x] AC-06: `verify/legacy.py` auto-detects project test commands when no explicit verify gate is configured.
- [x] AC-07: Unit tests in `tests/test_diff_repair_and_refactor.py` and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
