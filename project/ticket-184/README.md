# Ticket 184: Split standard_fleet god module into focused submodules

- **ID**: ticket-184
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the queue owner instructed continuing the
STARTER-603 implementation work autonomously (planfile ticket `Split god
module: src/koru/standard_fleet.py`, code2llm god-module signal).

`project/analysis.toon.yaml` flags `src/koru/standard_fleet.py` as a god
module (574 lines, 6 classes, 25 functions). Split it into focused submodules
by responsibility behind an unchanged public facade so `cli_fleet.py` and the
existing tests keep working without modification.

## Acceptance criteria

- [x] AC-01: Every former `__all__` name remains importable from
      `koru.standard_fleet` through the package facade.
- [x] AC-02: `tests/test_standard_fleet.py` and `tests/test_cli_fleet.py`
      pass unmodified (including the `koru.standard_fleet.scan_standard_fleet`
      monkeypatch targets).
- [x] AC-03: Ruff check and format pass on the new package.
- [x] AC-04: `./project/governance-check.sh --base origin/main` passes with
      zero errors.

## Validation evidence

- Focused suites: `27 passed` in
  `tests/test_standard_fleet.py tests/test_cli_fleet.py` (PYTHONPATH=src).
- Ruff: `All checks passed!`, all files already formatted.
- Governance gate: `GOV-PASS: passed (0 errors, 0 warnings)`.
- Non-slow suite: `4359 passed, 19 skipped, 165 deselected, 976 subtests
  passed`; the 4 `test_cli.py` failures reproduce on pristine origin/main.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
