# Ticket 236: Split god module vdisplay_client by responsibility

- **ID**: ticket-236
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address the code2llm god-module report for
`src/koru/integrations/vdisplay_client.py` (6546 lines, 272 top-level
functions; gate is >40) — planfile ticket PLF-040.

Split the module by responsibility, moving every definition verbatim into
`src/koru/integrations/vdisplay/`:

- `source_policy.py` — capture/source policy flags (`_vdisplay_source*`,
  `_capture_matches_requested_ide`, `_prefer_photo_vql_chat`,
  `_auto_ide_control_enabled`, `_auto_open_ide_enabled`, ...)
- `vql_sidecar.py` — sidecar observation, PNG resolution, capture-meta
  interpretation and the refresh pipeline (`_observe_vql_sidecar_path`,
  `_resolve_photo_png_path*`, `_photo_vql_ide_capture_mismatch`,
  `refresh_photo_vql_sidecar`, ...)
- `imgl_loader.py` — imgl/vdisplay CLI discovery, import machinery and
  subprocess env (`_real_imgl_src`, `_import_imgl_*`, `_vdisplay_cli_*`)
- `ide_control.py` — window focus and semantic IDE control orchestration
  (`_focus_window_*`, `_ide_control_*`, `ensure_vdisplay_ide_control`)
- `drive_prepare.py` — photo-VQL drive preparation (`_prepare_photo_vql_*`,
  `prepare_photo_vql_for_drive`)
- `chat_send.py` — send_chat pipeline and selector plumbing
  (`_send_chat_*`, `send_chat`, `_IDE_HINTS`, `_CHAT_INPUT_SELECTORS`,
  `_SUBMIT_BUTTON_SELECTORS`)
- `input_actuation.py` — agent controls, keyboard submit, IDE-prompt and OS
  type-text (`_agent_client`, `_control_*`, `_find_first_selector`,
  `_submit_via_keyboard`, `send_chat_via_ide_prompt`, `_type_text_*`)
- `chat_target.py` — photo-VQL chat target resolution
  (`get_vql_chat_target_from_photo`, `_photo_vql_*_chat_flow`, ...)
- `map_pointer.py` — IDE-map capture/pointer target math (`_map_chat_*`,
  `click_editor_via_photo_vql`, `_enrich_capture_meta_for_pointer`)
- `command_plan.py` — VQL command plan, cursor validation and LLM coordinate
  resolution (`_build_vql_command_plan`, `_vql_plan_*`,
  `_resolve_photo_vql_llm_coords*`)
- `capture_gates.py` — capture-mismatch and unverified-chat gating
  (`_photo_vql_capture_mismatch_*`, `_map_capture_mismatch_for_*`,
  `_photo_vql_unverified_chat_blocked`)
- `focus_edit.py` — focus-and-edit pipeline and mouse move
  (`perform_photo_vql_focus_and_edit`, `_photo_vql_edit_*`,
  `move_mouse_to_vql_target_and_focus_keyboard`)
- `vql_metadata.py` — candidate/metadata loading, freshness policy and the
  optional-extra `vdisplay.vql` shims (`load_vql_metadata`, `get_vql_target`,
  `resolve_click_for_frame`, `_vql_from_*`)

`vdisplay_client.py` keeps the runtime/availability wrappers, chat-text OCR
verification, `record_koru_drive_step` and the `vdisplay_fallback_enabled`
wrapper (10 defs; they read the patchable `_VDISPLAY_DIRECT` facade state)
and re-exports every moved name so `from koru.integrations.vdisplay_client
import X` keeps working (the `nxdo_discovery` facade pattern from tickets
234/235). A patch audit across `tests/` and `packages/coru/tests/` found 62
distinct facade-level monkeypatch targets; moved code resolves former module
globals through a lazy `_vdc()` facade accessor at call time, so patching the
facade keeps steering the pipeline (patch targets route through the facade
even when caller and callee share a new module — the LOAD_GLOBAL /
`__getattr__` regression documented above the `vdisplay.vql` shims).

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `vdisplay_client.py` reduced to a slim facade (10 top-level defs);
  the thirteen responsibility modules stay under the god-module gate (40).
- [x] AC-03: Behavior preserved — pre-split vdisplay/photo-vql test files pass
  unchanged.
- [x] AC-04: Import surface stable — every pre-split name still imports from
  `koru.integrations.vdisplay_client`; facade monkeypatching keeps steering
  moved code; no consumer file modified.
- [x] AC-05: `tests/test_vdisplay_module_split.py` passes and
  `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-040 planfile handoff instructs to
split the module, keep imports/patching stable, run local regression gates
and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
