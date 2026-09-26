# Ticket 234: Split god module nxdo discovery

- **ID**: ticket-234
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address the code2llm god-module report for
`src/koru/autonomy/nxdo_discovery.py` (550 lines, 4 classes) — planfile
ticket PLF-039.

Split the module by responsibility, moving every function verbatim:

- `src/koru/autonomy/nxdo_config.py` — environment/.env knob lookup
  (`_dotenv_value`, `_config_value`, `_env_flag`, `_env_float`,
  `_env_int`), the enable flag, `nxdo` binary resolution, API-key
  detection, target-repo glob expansion and the default subprocess
  runner (`Runner`, `DEFAULT_TIMEOUT_SECONDS`, `_default_runner`).
- `src/koru/autonomy/nxdo_cooldown.py` — per-repo cooldown stamps, the
  cost-control gate (`DEFAULT_COOLDOWN_SECONDS`, `STAMP_RELPATH`,
  `_load_stamps`/`_save_stamps`, `_select_target_repo`).
- `src/koru/autonomy/nxdo_tickets.py` — TaskPlan parsing, dedupe keys,
  ticket text/scaffold assembly and planfile filing
  (`DEFAULT_SOURCE`, `DEFAULT_MAX_TICKETS`, `_plan_from_output`,
  `_apply_plan_tickets` and helpers).

`src/koru/autonomy/nxdo_discovery.py` keeps only the pipeline
(`NxdoDiscoveryOutcome`, `_Preflight`, the phase helpers introduced by
ticket-224, `run_nxdo_discovery`, `format_nxdo_summary`) and re-exports
the moved names with redundant aliases so every pre-split import —
including the test-facing `_nxdo_executable` patch target and
`_dedupe_key` — keeps working unchanged (the `koru.queue.context`
facade pattern). A patch audit found exactly one facade-level
monkeypatch target (`nd._nxdo_executable`, consumed by `_preflight`,
which stays in the facade) and one cross-module target
(`koru.tasks.create_nl_task`, bound by a function-local import), so
import-time re-exports suffice without call-time indirection.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `nxdo_discovery.py` is reduced to the pipeline facade; the three new responsibility modules hold the moved behavior; every module clears the god-module gate (<500 lines or <4 classes).
- [x] AC-03: Behavior preserved — `tests/test_nxdo_discovery.py` and `tests/test_scan_phase.py` pass unchanged.
- [x] AC-04: Import surface stable — every pre-split public/private name still imports from `koru.autonomy.nxdo_discovery`; the `_nxdo_executable` facade patch target keeps steering `_preflight`; `src/koru/autonomy/phases/scan_phase.py` unmodified.
- [x] AC-05: `tests/test_nxdo_modules.py` (focused tests at the new module homes + facade stability pins) passes and `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-039 planfile handoff instructs
to split the module, keep public imports stable, add focused tests, run
local regression gates and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
