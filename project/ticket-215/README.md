# Ticket 215: Decompose god function compile_execution_plan

- **ID**: ticket-215
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: `God Function: compile_execution_plan` in
`src/koru/autonomy/execution_plan.py:353` (PLF-033, CC=13 / fan-out=18 /
mutations=20).

Split `compile_execution_plan` into focused module-level helpers that
communicate through small NamedTuples: `_collect_plan_signals` (signal payload
plus the open refactor tickets), `_pipeline_order` (strategy pipeline order
parsing), `_select_plan_work` / `_discovery_selection` / `_discovery_steps`
(queue-vs-discovery phase selection) and `_plan_summary` (summary rendering).
The compiled `ExecutionPlan` stays value-identical: signal key order, phase
precedence (first open ticket, else first discovery phase in pipeline order,
else idle), summary strings and the function-local `resolve_work_llm_context`
import used by test monkeypatching are all preserved.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-033 queue handoff;
  SESSION_EXECUTION_AUTHORIZATION from the same request).
- [x] AC-02: `compile_execution_plan` and every new helper fall under the
  god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6).
- [x] AC-03: `pytest -q tests/test_execution_plan.py
  tests/test_execution_profile_matching.py tests/test_queued_execution_steps.py`
  passes, including new regression tests for the discovery and idle branches
  that had no direct coverage before.
- [x] AC-04: code2llm analysis of the changed file reports no metric change for
  any pre-existing function; the only remaining above-threshold functions are
  the pre-existing, separately ticketed `_queued_ticket_steps`,
  `_ticket_matches_profile` and `_workflow_steps` (untouched).
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation evidence (2026-09-26)

- AC-02/AC-04: code2llm ProjectAnalyzer/SmellDetector probe on the changed
  file: `compile_execution_plan` CC=3 / fan-out=8 / mutations=4 (was CC=13 /
  fan-out=18 / mutations=20); new helpers `_collect_plan_signals` CC=2/8/2,
  `_pipeline_order` CC=3/3/2, `_select_plan_work` CC=2/4/2, `_discovery_selection`
  CC=3/3/1, `_discovery_steps` CC=3/3/4, `_plan_summary` CC=3/1/3. Per-function
  metrics of every pre-existing function in the module are unchanged. Remaining
  above-threshold functions are the pre-existing, separately ticketed
  `_queued_ticket_steps`, `_ticket_matches_profile` and `_workflow_steps`.
- AC-03: `pytest -q tests/test_execution_plan.py
  tests/test_execution_profile_matching.py tests/test_queued_execution_steps.py`
  → 39 passed, including the 2 new discovery/idle branch tests. Full suite:
  4476 passed, 25 failed — all 25 in planfile-transport / scan-runtime /
  ticket-queue files that do not import `koru.autonomy.execution_plan`
  (transitively verified via `sys.modules`), matching the known environmental
  reds.
- AC-05: `bash project/governance-check.sh` → GOV-PASS (0 errors).
- Rebased onto `origin/main` (9ea111ee) after tickets 212/213/214 merged;
  `delivery.acceptedBaseSha` re-pinned to the post-rebase base.
