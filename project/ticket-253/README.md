# Ticket 253: Address code smell: shotgun surgery commands in todo2code gate

- **ID**: ticket-253
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery: commands` report for
`src/koru/queue/todo2code_gate.py:73` (planfile **PLF-043**): the generic local
name `commands` is assigned in five functions of the verify-gate pipeline, so
code2llm counts 5 same-file mutators for one variable. Give each pipeline stage
local a stage-accurate name (`declared`, `declared_commands`, `gates`) and
replace the only conditional rebinding — the parameter overwrite in
`_compose_wrapped_commands` — with the pure selection
`gates = container_commands or commands`. Produced command lists, detector
precedence and error strings stay byte-identical.

Scope: `src/koru/queue/todo2code_gate.py` and
`tests/test_todo2code_autonomous_gate.py` only (XS delivery contract in
`intent.json`).

## Acceptance criteria

- [ ] AC-01: No function in `todo2code_gate.py` assigns or mutates a variable
  named `commands` (grep for assignment/mutating calls is empty).
- [ ] AC-02: `tests/test_todo2code_autonomous_gate.py` passes, including the
  new compose-fallback pin (`test_docker_project_wraps_host_gates_when_container_declares_none`).
- [ ] AC-03: Neighboring todo2code suites (`test_todo2code_ticket_text.py`,
  `test_todo2code_modules.py`, `test_todo2code_discovery.py`) stay green.
- [ ] AC-04: `project/governance-check.sh` reports 0 errors.

## Session authorization

`SESSION_EXECUTION_AUTHORIZATION`: planfile handoff PLF-043 (2026-09-26)
instructed this session to continue the implementation autonomously, run the
relevant checks before closing, and not leave completed work in
`waiting_input`. Recorded by the Claude lane (agent-owned file).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
