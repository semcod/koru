# Ticket 252: Address code smell: shotgun surgery command in operator wup

- **ID**: ticket-252
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery: command` report for
`src/koru/autonomy/operator/operator_wup.py:329` (planfile **PLF-042**): the
variable `command` is assigned and grown via `append`/`extend` across the
module's watch and docker-compose call sites. Make `_build_command(base,
*groups)` the single owner of argv-list mutation and stop rebinding the name
`command` at read-only consumers. Produced argv lists stay byte-identical.

Scope: `src/koru/autonomy/operator/operator_wup.py` and
`tests/test_autonomous.py` only (XS delivery contract in `intent.json`).

## Acceptance criteria

- [ ] AC-01: The only `command` assignment/mutation lives inside
  `_build_command`; no other function grows a command list.
- [ ] AC-02: Existing wup argv pins plus new `_build_command` /
  `_compose_ps_command` tests pass (`pytest tests/test_autonomous.py -k wup`).
- [ ] AC-03: Full `tests/test_autonomous.py` suite passes (no baseline
  regression).
- [ ] AC-04: `project/governance-check.sh` reports 0 errors.

## Session authorization

`SESSION_EXECUTION_AUTHORIZATION`: planfile handoff PLF-042 (2026-09-26)
instructed this session to continue the implementation autonomously, run the
relevant checks before closing, and not leave completed work in
`waiting_input`. Recorded by the Claude lane (agent-owned file).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
