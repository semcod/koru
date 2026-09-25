# Ticket 216: Decompose god function compile_inert_plan

- **ID**: ticket-216
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: compile_inert_plan` in
`src/koru/poa/plan_compile.py:32` (PLF-034, CC=10 / fan-out=18 /
mutations=23).

Split `compile_inert_plan` into focused module-level helpers that
communicate through small NamedTuples: `_validate_planning_inputs`
(document/policy-boundary/TTL validation, returning `_ValidatedInputs`),
`_require_validity_window` (snapshot interval enforcement), `_request_hash`
(canonical plan-request hash), `_compile_planned_steps` over `_planned_step`,
`_compensation_process_uri` and `_binding_evidence` (returning
`_PlannedCompilation`), `_build_plan` (hash-pinned `poa.plan/v1`, returning
`_CompiledPlan`) and `_planning_result` (planning-result document). The
compiled planning result stays value-identical: same validation order and
error messages, same key sets, same idempotency-key/plan_id derivation, and
the module's public API is unchanged.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-034 queue handoff;
  SESSION_EXECUTION_AUTHORIZATION from the same request).
- [x] AC-02: `compile_inert_plan` and every new helper fall under the
  god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6).
- [x] AC-03: `pytest -q tests/test_poa_registry.py tests/test_poa_logs.py`
  passes unchanged (pure extraction, no behavior change).
- [x] AC-04: code2llm analysis of the module reports no metric change for any
  pre-existing function; the only remaining above-threshold functions are the
  pre-existing, separately ticketed `verify_planning_result` and
  `_select_bindings` (untouched).
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation evidence (2026-09-26)

- AC-02/AC-04: code2llm ProjectAnalyzer/SmellDetector probe on `src/koru/poa`:
  `compile_inert_plan` CC=1 / fan-out=8 / mutations=5 (was CC=10 / fan-out=18 /
  mutations=23); new helpers `_validate_planning_inputs` 7/9/4 (CC/fan/mut),
  `_require_validity_window` 2/2/3, `_request_hash` 1/2/1,
  `_compile_planned_steps` 2/5/2, `_planned_step` 2/5/4,
  `_compensation_process_uri` 2/2/2, `_binding_evidence` 1/1/1,
  `_build_plan` 1/4/3, `_planning_result` 1/1/1; pre-existing
  `verify_planning_result` 13/10/5, `_select_bindings` 11/9/10,
  `_validate_process_graph` 7/10/4 and `_require_process_uri_kind` 2/1/1 all
  identical to the pre-change baseline.
