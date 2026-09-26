# Ticket 225: Decompose god function run_ticket2dsl

- **ID**: ticket-225
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: run_ticket2dsl` in
`src/koru/autonomy/ticket2dsl.py:287` (PLF-051).

The orchestrator measures CC=10, fan-out=20, mutations=26 — it trips the
code2llm fan-out and mutation gates. Keep it a linear guard/build/snapshot/write
sequence: early skips and build errors construct the `Ticket2dslOutcome`
directly instead of mutating a shared object, the unit-cap resolution
(argument or `KORU_TICKET2DSL_MAX_UNITS`, clamped with `max(1, ...)`) moves to
`_resolve_unit_limit`, the post-build outcome snapshot to `_ran_outcome`, the
`koru.ticket-work-unit-set/v1` payload to `_unit_set_payload` and the three
artifact writes to `_write_ticket2dsl_artifacts` + `_write_artifact`.
`build_work_units` now returns the private `_BuiltUnits` NamedTuple so the
orchestrator reads `.units`/`.filtered` instead of unpacking a bare tuple.
Every outcome field is populated at the same pipeline point and in the same
order as before; OSError during artifact writing still lands in
`outcome.error` with the counts retained.

Session execution authorization: planfile PLF-051 queue handoff delivered the
implementation instruction (observed 2026-09-26).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-051 queue handoff).
- [x] AC-02: `run_ticket2dsl` and every touched or new helper measure
  fan-out <= 10, mutations <= 6 and CC <= 12 (code2llm god-function gates).
- [x] AC-03: `pytest -q tests/test_ticket2dsl.py` passes unchanged.
- [x] AC-04: No untouched function in the module crosses a god-function gate
  it did not already cross before this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
