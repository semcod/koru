# Ticket 457: Fix ruff lint violations across src/koru and tests to restore CI smoke and main gates

- **ID**: ticket-457
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: User authorized fixing ruff lint violations in `semcod/koru` to restore CI gates.

## Goal and scope

1. Fix all `ruff check src tests` violations across `src/koru/queue/**`, `src/koru/scan_artifacts.py`, and `tests/**` (`E501`, `E402`, `E731`, `E741`, `B010`, `B905`, `UP017`, `I001`) without altering runtime semantics.

## Acceptance criteria

- [x] AC-01: `python3 -m ruff check src tests` exits `0` with `All checks passed!` and unit tests pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
