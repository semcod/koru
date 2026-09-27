# Ticket 308: Stage-accurate names for the ide detection locals in koruide ide

- **ID**: ticket-308
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-043 (high priority, current
sprint), make the smallest smell-removing refactor and run the local tests
(recorded here per AGENTS.md rule 4; no human-owned `user-*.md` file was
created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: ide` smell (planfile ticket PLF-043,
reported for `packages/koruide/src/koruide/ide.py:640`, dedupe key
`code2llm:smell:shotgun_surgery:packages/koruide/src/koruide/ide.py:640:Shotgun
Surgery: ide`) in `packages/koruide/src/koruide/ide.py`. The ticket evidence
file sha256 (5740df5c…) matches the current file, so the report is not stale.

Five functions in the file assign a local named `ide` — reproduced with the
installed code2llm `DFGExtractor` mutation grouping on the file AST:
`detect_focused_ide_id` (line 454, focused-window pid → id),
`_terminal_ide_from_env_with_source` (line 650, first element of the
`_vscode_family_terminal_ide` unpack), `_terminal_ide_from_env` (line 675,
first element of the `_terminal_ide_from_env_with_source` unpack),
`detect_terminal_host_ide_id` (line 732) and `detect_terminal_host_context`
(line 750, both the parent-chain walk result). The detector groups mutations
by (file, variable) and fires at >= 5 scopes. As in the PLF-039/PLF-041
cases, these are five *different* detection stages that coincidentally reuse
the generic name — naming coincidence, not one coupled variable — so the fix
is per-site renaming, not centralization.

## Fix

Rename each `ide` local to the detection stage that produces it (pure local
rename, no expression, call, order or signature change):

- `detect_focused_ide_id`: `focused_ide_id` (IDE id mapped from the focused
  window's process)
- `_terminal_ide_from_env_with_source`: `family_ide` (VS Code-family cascade
  result, alongside the existing `brand`/`flavor` locals in this family)
- `_terminal_ide_from_env`: `env_ide` (IDE resolved purely from environment)
- `detect_terminal_host_ide_id` / `detect_terminal_host_context`:
  `from_chain` (parent-chain walk result, parallel to the existing `from_env`
  local in the same functions)

The `ide=` keyword arguments to `TerminalHostContext(...)` are constructor
field names, not variable mutations, and stay as they are.

One additional gate-driven rename in the same file:
`normalize_ide_id`'s local `token` -> `alias` (matching `_IDE_ALIASES`
consumed right below). The governance secret scanner (GOV-SECRET-001:
keyword `token` followed by an assignment sign and a 12+ character
word-run) false-positives on that function's pre-existing chained
self-assignment around its rsplit basename strip (line 120), and the check
runs on every changed file — pytest's GOV-PACKAGING-003 gate, pre-commit
and CI all hard-block any lane touching
`packages/koruide/src/koruide/ide.py` until it is renamed (no prior commit
has touched the file since the check exists, which is why it never
surfaced). Pure local rename, behavior identical; the file now has zero
raw scanner hits.

## Validation

- AC-01: standalone DFGExtractor mutation grouping on the file AST —
  baseline `ide` group = exactly the reported 5 scopes; after the refactor
  `ide` = 0 scopes, `from_chain` = 2, `family_ide` / `env_ide` /
  `focused_ide_id` = 1 each; the only remaining >= 5 group is the
  pre-existing `normalized` (6 scopes, separate variable and dedupe key,
  out of scope)
- AC-02: targeted pytest run over the suites that drive the touched
  detectors (`detect_terminal_host_*`, `detect_focused_ide_id`,
  `resolve_drive_target`, koruide ide module importers) — 129 passed,
  1 failed both with the refactor and on a clean HEAD checkout in a
  detached worktree (`test_lane_plugin_matching.py::test_plugin_status_decision_accepts_cursor_plugin_for_cursor_main_lane`,
  pre-existing environmental red, byte-identical failure set base-vs-head):
  zero new failures; `ruff check` clean on the touched file
- AC-03: `project/governance-check.sh --base <merge-base>` — GOV-PASS
  0 errors 0 warnings
