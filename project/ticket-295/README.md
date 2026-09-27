# Ticket 295: Rename generic fix locals to stage-accurate names in readiness checks

- **ID**: ticket-295
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-040 (high priority, current
sprint), make the smallest refactor that removes the reported smell and run
the local tests (recorded here per AGENTS.md rule 4; no human-owned
`user-*.md` file was created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: fix` smell (planfile ticket PLF-040,
reported for `src/koru/autonomy/readiness/readiness.py:890`).

Five functions in the file bind a local named `fix`
(`_planfile_availability_issue`, `_koru_runtime_identity_issue`,
`check_daemon_client_alignment`, `check_workspace_socket_ownership`,
`check_lane_terminal_socket_alignment`; reproduced with the installed
code2llm `DFGExtractor` mutation grouping on the file AST: 5 mutation
scopes, 148 total mutation records). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each function binds an independent value that only coincidentally shares
the generic name.

Fix: stage-accurate renames plus pure selection, same lane shape as the
merged ticket-279/ticket-284/ticket-285/ticket-294 rename lanes:

- `planfile_install_cmd` — the pip command that installs planfile (venv pip
  when present, plain pip fallback) in `_planfile_availability_issue`
- `bit_fix_command` — the `fix=`-annotated command extracted from the
  koru path/version diagnostic bits in `_koru_runtime_identity_issue`
- `check_daemon_client_alignment` keeps no local at all: its
  `issues[0].fix_command if issues else None` selection is redundant —
  `_build_readiness_result` already defaults a `None` `primary_fix` to
  `_first_fix_command(issues)`, which returns the identical value in every
  reachable case (when `issues[0].fix_command` is set it is by definition
  the first non-`None` fix command; when it is `None` the old code also
  passed `None` and took the same builder default)
- `check_workspace_socket_ownership` keeps no local at all: its
  `next((i.fix_command for i in issues if i.fix_command), None)` *is*
  `_first_fix_command(issues)`, i.e. exactly the builder default
- `check_lane_terminal_socket_alignment` inlines the fallback into the pure
  selection `primary_fix or _first_fix_command(issues)` (the helper is
  side-effect-free, so the lazy `or` evaluation is equivalent)

## Non-goals

- No behavior change: same issues, same `primary_fix` selection, same
  `ReadinessResult` shape; function signatures untouched
- No rename of the pre-existing `issues` group (10 scopes, separate dedupe
  key, not reported by this ticket) or any other group; this lane only
  clears the reported `fix` group
- No new shared helper: the two surviving renames compute unrelated values
  (a pip install command vs a bit-extracted annotation)

## Acceptance criteria

- [x] AC-01: code2llm DFGExtractor mutation grouping on the file AST
      reports the `fix` group at 0 scopes (baseline 5) and no other
      variable group newly reaches the >= 5 threshold
- [x] AC-02: `tests/test_autonomous_readiness.py` passes; ruff reports
      zero errors on the touched file
- [x] AC-03: `./project/governance-check.sh` reports 0 errors and 0
      warnings from the ticket worktree
