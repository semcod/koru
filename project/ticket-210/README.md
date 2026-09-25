# Ticket 210: Decompose god function apply plan tickets

- **ID**: ticket-210
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: `God Function: _apply_plan_tickets` in
`src/koru/autonomy/todo2code_discovery.py:502` (PLF-027).

Extract focused helper functions for plan relative path resolution (`_relative_plans_path`),
plan deduplication identity (`_plan_identity`), plan priority resolution (`_resolve_plan_priority`),
scaffold enrichment (`_enrich_plan_scaffold`), and task dispatch (`_dispatch_plan_task`).
Preserve identical usefulness filtering, deduplication keys, task creation arguments, and result tuples.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-027 queue handoff).
- [x] AC-02: `_apply_plan_tickets` and all new helpers have CC <= 7 (Rank A or B).
- [x] AC-03: `pytest -q tests/test_todo2code_discovery.py tests/test_todo2code_dedupe.py` passes unchanged.
- [x] AC-04: `code2llm` re-run reports no god function finding for `_apply_plan_tickets`.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
