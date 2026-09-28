# Ticket 353: fix execution plan import sorting and format cleanliness

- **ID**: ticket-353
- **Owner**: agent:Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION ("wykonaj i przetestuj, scal, popraw")

## Goal and scope

Fix import sorting, unused imports, and format cleanliness in `src/koru/autonomy/execution_plan.py` and `src/koru/autonomy/execution_plan_selection.py`:
1. Move `_select_profile` definition after all module import statements to satisfy E402.
2. Remove unused imports and format import blocks according to Ruff conventions (I001).
3. Ensure hermetic tests in `tests/test_execution_plan*.py` pass and `ruff check src/koru/` passes clean.

## Acceptance criteria

- [x] AC-01: Ruff check passes with 0 errors across `src/koru/`.
- [x] AC-02: Unit tests in `tests/test_execution_plan*.py` pass green.
- [x] AC-03: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
