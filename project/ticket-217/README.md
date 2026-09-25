# Ticket 217: Decompose god function configure_loop_state

- **ID**: ticket-217
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: configure_loop_state` in
`src/koru/autonomy/cycle/cycle_config.py:145` (PLF-035).

Split the shell-client resolution cascade into `_resolve_shell_client`, its
`os.environ` exports into `_export_shell_client_env`, the IDE-vs-shell-client
selection into `_resolve_selected_ide`, the queue-flag fold into
`_resolve_queue_selection` (returning a `_QueueSelection` NamedTuple) and the
checkpoint restoration into `_restore_loop_checkpoint` (returning a
`_LoopCheckpoint` NamedTuple) so `configure_loop_state` contains no tuple
unpacking (double-counted as mutations by code2llm). Preserve the public
signature, return tuple, stderr messages and the loud `SystemExit` misrouting
guard unchanged.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-035 queue handoff).
- [x] AC-02: `configure_loop_state` metrics fall under the god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6); every new helper stays under too.
- [x] AC-03: `pytest -q tests/test_autonomous_cycle_config.py tests/test_shell_client_auto_routing.py` passes unchanged.
- [x] AC-04: code2llm analysis of the changed file reports no function above any god-function threshold.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
