# Ticket 267: Address code smell: shotgun surgery cycle_telemetry in cycle chat activity

- **ID**: ticket-267
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: cycle_telemetry` smell (planfile ticket
PLF-042, dedupe key
`code2llm:smell:shotgun_surgery:src/koru/autonomy/cycle/cycle_chat_activity.py:540`)
in `src/koru/autonomy/cycle/cycle_chat_activity.py`.

Eight functions in the file mutate a parameter named `cycle_telemetry`
(`_upsert_reflection_needs_input_ticket`, `_record_llx_chat_reflection`,
`_apply_needs_input_heuristic`, `_check_recent_drive_ack_skip`,
`_check_chat_intake_skip`, `_check_recent_self_drive_skip`,
`_apply_chat_activity_skip_decision`, `_evaluate_chat_activity_skip`). The
detector groups mutations by (file, variable) and fires at >= 5 scopes — the
shared *name* is the smell; each helper actually writes a disjoint set of
telemetry keys for its own skip decision.

Fix: stage-accurate parameter names for the telemetry view each helper records
— `reflection_needs_input_telemetry`, `llx_reflection_telemetry`,
`needs_input_heuristic_telemetry`, `recent_drive_ack_skip_telemetry`,
`chat_intake_skip_telemetry`, `recent_self_drive_skip_telemetry`,
`chat_activity_skip_telemetry`, `chat_activity_eval_telemetry`. The umbrella
name `cycle_telemetry` stays at the gate entry
(`_skip_due_to_recent_chat_activity`, keyword-called with `cycle_telemetry=`
from `cycle_skip_conditions.py`) and in the two pure pass-through helpers
(`_apply_llx_chat_reflection`, `_gather_chat_activity_context`), which produce
no mutation records. Mutation groups drop from 8 scopes to 0. Pure rename of
parameters and their keyword call sites inside the module; no behavior change.

Tests: every renamed scope is already executed by existing tests that drive
`_check_autopilot_skip_conditions` / the cycle and assert the telemetry keys
flowing through the renamed parameters (redrive cooldown, chat intake,
self-drive skip, reflection policy, needs-input heuristic in
`tests/test_autonomous*.py`, `tests/test_autonomy_policy_*.py`,
`tests/test_decision_*.py`, `tests/test_cycle_orchestrator.py`); those run
unchanged as the behavioral proof of the rename.

Authorization: the operator handoff for PLF-042 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  `src/koru/autonomy/cycle/cycle_chat_activity.py`, and introduces no new
  smell for that file. Verified two ways on a plain /tmp copy of the tree at
  the accepted base SHA: the installed code2llm `DFGExtractor` + real
  detector grouping run standalone (deterministic ground truth) reports the
  `cycle_telemetry` mutation group spanning exactly the 8 ticket-named
  scopes for the original content and nothing (largest group 2) for the
  renamed content, with the file's mutation count unchanged (71) and no new
  shotgun entry; the end-to-end CLI invocation that generated the ticket
  emits the planfile ticket with dedupe key
  `code2llm:smell:shotgun_surgery:src/koru/autonomy/cycle/cycle_chat_activity.py:500`
  on original content and no ticket for that file on renamed content. The
  separate pre-existing findings (`Shotgun Surgery: raw` in
  `cycle_chat_activity_config.py`, `God Function` in
  `cycle_chat_activity_tickets.py`) are untouched (minimal-scope decision).
- [x] AC-02: `python -m pytest tests/test_autonomy_policy_engine.py
  tests/test_autonomous_redrive_cooldown.py
  tests/test_autonomous_cycle_chat_activity_text.py
  tests/test_autonomous_cycle_chat_activity_tickets.py
  tests/test_autonomy_policy_decision.py tests/test_decision_arbiter.py
  tests/test_decision_trace.py tests/test_cycle_orchestrator.py -q` passes
  unchanged in the ticket worktree (134 passed); `ruff check` reports zero
  errors on the touched file. The full `python -m pytest
  tests/test_autonomous.py -q` reports 3 failures (171 passed) that are
  pre-existing on the untouched base, verified by an A/B run of the exact
  three tests on a plain /tmp copy of the base tree with and without the
  renamed file: `uses_heuristic_without_llx` and
  `blocks_self_drive_even_without_ticket_ack` fail on both variants
  (environmental baseline reds on this machine), and
  `heuristic_can_be_disabled` is network-flaky on both variants (3x renamed:
  fail/fail/pass; 3x original: pass/fail/fail) because it does not mock
  `koru.autonomy.planning_llm.reflect_on_chat`, so a live OpenRouter verdict
  decides whether a ticket is created. No outcome correlates with the rename.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
