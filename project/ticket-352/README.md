# Ticket 352: refactor build context using context builder

- **ID**: ticket-352
- **Owner**: agent:Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION ("wykonaj i przetestuj, scal, popraw")

## Goal and scope

Refactor `build_context` in `src/koru/context.py` to decompose cyclomatic complexity and resolve PLF-031 / GitHub #525:
1. Introduce `ContextBuilder` coordinator class that handles project loading, ticket state collection, environment probe execution, and brief assembly.
2. Keep `build_context` as a clean facade calling `ContextBuilder`, preserving 100% parameter compatibility and hermetic test mock injection.
3. Verify all hermetic tests in `tests/test_context*.py` pass.

## Acceptance criteria

- [x] AC-01: `build_context` delegates to `ContextBuilder`.
- [x] AC-02: Unit tests in `tests/test_context*.py` pass green (45 passed).
- [x] AC-03: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
