# Ticket 175: decompose god function get_vql_chat_target_from_photo

- **ID**: ticket-175
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Remove the code2llm `God Function: get_vql_chat_target_from_photo` smell
(STARTER-578) from `src/koru/integrations/vdisplay_client.py` by extracting
the nested closures and selection stages into module-level helpers, without
behavior change.

## Acceptance criteria

- [ ] AC-01: `get_vql_chat_target_from_photo` no longer trips the code2llm
  god-function thresholds (CC<=12, fan-out<=10, mutations<=6).
- [ ] AC-02: Existing VQL chat-target tests pass unchanged.
- [ ] AC-03: Ruff and the governance gate pass.

## Slice 2: STARTER-584 (2026-09-19)

The same file's orchestrator `perform_photo_vql_focus_and_edit` was reported
by code2llm as `God Function` (CC=10, fan-out=22, mutations=39; planfile
ticket STARTER-584). Active scope already belongs to this ticket
(`rejectActiveScopeOverlap`), so the slice continues here.

Extracted the phase sequence into module helpers with two context dicts
(`selected`, `plan`): `_photo_vql_entry_gate_blocker`,
`_photo_vql_selected_target`, `_photo_vql_refined_plan`,
`_photo_vql_edit_stages` and `_photo_vql_edit_pipeline`. The dead
`use_llm_vision` local (F841; gating lives in
`_resolve_photo_vql_llm_coords`) was removed. Call order, kwargs, returns
and the public API are unchanged.

- AC-04: `perform_photo_vql_focus_and_edit` no longer trips the code2llm
  god-function thresholds (was CC=10/fan-out=22/mutations=39; now
  CC=6/fan-out=5/mutations=0 measured by the same project analyze).
- AC-05: No new code2llm smell entries introduced for this file, and no
  helper exceeds the thresholds (max observed: fan-out 5, mutations 6, CC 5).
- AC-06: tests/test_photo_vql_drive.py, tests/test_photo_vql_orchestrator.py,
  tests/test_vdisplay_control_fallback.py and the full `vdisplay or vql`
  selection pass (175 passed, 4 skipped).
- AC-07: `ruff check` clean; `./project/governance-check.sh` GOV-PASS.
