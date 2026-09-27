# Ticket 277: Address code smell: shotgun surgery errors locals in koruide command scenario

- **ID**: ticket-277
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: errors` smell (planfile ticket PLF-052,
reported for `packages/koruide/src/koruide/command_scenario.py:269`) in
`packages/koruide/src/koruide/command_scenario.py`.

Seven functions in the file mutate a list local named `errors`
(`_validate_step`, `_validate_step_kind`, `_validate_step_command`,
`_validate_step_risk`, `_validate_mode`, `_scenario_ide_and_steps`,
`_validate_scenario_steps`; reproduced with the installed code2llm
`DFGExtractor` mutation grouping on the file AST: 9 mutation records — every
one an `.append`/`.extend` on `errors`). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each function actually contributes its own validation stage's findings to the
same accumulated report (per-step findings, action-kind findings,
missing-command findings, risk-policy findings, mode findings, scenario-header
findings, and the per-step aggregation into the scenario report).

Fix: stage-accurate names for each stage's error channel — `step_errors`
(`_validate_step`, the per-step accumulator; matches the caller's existing
unpack), `action_errors` (`_validate_step_kind`), `command_errors`
(`_validate_step_command`), `risk_errors` (`_validate_step_risk`),
`mode_errors` (`_validate_mode`), `header_errors` (`_scenario_ide_and_steps`,
the ide/steps-presence header checks), `scenario_errors`
(`_validate_scenario_steps`, which aggregates step findings into the scenario
report) and `scenario_errors` for the `errors` local of the public
`validate_ide_command_scenario` entry point, whose `errors` local is that same
scenario-level accumulator (renamed for coherence; it carries no method
mutation itself). The `errors` mutation group drops from 7 scopes to 0. Pure
rename of function-internal locals and sink parameters; no signature, return
shape, dataclass field (`ScenarioValidation.errors`) or behavior change; no
other file is touched.

Tests: the suites that exercise the renamed validation paths
(`tests/test_ide_command_catalog.py` — direct
`validate_ide_command_scenario` coverage — plus `tests/test_strategy_prompt.py`,
`tests/test_mcp_server.py`, `tests/test_mcp_server_split.py`, which import the
module through koruapi) run unchanged as the behavioral proof of the pure
rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `errors` in `packages/koruide/src/koruide/command_scenario.py`,
  and introduces no new (file, variable) mutation group at or beyond the
  threshold. Verified with the installed code2llm `DFGExtractor` mutation
  grouping on the file AST (standalone extract; `ProjectAnalyzer.analyze` on
  copies/worktrees silently yields empty scopes): baseline content reports
  `Mutation of variable 'errors' spans 7 functions` from exactly the seven
  scopes listed above (9 mutation records); renamed content reports an
  `errors` group of 0 scopes; file mutation record count unchanged (47, pure
  rename); every renamed local lands at 1-2 scopes (the largest, `step_errors`,
  covers its `.append`s in `_validate_step` plus the extractor's
  double-counted tuple-unpack binding at the caller in
  `_validate_scenario_steps`) — all far below the >= 5 threshold. The
  pre-existing `warnings` group (5 scopes) is untouched — it is a separate
  finding outside this ticket's scope.
- [x] AC-02: `python3 -m pytest tests/test_ide_command_catalog.py
  tests/test_strategy_prompt.py tests/test_mcp_server.py
  tests/test_mcp_server_split.py -q` passes unchanged in the ticket worktree;
  `ruff check packages/koruide/src/koruide/command_scenario.py` reports zero
  errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
