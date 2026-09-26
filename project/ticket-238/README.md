# Ticket 238: consolidate autoloop env overrides into declarative table

- **ID**: ticket-238
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery: args` smell in
`src/koru/autonomy/env.py:221` (mutation of `args` spanning 5 functions) —
planfile ticket PLF-042.

Replace the five per-domain `_apply_*_env` mutators
(`_apply_ticket_and_diagnostics_env`, `_apply_autopilot_env`,
`_apply_scan_env`, `_apply_wup_env`, `_apply_operator_env`) with a single
declarative `_AUTOLOOP_ENV_OVERRIDES` table: 30 frozen
`_EnvOverride(env, dest, coerce, optional)` rows built from four pure
factories (`_keep_flag`, `_keep_value`, `_lower_choice`, `_keep_number`)
plus three bespoke coercions that preserve special semantics verbatim
(`_coerce_ticket_sources` invalid-value warning, `_coerce_idle_diagnostics`
ENABLE_IDLE_DIAGNOSTICS default, `_coerce_wup_watch` None pass-through).
All `args` writes now happen in one setattr loop inside
`apply_autoloop_env_to_args`; `optional=True` rows skip namespaces lacking
the operator extras. Adding an autoloop env knob becomes one table row.

Behavior is preserved: validated before extraction by a 3209-case
differential A/B against the original module (0 mismatches, including the
invalid TICKET_SOURCES warning path, blank envs, clamping and optional
operator fields). The public surface (`env_get`, `env_truthy`,
`parse_boolish`, `AUTOLOOP_ENV_DEFAULTS`, `apply_autoloop_env_to_args`) is
unchanged and no consumer module is touched.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: `tests/test_autonomy_env.py` passes including the new edge guards (blank env, unparseable number, invalid choice fallback, optional operator rows).
- [x] AC-03: The consumer slice (`tests/test_autonomy_environment.py`, `tests/test_autonomous.py`, `tests/test_autonomous_reporting.py`, `tests/test_autonomous_readiness.py`, `tests/test_autonomous_gillm_fallback.py`, `tests/test_doctor.py`, `tests/test_ide_map_consolidation.py`, `tests/test_autonomous_operator.py`, `tests/test_autonomous_operator_reload.py`, `tests/test_autonomous_operator_unsupported_ide.py`, `tests/test_operator_pipeline.py`, `tests/test_autopilot_config.py`) passes unchanged.
- [x] AC-04: `ruff check` and `ruff format --check` report no findings on `src/koru/autonomy/env.py` and `tests/test_autonomy_env.py`.
- [x] AC-05: `bash project/governance-check.sh` reports 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-042 planfile handoff (user message
2026-09-26) instructs to clear the abandoned ticket-235 lane, re-run the
PLF-042 handoff and deliver the already-validated refactor patch.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
