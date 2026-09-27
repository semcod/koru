# Ticket 306: Rename the generic ide locals in coru cli to stage-accurate names

- **ID**: ticket-306
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-041 (high priority, current
sprint), implement the smallest smell-removing refactor in
`packages/coru/src/coru/cli.py` and run the local regression gates (recorded
here per AGENTS.md rule 4; no human-owned `user-*.md` file was created or
edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: ide` smell (planfile ticket PLF-041,
reported for `packages/coru/src/coru/cli.py:447`, dedupe key
`code2llm:smell:shotgun_surgery:packages/coru/src/coru/cli.py:447:Shotgun
Surgery: ide`; ticket-evidence file sha256
`5f887e6d1b4cf20addde82b833c766544f70158d83ccd4cfa131da55e13a5194` still
matches the working tree) in `packages/coru/src/coru/cli.py`.

Five functions in the file mutate a local named `ide`
(`_terminal_ide_hint`, `_cmd_repair_history`, `_cmd_repair_run`,
`_cmd_sync`, `_maybe_rewrite_ide_auto_shorthand`; reproduced with the
installed code2llm `DFGExtractor` mutation grouping on the file AST: 5
mutation scopes, 92 total mutation records). The detector groups mutations
by (file, variable) and fires at >= 5 scopes — the shared *name* is the
smell; each function binds an independent local that only coincidentally
shares the generic name. Function parameters and the `Plan`/`SessionContext`
/`AutoReadiness` dataclass fields named `ide` are not counted by the
detector (body-only visit; `AnnAssign` unhandled) and stay unchanged.

Fix: stage-accurate renames, same lane shape as the merged
ticket-265/ticket-296/ticket-304 rename lanes:

- `shell_ide` — IDE owning this shell (`_terminal_ide_hint`, first element
  of the `_terminal_shell_context()` unpack whose docstring already names
  the stage "Best-effort IDE owning this shell")
- `lane_ide` — the lane IDE resolved from `_default_lane(args.ide,
  args.instance)` (`_cmd_repair_history` lane-filter log, `_cmd_repair_run`
  autopilot env payload + lane repair, `_cmd_sync` seeds the sync `Plan`);
  one shared name because all three bind the identical resolved-lane value,
  landing at 3 scopes — below the >= 5 threshold
- `shorthand_ide` — the lane-hint IDE token recognized in the raw argv
  (`_maybe_rewrite_ide_auto_shorthand`, `coru cursor auto` →
  `coru auto cursor`)

Every `ide` is read after its binding, so this is a pure rename — no
inlining, no removed records. Not renamed: the `ide` parameter of
`_project_for_lane` and the dataclass fields (read-only data flow / class
scope, not counted by the detector), `target_ide`/`term_ide` (already
stage-accurate, 1 scope each).

## Acceptance criteria

- [x] AC-01: DFGExtractor mutation grouping on the file AST reports the
      `ide` group at 0 scopes after the rename (baseline 5 scopes, exactly
      the ticket's "spans 5 functions"); total mutation record count stays
      92 (pure rename); `lane_ide` lands at 3 scopes, `shell_ide` and
      `shorthand_ide` at 1 scope each; no group reaches the >= 5 threshold.
- [x] AC-02: The coru cli test modules touching the renamed paths pass
      unchanged (pure rename of function-internal locals) and `ruff check`
      reports no new findings on the touched file (the 2 pre-existing I001
      import-order findings on the facade import block are the verified
      origin/main baseline and stay untouched).
- [x] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS from this worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not delivery output.
