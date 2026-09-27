# Ticket 304: Address code smell: Shotgun Surgery: fw locals in portal input

- **ID**: ticket-304
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-039 (high priority, default
queue), implement the smallest smell-removing refactor and run the local
regression gates (recorded here per AGENTS.md rule 4; no human-owned
`user-*.md` file was created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: fw` smell (planfile ticket PLF-039,
reported for `src/koru/integrations/vdisplay/portal_input.py:270`,
dedupe key `code2llm:smell:shotgun_surgery:src/koru/integrations/vdisplay/portal_input.py:270:Shotgun
Surgery: fw`) in `src/koru/integrations/vdisplay/portal_input.py`.

Six functions in the file mutate a local named `fw`
(`_focus_ring_appeared`, `calibrate_input_from_focus`,
`_pending_action_present`, `_stream_target_from_ocr`, `_precise_stream_xy`,
`_clear_and_reanchor_stream_xy`; reproduced with the installed code2llm
`DFGExtractor` mutation grouping on the file AST: 6 mutation scopes, 201
total mutation records). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; each function
binds an independent frame-width local that only coincidentally shares the
generic name.

Fix: stage-accurate renames pairing the width with each function's already
stage-named height sibling, same lane shape as the merged
ticket-279/ticket-284/ticket-285/ticket-294 rename lanes:

- `guard_w` — pixel-array width of the focus-guard before/after frames
  (`_focus_ring_appeared`, drives the stream→frame window scaling; sibling
  `guard_h`)
- `calib_w` — PNG width of the manual-calibration frame
  (`calibrate_input_from_focus`, passed to `frame_to_stream`; sibling
  `calib_h`)
- `panel_w` — PNG width of the chat-panel frame
  (`_pending_action_present`, drives the right-half panel region test;
  sibling `panel_h`)
- `anchor_w` — PNG width of the OCR-anchor frame
  (`_stream_target_from_ocr`, passed to `frame_to_stream`; sibling
  `anchor_h`)
- `precise_w` — PNG width of the precise-placeholder frame
  (`_precise_stream_xy`, passed to `frame_to_stream`; sibling `precise_h`)
- `reanchor_w` — PNG width of the post-clear re-anchor frame
  (`_clear_and_reanchor_stream_xy`, passed to `frame_to_stream`; sibling
  `reanchor_h`)

Every `fw` is read after its binding, so this is a pure rename — no
inlining, no removed records. Not renamed: `fw0` in
`_maybe_autoremember_focused_input` (a distinct name, not part of the
group) and the `frame` parameters/locals (read-only data flow, not counted
by the detector). The separate `p` group (6 scopes, pre-existing) has its
own planfile ticket and is out of this lane's scope.

## Acceptance criteria

- [x] AC-01: DFGExtractor mutation grouping on the file AST reports the
      `fw` group at 0 scopes after the rename (baseline 6 scopes, exactly
      the ticket's "spans 6 functions"); total mutation record count stays
      201 (pure rename); every renamed local at exactly 1 scope; no group
      newly reaches the >= 5 threshold (`p` stays at 6, pre-existing with
      its own planfile ticket).
- [x] AC-02: `tests/test_portal_input.py` passes unchanged and
      `ruff check src/koru/integrations/vdisplay/portal_input.py` is clean.
- [x] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS from this worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
