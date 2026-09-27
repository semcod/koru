# Ticket 268: Shotgun surgery cycle_telemetry in scan phase

- **ID**: ticket-268
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: cycle_telemetry` smell (planfile ticket
PLF-043, dedupe key
`code2llm:smell:shotgun_surgery:src/koru/autonomy/phases/scan_phase.py:595`)
in `src/koru/autonomy/phases/scan_phase.py`.

Nine functions in the file mutate a parameter named `cycle_telemetry`
(`_skip_scan_after_idle_for_rate_limit`,
`_skip_scan_after_idle_for_create_failed_cooldown`,
`_skip_scan_after_idle_for_duplicate_cooldown`,
`_record_scan_after_idle_result`, `_record_code2llm_discovery_telemetry`,
`_record_monag_discovery_telemetry`, `_record_nxdo_discovery_telemetry`,
`_record_todo2code_discovery_telemetry`,
`_record_code_change_autonomy_telemetry`). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each helper actually writes a disjoint set of telemetry keys for its own
scan/idle stage.

Fix: stage-accurate parameter names for the telemetry view each helper records
— `rate_limit_skip_telemetry`, `create_failed_cooldown_skip_telemetry`,
`duplicate_cooldown_skip_telemetry`, `idle_scan_result_telemetry`,
`code2llm_discovery_telemetry`, `monag_discovery_telemetry`,
`nxdo_discovery_telemetry`, `todo2code_discovery_telemetry`,
`code_change_autonomy_telemetry`. The umbrella name `cycle_telemetry` stays in
the four non-mutating pass-through scopes (`handle_backlog_promotion_after_idle`,
`handle_scan_after_idle`, `_run_idle_discovery_fallbacks`,
`_run_scan_after_idle`), which produce no mutation records and where it
genuinely names the cycle-wide dict. Mutation group drops from 9 scopes to 0.
Pure rename of parameters and their in-module call references; every call site
is positional; no behavior change. Same accepted pattern as ticket-266
(PLF-041) for the identical smell in `cycle_skip_conditions.py`.

Tests: every renamed scope is already executed by existing tests that call
`handle_scan_after_idle` / `handle_backlog_promotion_after_idle` /
`_skip_scan_after_idle_for_duplicate_cooldown` / `_run_scan_after_idle` and
assert the telemetry keys flowing through the renamed parameters
(`tests/test_scan_phase.py`, `tests/test_cycle_backlog_promotion.py`,
`tests/test_autonomous.py`); those run unchanged as the behavioral proof of
the rename.

Authorization: the operator handoff for PLF-043 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  `src/koru/autonomy/phases/scan_phase.py`, and introduces no new smell for
  that file. Verified with the installed code2llm `DFGExtractor` +
  `SmellDetector._detect_shotgun_surgery` run standalone (deterministic ground
  truth) on plain /tmp copies: original content fires the smell with exactly
  the 9 reported scopes, renamed content fires nothing for the file while
  recording the same mutations and no new shotgun entry.
- [x] AC-02: `pytest tests/test_scan_phase.py tests/test_cycle_backlog_promotion.py`
  and the `tests/test_autonomous.py` selection covering the scan-after-idle /
  backlog-promotion scopes pass in the ticket worktree; `ruff check` reports
  zero errors on the touched file.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
