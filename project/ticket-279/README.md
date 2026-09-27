# Ticket 279: Address code smell: Shotgun Surgery: event locals in koru observability emit helpers

- **ID**: ticket-279
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: event` smell (planfile ticket PLF-054,
reported for `src/koru/observability_events.py:57`) in
`src/koru/observability_events.py`.

Eight functions in the file assign a local named `event`
(`emit_intent`, `emit_decision`, `emit_action`, `emit_phase`, `emit_verify`,
`emit_failure`, `emit_blocker`, `emit_next`; reproduced with the installed
code2llm `DFGExtractor` mutation grouping on the file AST: 8 mutation
records, one per scope). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; each function
actually builds, records and returns one distinct event kind
(`autopilot.intent`, `autopilot.route.decision`,
`autopilot.drive.requested`, `autopilot.drive.phase`,
`autopilot.drive.verified`, `autopilot.drive.failed`, `autonomy.blocker`,
`autonomy.next`), so no real logic is shared across the scopes.

Fix: name each helper's local after the event kind it owns —
`intent_event` (`emit_intent`), `decision_event` (`emit_decision`),
`action_event` (`emit_action`), `phase_event` (`emit_phase`),
`verified_event` (`emit_verify`), `failure_event` (`emit_failure`),
`blocker_event` (`emit_blocker`), `next_event` (`emit_next`). The
`record_obs_event` parameter stays `event`: it is a single scope, is not an
assignment, and never contributed to the mutation group.

## Non-goals

- No behavior, emission semantics or interface change.
- No restructuring into a shared private emit helper; each `emit_*` already
  owns exactly one stage (one event kind), the shared generic name was the
  defect, not a missing abstraction.
- No rename of locals in other files that happen to use `event` (each is an
  independent local in its own file scope).

## Evidence

- AC-01: standalone `DFGExtractor` mutation grouping on the file AST —
  baseline `'event'` group of exactly 8 scopes (matching the ticket's
  "spans 8 functions"); after the rename the `'event'` group is empty, file
  mutation record count unchanged at 9 (pure rename), every renamed local
  lands at 1 scope, far below the >= 5 threshold.
- AC-02: `python3 -m pytest tests/test_koruide_daemon_handlers_ack.py
  tests/test_koruide_standalone_import.py
  tests/test_koruide_daemon_handlers_drive.py -q` and
  `ruff check src/koru/observability_events.py` — the suites that exercise
  the emit paths pass unchanged; ruff reports zero errors.
- AC-03: `bash project/governance-check.sh --base <merge-base>` — GOV-PASS
  with the changed files declared.

## Delivery

Pure rename of function-internal locals in one module; no signature, return
shape or behavior change; rollback is reverting the ticket commit.
