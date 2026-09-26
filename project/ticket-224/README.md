# Ticket 224: decompose god function run nxdo discovery

- **ID**: ticket-224
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: run_nxdo_discovery` in
`src/koru/autonomy/nxdo_discovery.py:348` (PLF-050).

The orchestrator measures CC=14, fan-out=20, mutations=43 — all three
code2llm god-function gates tripped. Split the linear pipeline into phase
helpers that each own a bounded slice of the `NxdoDiscoveryOutcome` writes:
`_preflight` (guard checks, records resolved binary/repo), `_nxdo_command`
(argv assembly with model/extra-context knobs), `_execute` (timed subprocess
run with timeout/exec-error capture), `_record_attempt` (returncode/ran plus
the per-repo cooldown stamp), `_failure_message` (last output line) and
`_interpret_plan` (rc check, TaskPlan parse, ticket application), with
`_Preflight` as a NamedTuple so the orchestrator reads fields instead of
unpacking tuples. Every outcome field is populated at the same pipeline point
and in the same order as before; exec failures still skip the cooldown stamp.

Session execution authorization: planfile PLF-050 queue handoff delivered the
implementation instruction (observed 2026-09-26).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-050 queue handoff).
- [x] AC-02: `run_nxdo_discovery` and every touched or new helper measure
  fan-out <= 10, mutations <= 6 and CC <= 12 (code2llm god-function gates).
- [x] AC-03: `pytest -q tests/test_nxdo_discovery.py tests/test_scan_phase.py`
  passes unchanged.
- [x] AC-04: No untouched function in the module crosses a god-function gate
  it did not already cross before this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
