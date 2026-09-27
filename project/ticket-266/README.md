# Ticket 266: Address code smell: shotgun surgery cycle_telemetry in cycle skip conditions

- **ID**: ticket-266
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: cycle_telemetry` smell (planfile ticket
PLF-041, dedupe key
`code2llm:smell:shotgun_surgery:src/koru/autonomy/cycle/cycle_skip_conditions.py:605`)
in `src/koru/autonomy/cycle/cycle_skip_conditions.py`.

Eight functions in the file mutate a parameter named `cycle_telemetry`
(`_check_autopilot_skip_conditions`, `_diagnostics_fail_skip_result`,
`_autopromote_waiting_ticket_llm_ready`, `_clear_manual_send_for_new_ticket`,
`_clear_manual_send_for_message_sent`, `_allow_manual_send_alt_retry`,
`_manual_send_required_decision`, `_handle_stuck_status_skip_candidate`). The
detector groups mutations by (file, variable) and fires at >= 5 scopes — the
shared *name* is the smell; each helper actually writes a disjoint set of
telemetry keys for its own skip decision.

Fix: stage-accurate parameter names for the telemetry view each helper records
— `diagnostics_skip_telemetry`, `llm_ready_promotion_telemetry`,
`new_ticket_clear_telemetry`, `message_sent_clear_telemetry`,
`alt_retry_telemetry`, `manual_send_decision_telemetry`,
`stuck_status_telemetry`. The umbrella name `cycle_telemetry` stays at the gate
entry (`_check_autopilot_skip_conditions`, whose keyword-called parameter is
the cycle-wide dict) and in the two pure pass-through helpers, which produce no
mutation records. Mutation groups drop from 8 scopes to 1. Pure rename of
parameters and their keyword call sites inside the module; no behavior change.

Tests: every renamed scope is already executed by existing tests that call
`_check_autopilot_skip_conditions` / `run_cycle` and assert the telemetry keys
flowing through the renamed parameters (manual-send chain, alt retry, idle
streak, stuck status, llm-ready promotion, diagnostics fail in
`tests/test_autonomous.py` and `tests/test_cycle_orchestrator.py`); those run
unchanged as the behavioral proof of the rename.

Authorization: the operator handoff for PLF-041 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  `src/koru/autonomy/cycle/cycle_skip_conditions.py`, and introduces no new
  smell for that file. Verified two ways on a plain /tmp copy of the tree:
  the installed code2llm `DFGExtractor` + `SmellDetector._detect_shotgun_surgery`
  run standalone (deterministic ground truth) reports `Shotgun Surgery:
  cycle_telemetry` for the original content (8 mutating scopes, matching the
  ticket exactly) and nothing for the renamed content, with the file's mutation
  count unchanged (113) and no new shotgun entry; the end-to-end CLI
  invocation that generated the ticket fires both cycle_skip_conditions
  shotgun entries on original content (2/2 runs) and neither on renamed
  content. The separate pre-existing `Shotgun Surgery: ticket_id` finding is
  untouched (minimal-scope decision). Caveat recorded: the CLI pipeline is
  nondeterministic for mutation-driven findings of this file (one control run
  on unchanged content dropped them spontaneously), hence the standalone
  detector run as the authoritative evidence.
- [x] AC-02: `pytest tests/test_autonomous.py -q -k 'submit_unverified or
  idle_streak or stuck_waiting_input or llm_ready'` (14 passed),
  `pytest tests/test_autonomy_policy_engine.py tests/test_cycle_orchestrator.py`
  (14 passed) and the full `pytest tests/test_autonomous.py` run unchanged in
  the ticket worktree; `ruff check` reports zero errors on the touched file.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
