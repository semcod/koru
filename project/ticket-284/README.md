# Ticket 284: Address code smell: Shotgun Surgery: fh locals in vdisplay portal input

- **ID**: ticket-284
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Planfile**: PLF-058 (dedupe key
  `code2llm:smell:shotgun_surgery:src/koru/integrations/vdisplay/portal_input.py:403:Shotgun Surgery: fh`)

## Goal and scope

Clear the code2llm Shotgun Surgery smell for the variable `fh`
in `src/koru/integrations/vdisplay/portal_input.py` (reported at line 403,
planfile ticket PLF-058). Seven functions in the module each assigned a
generic local named `fh`; the code2llm shotgun-surgery detector groups
mutations by (file, variable) and fires at >= 5 scopes, so the shared
generic name read as one cross-cutting concern.

Replace the generic local in each function with a stage-accurate name for
the piece of frame geometry that stage actually consumes:

- `guard_h` (`_focus_ring_appeared`) - the height of the decoded
  before/after RGB array that scales the stream-space target into frame
  pixels and clamps the focus-guard's blue-sampling window.
- `frame_rows` (`_blue_ring_center`) - the decoded frame's row count sizing
  the blue-row bincount histogram that locates the lowest wide ring band.
- `calib_h` (`calibrate_input_from_focus`) - the calibration frame's height
  mapping the detected ring center into stream coords.
- `panel_h` (`_pending_action_present`) - the frame height gating a
  'backspace' OCR box into the chat-panel region above the terminal strip.
- `anchor_h` (`_stream_target_from_ocr`) - the frame height mapping the OCR
  anchor (placeholder or landmark fallback) into stream coords.
- `precise_h` (`_precise_stream_xy`) - the frame height mapping the precise
  placeholder anchor into stream coords (pairs with `precise_fx`).
- `reanchor_h` (`_clear_and_reanchor_stream_xy`) - the frame height mapping
  the post-clear re-anchor position into stream coords.

The sibling `fw` keeps its generic name in this lane: it is a separate open
planfile ticket with its own dedupe key (`...:403:Shotgun Surgery: fw`,
6 scopes) and gets its own rename lane. The already-distinct `aw`/`ah`
(`_focused_near`) and `fw0`/`fh0` (`_maybe_autoremember_focused_input`)
pairs are different variable names and were never counted. The
`frame_w=`/`frame_h=` keyword arguments of `frame_to_stream` are call-site
arguments, not locals, and keep the portal session contract unchanged.
Pure rename: no signature, return shape, env var or behavior change.

Session authority: the planfile handoff for PLF-058 delivered the
implementation instruction and closure commands
(SESSION_EXECUTION_AUTHORIZATION).

## Acceptance criteria

- [x] AC-01: Standalone code2llm DFGExtractor mutation grouping on the file
  AST reports the `fh` group dropping from 7 scopes (matching the ticket's
  "spans 7 functions") to 0, with the file mutation record count unchanged
  at 201 (pure rename) and each new local (`guard_h`, `frame_rows`,
  `calib_h`, `panel_h`, `anchor_h`, `precise_h`, `reanchor_h`) landing at
  exactly 1 scope, far below the >= 5 threshold; the untouched `fw` group
  stays at 6 scopes for its own open ticket.
- [x] AC-02: `python3 -m pytest tests/test_portal_input.py
  tests/test_vdisplay_coordinate_contract.py
  tests/test_autonomous_vdisplay_defaults.py tests/test_vdisplay_module_split.py -q`
  passes unchanged and `ruff check
  src/koru/integrations/vdisplay/portal_input.py` reports zero errors -
  pure rename of function-internal locals.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` returns
  GOV-PASS from the ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
