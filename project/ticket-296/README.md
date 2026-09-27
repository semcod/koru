# Ticket 296: Rename the generic found locals to stage-accurate names in scan_artifacts

- **ID**: ticket-296
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-041 (high priority, current
sprint): code2llm reports `Shotgun Surgery: found` at
`src/koru/scan_artifacts.py:86` with the mutation spanning 7 functions —
make the smallest refactor that removes the smell and run local tests
(recorded here per AGENTS.md rule 4; no human-owned `user-*.md` file was
created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: found` smell (planfile ticket
PLF-041, reported for `src/koru/scan_artifacts.py:86`).

Seven functions in the file bind a local named `found`
(`_find_analysis_file`, `_load_yaml_mapping`, `_parse_high_cc_suggestions`,
`_scan_vallm_validation`, `_scan_structured_semcod_report`,
`_scan_pfix_report`, `_scan_metrun_report`; reproduced with the installed
code2llm `DFGExtractor` mutation grouping on the file AST: 7 mutation
scopes, 247 total mutation records). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each function binds an independent value (an artifact probe hit or a
function-location lookup) that only coincidentally shares the generic
name.

Fix: stage-accurate renames plus one inlined pure selection, same lane
shape as the merged ticket-279/ticket-284/ticket-285/ticket-294/ticket-295
rename lanes:

- `yaml_artifact` — the first existing YAML artifact probe hit
  `(path, rel)` in `_load_yaml_mapping`
- `func_locations` — the recorded `file:line` locations for the
  CC-reported function in `_parse_high_cc_suggestions`
- `validation_artifact` — the located VALLM validation report in
  `_scan_vallm_validation`
- `report_artifact` — the located structured report (shared by the
  pyqual/prefact/regix/redsl scanners) in `_scan_structured_semcod_report`
- `diagnose_artifact` — the located Pfix diagnose report in
  `_scan_pfix_report`
- `metrun_artifact` — the located Metrun report in `_scan_metrun_report`
- `_find_analysis_file` keeps no local at all: its single-use
  `found if found is not None else (None, "")` inlines into the pure
  selection `_first_existing_artifact(...) or (None, "")` (the probe
  returns `None` or an always-truthy 2-tuple, so the `or` is equivalent)

## Non-goals

- No behavior change: same suggestions, same artifact probe order, same
  fallbacks; function signatures and the module `__all__` untouched
- No rename of the pre-existing `path` (12), `rel` (9), `suggestions` (7),
  `payload` (6), `priority` (6) or `text` (6) groups — each a separate
  unreported dedupe key; this lane only clears the reported `found` group
- No new shared helper: the surviving renames bind different artifact
  families and lookup shapes; forcing an abstraction would couple
  independent scanners

## Acceptance criteria

- [x] AC-01: code2llm DFGExtractor mutation grouping on the file AST
      reports the `found` group at 0 scopes (baseline 7), each new name at
      exactly 1 scope, and no other variable group newly reaches the
      >= 5 threshold
- [x] AC-02: the scan suites covering the touched module
      (`tests/test_scan_artifacts.py`, `tests/test_scan_split.py`,
      `tests/test_scan.py`) show no new failures vs the `main` baseline;
      ruff reports zero errors on the touched file
- [x] AC-03: `./project/governance-check.sh` reports 0 errors and 0
      warnings from the ticket worktree
