# Ticket 307: Rename generic ide lane locals to stage-accurate resolved-lane names in cli_dispatch

- **ID**: ticket-307
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-042 (high priority, current
sprint), make the smallest smell-removing refactor and run the local tests
(recorded here per AGENTS.md rule 4; no human-owned `user-*.md` file was
created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: ide` smell (planfile ticket PLF-042,
reported for `packages/coru/src/coru/cli_dispatch.py:186`, dedupe key
`code2llm:smell:shotgun_surgery:packages/coru/src/coru/cli_dispatch.py:186:Shotgun
Surgery: ide`) in `packages/coru/src/coru/cli_dispatch.py`.

Five functions in the file mutate a local named `ide` via the identical
tuple unpack `ide, instance = default_lane(args.ide, args.instance)`
(`dispatch_lane_command`, `dispatch_auto_command`,
`dispatch_calibration_command`, `dispatch_daemon_command`,
`dispatch_doctor_command`; reproduced with the installed code2llm
`DFGExtractor` mutation grouping on the file AST: 5 mutation scopes). The
detector groups mutations by (file, variable) and fires at >= 5 scopes.
Unlike the PLF-039 portal-input case (one generic name, six unrelated
frames -> per-site renames), here all five bindings are the *same* stage —
resolve the targeted lane from CLI args plus configured defaults —
copy-pasted into every dispatcher: genuine duplication, not naming
coincidence.

## Fix

Centralize the repeated resolution and read it through attribute access:

- new module-local `_resolve_lane(args, default_lane)` owns the single
  remaining unpack and returns the NamedTuple `ResolvedLane(ide, instance)`
- each dispatcher binds one stage-accurate lane local: `lane`
  (`dispatch_lane_command`, per matched branch exactly as before, plus the
  stage-1 resolution in `dispatch_calibration_command`), `auto_lane`
  (`dispatch_auto_command`), `calibration_lane` (the
  `ResolvedLane(*resolve_calibration_lane(...))` re-target),
  `doctor_lane` (`dispatch_doctor_command`), `daemon_lane`
  (`dispatch_daemon_command`) and reads `lane.ide` / `lane.instance` —
  attribute access is not a variable mutation, so no group re-forms
- behavior unchanged: same `default_lane` call on the same matched branches
  in the same order (nothing hoisted ahead of a command match or a
  `requires_system_shell` check), same handler arguments; the injected
  `default_lane` callable in `coru.cli` keeps returning a plain tuple

## Validation

- AC-01: standalone DFGExtractor mutation grouping on the file AST —
  baseline `ide` group = exactly the reported 5 scopes; after the refactor
  `ide`/`instance` = 1 scope each (`_resolve_lane`), `lane` = 2,
  stage-named locals = 1 each, largest remaining group `rc` = 3
  (pre-existing, below the >= 5 threshold): **no group fires**
- AC-02: `pytest packages/coru/tests/test_coru_cli.py -q` — 117 passed,
  failure set byte-identical to the branch base (13 pre-existing
  environmental reds, verified by swapping HEAD file content in and
  diffing sorted FAILED lists): zero new failures; `ruff check` clean on
  the touched file
- AC-03: `project/governance-check.sh --base <merge-base>` — GOV-PASS
  0 errors 0 warnings
