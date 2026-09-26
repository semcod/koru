# Ticket 232: Extract vdisplay runtime and readiness helpers from vdisplay client

- **ID**: ticket-232
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Extract vdisplay runtime discovery, agent probing, fallback decision policies,
source resolution, and readiness annotations from
`src/koru/integrations/vdisplay_client.py` into
`src/koru/integrations/vdisplay_readiness.py`. Maintain 100% backward-compatible
re-exports in `vdisplay_client.py` and test compatibility (including monkeypatches).
Base: origin/main `09310f23`.

SESSION_EXECUTION_AUTHORIZATION: the planfile handoff for decomposing the vdisplay_client
God Module authorizes executing this refactor autonomously under Wellmanifest rules.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile handoff).
- [x] AC-02: All existing vdisplay tests pass (`pytest -q tests/test_vdisplay*.py -p no:wellmanifest_governance`).
- [x] AC-03: New unit tests in `tests/test_vdisplay_readiness.py` pass.
- [x] AC-04: `project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
