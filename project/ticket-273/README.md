# Ticket 273: Address code smell: shotgun surgery data locals in autopilot install manager

- **ID**: ticket-273
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-048,
reported for `src/koru/autopilot/install_manager.py:163`) in
`src/koru/autopilot/install_manager.py`.

Six functions in the file mutate a local named `data`
(`_source_version`, `_is_koru_source_root`, `_installed_editable_source_root`,
`_expected_plugin_version`, `_expected_plugin_build_sha`,
`format_install_manager_report`). The detector groups mutations by (file,
variable) and fires at >= 5 scopes — the shared *name* is the smell; each
function actually holds an independent decoded document (a parsed
`pyproject.toml` TOML table, a parsed `direct_url.json`, a parsed plugin
`package.json`, or the report serialized through `InstallManagerReport.to_dict`).

Fix: stage-accurate local names — `pyproject` (parsed `pyproject.toml` TOML,
in `_source_version` and `_is_koru_source_root`), `direct_url` (parsed
`direct_url.json` editable-install metadata), `package_manifest` (parsed
plugin `package.json`, in `_expected_plugin_version` and
`_expected_plugin_build_sha`), `report_dict` (the report's `to_dict()`
serialization, also renaming the `data` parameter of
`_install_manager_base_lines` that receives it). The `data` mutation group
drops from 6 scopes to 0. Pure rename of function-internal locals and one
private helper parameter; no signature, return shape or behavior change; no
other file is touched.

Tests: the module's dedicated suite `tests/test_install_manager.py` exercises
the renamed paths end-to-end and runs unchanged as the behavioral proof of the
pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `data` in `src/koru/autopilot/install_manager.py`, and
  introduces no new smell for that file. Verified with the installed code2llm
  `DFGExtractor` mutation grouping on the file AST (standalone extract;
  `ProjectAnalyzer.analyze` on copies/worktrees silently yields empty
  scopes): baseline content reports `Mutation of variable 'data' spans
  6 functions` from exactly the six scopes listed above; renamed content
  reports a `data` group of 0 scopes; file mutation record count unchanged
  (185, pure rename); every renamed local lands at <= 2 scopes, far below
  the >= 5 threshold.
- [x] AC-02: `python3 -m pytest tests/test_install_manager.py -q` passes
  unchanged in the ticket worktree; `ruff check
  src/koru/autopilot/install_manager.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
