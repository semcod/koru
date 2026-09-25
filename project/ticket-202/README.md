# Ticket 202: Reduce cyclomatic complexity in select task model

- **ID**: ticket-202
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Reduce cyclomatic complexity: `src.koru.task_model_policy.select_task_model` (CC=38, limit 15) at
`src/koru/task_model_policy.py:24` (PLF-021).

Extract focused helpers for explicit/pinned model resolution, routing mapping resolution,
target file validation, labels validation, ruff codes validation, and bounded lint-fix check.
Preserve exact model selection semantics and reasons.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-021 queue handoff).
- [x] AC-02: `select_task_model` and all new helpers have CC <= 6 (Rank A).
- [x] AC-03: Existing task model policy tests pass unchanged (`pytest -q tests/test_task_model_policy.py`).
- [x] AC-04: Governance check passes with 0 errors (`bash project/governance-check.sh`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Result (measured 2026-09-25)

- `select_task_model` CC 38 → 3 (radon Rank A); all new helpers CC ≤ 6.
- Helpers return `NamedTuple` (never unpacked tuples) so code2llm's mutation
  counter does not double-count unpack targets; `select_task_model` mutations 12 → 3.
- code2llm re-run: `code2llm:cc:...select_task_model` finding gone; no new
  smell findings for this file (pre-existing `drive_with_model_policy` smell
  unchanged and out of scope).
- `pytest tests/test_task_model_policy.py tests/test_autonomous_cycle_drive_retry.py
  tests/test_model_history.py tests/test_queue_runners.py` → 52 passed.
- `project/governance-check.sh` → GOV-PASS (0 errors, 0 warnings).
