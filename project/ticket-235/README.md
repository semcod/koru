# Ticket 235: Split god module todo2code_discovery by responsibility

- **ID**: ticket-235
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address the code2llm god-module report for
`src/koru/autonomy/todo2code_discovery.py` (846 lines, 5 classes; over the
function-count gate) — planfile ticket PLF-039.

Split the module by responsibility, moving every function verbatim:

- `src/koru/autonomy/todo2code_config.py` — environment/.env knob lookup
  (`_env_flag`, `_env_float`, `_env_int`, `_config_value` re-export), the
  enable flag, output-dir containment and discovery limit resolution
  (`DEFAULT_SOURCE`, `DEFAULT_OUT_SUBDIR`, `DEFAULT_MAX_TICKETS`,
  `DEFAULT_STALE_MINUTES`, `DEFAULT_TIMEOUT_SECONDS`,
  `DEFAULT_MIN_USEFULNESS`, `todo2code_enabled`, `_out_dir`,
  `_discovery_limits`).
- `src/koru/autonomy/todo2code_plans.py` — plan artifact discovery and
  plan-field normalization (`PLANS_FILENAME`, `find_latest_plans_path`,
  `_plans_fresh`, `_load_plan_set`, `_string_list`, `_truncate`,
  `_plan_paths`, `_plan_dedupe_key`, `_slug`).
- `src/koru/autonomy/todo2code_tickets.py` — sprint dedupe identities,
  ticket text/scaffold assembly, usefulness ranking and planfile filing
  (`_PRIORITY_MAP`, `_ExistingPlanTickets`, `_existing_todo2code_keys`,
  `_ticket_text`, `_ticket_scaffold`, `_RankedPlans`, `_PlanIdentity`,
  `_PlanDispatch`, `_apply_plan_tickets` and helpers).

`src/koru/autonomy/todo2code_discovery.py` keeps only the pipeline
(`Todo2codeDiscoveryOutcome`, `Runner`, `_default_runner`,
`_run_t2c_pipeline`, `_consume_plan_set`, `run_todo2code_discovery`,
`format_todo2code_summary`) and re-exports the moved names with redundant
aliases so every pre-split import — including the test-facing
`_t2c_executable` patch target, `scan.py`'s `_PRIORITY_MAP` /
`_plan_dedupe_key` and `code_change_autonomy.py`'s `_config_value` /
`_out_dir` — keeps working unchanged (the `nxdo_discovery` facade
pattern). A patch audit found one facade-level monkeypatch target
(`td._t2c_executable`, consumed by `run_todo2code_discovery`, which stays
in the facade) and one cross-module target (`koru.tasks.create_nl_task`,
bound by a function-local import in `_dispatch_plan_task`), so
import-time re-exports suffice without call-time indirection.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `todo2code_discovery.py` is reduced to the pipeline facade; the three new responsibility modules hold the moved behavior; every module clears the god-module gate (≤40 functions, ≤10 classes).
- [x] AC-03: Behavior preserved — `tests/test_todo2code_discovery.py`, `tests/test_todo2code_dedupe.py`, `tests/test_todo2code_plan_ranking.py` and `tests/test_todo2code_ticket_text.py` pass unchanged.
- [x] AC-04: Import surface stable — every pre-split public/private name still imports from `koru.autonomy.todo2code_discovery`; the `_t2c_executable` facade patch target keeps steering the pipeline; `src/koru/scan.py`, `src/koru/autonomy/code_change_autonomy.py`, `src/koru/autonomy/phases/scan_phase.py` and `src/koru/ide_doctor_cli.py` unmodified.
- [x] AC-05: `tests/test_todo2code_modules.py` (focused tests at the new module homes + facade stability pins) passes and `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-039 planfile handoff instructs
to split the module, keep public imports stable, add focused tests, run
local regression gates and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
