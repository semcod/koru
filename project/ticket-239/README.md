# Ticket 239: Consolidate photo-VQL blocked-gate persistence in focus_edit

- **ID**: ticket-239
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery: blocked` finding — planfile ticket
PLF-043. The report names `src/koru/integrations/vdisplay_client.py:5576`,
but ticket-236 (origin/main) moved the photo-VQL gates verbatim into
responsibility modules, so on the current base the smell lives in
`src/koru/integrations/vdisplay/focus_edit.py`: a local named `blocked` is
assigned in 5 functions (code2llm flags >=5 per file).

The shared logic that makes the change shotgun is the blocked-gate
persist-and-return tail, repeated inline in five gates:

```python
session = _vdc()._autonomy_session.active_session_dir()
if session is not None:
    _vdc()._autonomy_session.persist_autonomy_phase(session, PHASE, EVENT, blocked)
return blocked
```

Add one module-local helper `_persist_blocked_gate_result(blocked, *,
phase, event)` owning that stanza (resolving `_autonomy_session` through
the late-binding `_vdc()` facade exactly like the inline code) and route
the five gates through it:

- `_photo_vql_stale_metadata_gate` — decide/`stale_abort`
- `_photo_vql_capture_mismatch_gate` — decide/`ide_capture_blocked`
- `_photo_vql_map_source_preflight_gate` — act/`map_source_mismatch_preflight_blocked`
- `_photo_vql_target_map_mismatch_gate` — act/`map_source_mismatch_blocked`
- `_photo_vql_unverified_chat_gate` — act/`chat_actuation_blocked`

After the change `blocked` is assigned only in `_photo_vql_selected_target`
and `_photo_vql_refined_plan` (the result-dict containers), under the
threshold, and persistence policy lives in one function. The helper is
re-exported from the `vdisplay_client` facade, as
`tests/test_vdisplay_module_split.py` pins for every focus_edit def (no
existing name or `__all__` entry changes).

New `tests/test_photo_vql_blocked_gates.py` pins the phase/event wiring of
every gate plus the no-session path.

## Acceptance criteria

- [ ] AC-01: photo-VQL/vdisplay tests pass unchanged (blocked-gate tests,
      orchestrator, drive, guard vision, monitor source, module-split pins).
- [ ] AC-02: `blocked` is assigned in <5 functions of focus_edit.py.
- [ ] AC-03: ruff reports no new findings on the touched files.

## Out of scope

- Any change to gate predicates, abort payload shapes, log text, or event names.
- Any facade change beyond importing the new helper (no rename, move or
  `__all__` change).
- The send-chat `blocked` flow in `vdisplay/chat_send.py` (single-function
  file grouping — under the detector threshold).
- Other code2llm findings (scan.py, mcp_provision.py, ...).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
