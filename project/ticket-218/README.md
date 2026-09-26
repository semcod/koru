# Ticket 218: Decompose god function execute patch transaction

- **ID**: ticket-218
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: execute_patch_transaction` in
`src/koru/queue/transaction/service.py:69` (PLF-036).

Extract the orchestrator's inline phases into single-purpose helpers —
`_screen_before_plan` (pre-plan screens, returning a `_ScreenedPatch`
NamedTuple), `_open_run_journal`, `_refuse_invalid_verify_profile`,
`_deliver_artifact`, `_screen_promotion_gates` and `_run_plan` — preserving the
journal event sequence, refusal codes, messages and the public
`execute_patch_transaction` signature exactly.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-036 queue handoff).
- [x] AC-02: `execute_patch_transaction` metrics fall under the god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6); every helper introduced by this ticket stays under too.
- [x] AC-03: `pytest -q tests/test_queue_transaction_phases.py tests/test_queue_verify_profiles.py` passes unchanged plus new regression tests pinning the orchestrator's journal phase sequence.
- [x] AC-04: code2llm metric probe of the changed file reports no function above any god-function threshold introduced by this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
