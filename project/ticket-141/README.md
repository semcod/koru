# Ticket 141: Scope fleet standard scans and expose excluded repository inventory

- **ID**: ticket-141
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user approved adding an organization
filter and a separate way to show excluded local clones and worktrees.

Make the Wellmanifest fleet scan safe for a multi-repository workspace by
selecting only primary checkouts from the configured fleet organizations by
default. Checkouts without an origin, linked worktrees, duplicate clones and
other organizations remain visible through a read-only inventory command, but
cannot generate adoption tickets unless explicit inclusion flags are passed.
The scanner must not mutate any adopter repository.

## Acceptance criteria

- [x] AC-01: The user's explicit request approves the bounded scope.
- [x] AC-02: The default scan selects only `autogrammar`, `semcod`,
      `subactor` and `wellmanifest` primary checkouts.
- [x] AC-03: Local-only checkouts, linked worktrees, duplicate clones and
      other organizations are excluded from ticket candidates and remain
      available in the inventory report.
- [x] AC-04: `koru fleet standard-inventory` is read-only; explicit inclusion
      flags are required before excluded paths can be ticket candidates.
- [x] AC-05: Focused tests, full deterministic tests, Ruff, compilation and
      governance validation pass.

## Validation evidence

- `27 passed` in `tests/test_standard_fleet.py tests/test_cli_fleet.py`.
- `4163 passed, 19 skipped, 165 deselected, 977 subtests passed` in the full
  deterministic suite (`pytest -m 'not slow'`).
- `./project/governance-check.sh --base origin/main --head HEAD --actor agent`:
  `GOV-PASS: passed (0 errors, 0 warnings)`.
- Ruff, Python compilation, `git diff --check` and CLI help pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
