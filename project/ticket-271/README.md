# Ticket 271: Address code smell: shotgun surgery data locals in scan artifacts

- **ID**: ticket-271
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-046,
reported for `src/koru/scan_artifacts.py:1228`) in
`src/koru/scan_artifacts.py`.

Six functions in the file mutate a local named `data`
(`_scan_jscpd_report`, `_scan_redup_filtered`, `_scan_redup_changed`,
`_scan_structured_semcod_report`, `_scan_pfix_report`,
`_scan_todo2code_plans`). The detector groups mutations by (file, variable)
and fires at >= 5 scopes — the shared *name* is the smell; each function
actually holds an independent decoded artifact (a parsed jscpd duplication
report, one of two redup duplicate-group exports, a structured semcod report
artifact, the pfix diagnose artifact, or the todo2code plans document).

Fix: stage-accurate local names — `report` (parsed jscpd report),
`redup_payload` (each redup export), `artifact` (each
`_load_structured_artifact` result), `plans_payload` (decoded t2c plans
document). The `data` mutation group drops from 6 scopes to 0. Pure rename of
function-internal locals; the generic `data` *parameters* of the pure helpers
`_sum_structured_counts` / `_count_pfix_diagnose_issues` are not mutating
scopes and keep their names; no behavior change. The separate pre-existing
shotgun findings in this file (`path`, `rel`, `found`, `payload`, `files`,
`suggestions`, `priority`, `text`) are untouched by design, and no renamed
local feeds any of those groups (`report`/`redup_payload`/`artifact`/
`plans_payload` each land at <= 2 scopes, threshold is 5).

Tests: every renamed scope is executed through the public
`scan_semcod_quality_artifacts` / module scan entry points by the existing
suites `tests/test_scan_artifacts.py`, `tests/test_scan.py` and
`tests/test_scan_split.py`, which run unchanged as the behavioral proof of
the rename.

Authorization: the operator handoff for PLF-046 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `data` in `src/koru/scan_artifacts.py`, and introduces no new
  smell for that file. Verified with the installed code2llm
  `ProjectAnalyzer.analyze_project(src/koru)` + mutation grouping (package-dir
  analysis; single-file analysis yields empty function scopes and silently
  misses smells): baseline content reports `Mutation of variable 'data' spans
  6 functions` from exactly the six scopes listed above; renamed content
  reports a `data` group of 0 scopes; file mutation count unchanged (247,
  pure rename); no new (file, variable) group reaches the >= 5 threshold;
  every renamed local lands at <= 2 scopes; the separate pre-existing
  findings are unchanged by design.
- [x] AC-02: `python3 -m pytest tests/test_scan_artifacts.py tests/test_scan.py
  tests/test_scan_split.py -q` passes unchanged in the ticket worktree (green
  on base and head); `ruff check src/koru/scan_artifacts.py` reports zero
  errors.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
