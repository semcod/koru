# Ticket 206: Reduce cyclomatic complexity in normalize message

- **ID**: ticket-206
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koruapi.opencode_terminals.normalize_message` (CC=38, limit 15) at
`src/koruapi/opencode_terminals.py:570` (PLF-025).

Extract focused helpers for typed part formatting (`_part_to_chunk`, `_parts_to_chunks`),
legacy shape formatting (`_legacy_chunks`), and metadata resolution (`_message_metadata`).
Preserve identical output dictionary structure, role resolution, chunk joining, and
fallback semantics.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-025 queue handoff).
- [x] AC-02: `normalize_message` and all new helpers have CC <= 9 (Rank A or low B).
- [x] AC-03: `pytest -q tests/test_dashboard_terminals.py tests/test_opencode_serve_scan.py` passes unchanged.
- [x] AC-04: `code2llm` re-run reports no complexity finding for `normalize_message`.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
