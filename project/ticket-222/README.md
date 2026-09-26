# Ticket 222: decompose god function apply plan tickets

- **ID**: ticket-222
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: _apply_plan_tickets` in
`src/koru/autonomy/todo2code_discovery.py:559` (PLF-040).

Round two after PLF-027 (ticket-210) extracted five helpers and dropped CC
14→7: the remaining triggers are fan-out=11 (>10) and mutations=25 (>6).
Extract the per-plan loop body into `_file_plan_ticket` (scaffold, identity,
dedupe skip) and `_record_plan_dispatch` (created/skipped bookkeeping), and
give `_rank_useful_plans`, `_existing_todo2code_keys`, `_plan_identity` and
`_dispatch_plan_task` NamedTuple results so callers stop tuple-unpacking.
Preserve identical usefulness filtering, dedupe identities, limit accounting,
task creation arguments and the returned 4-tuple.

Session execution authorization: planfile PLF-040 queue handoff delivered the
implementation instruction (observed 2026-09-26).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-040 queue handoff).
- [x] AC-02: `_apply_plan_tickets` and every touched or new helper measure
  fan-out <= 10, mutations <= 6 and CC <= 12 (code2llm god-function gates).
- [x] AC-03: `pytest -q` on all five todo2code test modules passes unchanged.
- [x] AC-04: No untouched function in the module crosses a god-function gate
  it did not already cross before this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
