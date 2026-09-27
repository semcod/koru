# Ticket 294: Address code smell: Shotgun Surgery: filtered locals in koruide command picker

- **ID**: ticket-294
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

Clear the code2llm `Shotgun Surgery: filtered` smell (planfile ticket
PLF-039, reported for
`packages/koruide/src/koruide/command_picker.py:182`) in
`packages/koruide/src/koruide/command_picker.py`.

Five functions in the file mutate a local named `filtered`
(`_sanitize_antigravity_focus_open`, `_sanitize_vscodium_focus_open`,
`_sanitize_cursor_submit`, `_sanitize_cursor_paste`,
`_sanitize_cursor_focus_open`; reproduced with the installed code2llm
`DFGExtractor` mutation grouping on the file AST: 5 mutation scopes, 78
total mutation records). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; each function
binds an independent list that only coincidentally shares the generic name.

Fix: stage-accurate renames plus one pure selection, same lane shape as the
merged ticket-279/ticket-284/ticket-285 rename lanes:

- `non_rejected` — the plugin-reported commands left after removing the
  rejected antigravity agent/chat openers
  (`_sanitize_antigravity_focus_open`, consumed by the preferred-side-panel
  ordering)
- `allowed` — the commands passing the vscodium focus_open candidate policy
  (`_sanitize_vscodium_focus_open`, passed to `_prefer_commands`)
- `submit_candidates` — the commands passing the cursor submit candidate
  policy (`_sanitize_cursor_submit`, with the hardcoded pair kept as the
  empty fallback)
- `paste_candidates` — the commands passing the cursor paste candidate
  policy (`_sanitize_cursor_paste`, with the hardcoded typeText ladder kept
  as the empty fallback)
- `_sanitize_cursor_focus_open` keeps no local at all: its single-use
  binding is inlined into the return (pure selection), removing that
  mutation record outright

Not renamed: the `commands` parameters (read-only, not counted as mutations
by the detector) and the module-level sanitize dispatch
(`_sanitize_focus_open_candidates`, `_sanitize_cursor_candidates`,
`_sanitize_candidates`), which routes by (ide, capability) and is not part
of the mutation group.

## Acceptance criteria

- [x] AC-01: DFGExtractor mutation grouping on the file AST reports the
      `filtered` group at 0 scopes after the rename (baseline 5 scopes,
      exactly the ticket's "spans 5 functions"); total mutation record count
      drops from 78 to 77, the single removed record being the inlined
      `_sanitize_cursor_focus_open` selection; every renamed local at 1
      scope; no group newly reaches the >= 5 threshold (next highest:
      `ordered`/`rate` at 3, pre-existing).
- [x] AC-02: `tests/test_command_picker.py tests/test_autonomous_submit_strategy.py
      tests/test_koruide_daemon_handlers_drive.py` pass unchanged and
      `ruff check packages/koruide/src/koruide/command_picker.py` is clean.
- [x] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS from this worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
