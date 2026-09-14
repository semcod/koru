# Ticket 129: Report Koru doctor dependency and virtualenv drift to Planfile

- **ID**: ticket-129
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

Implement the requested transparent dependency and environment drift diagnostics in Koru.
SESSION_EXECUTION_AUTHORIZATION: the user asked to continue the autonomous delivery
flow after the preceding protected merges.

## Acceptance criteria

- [x] AC-01: Detect competing project virtual environments.
- [x] AC-02: Provide a read-only opt-in uv lock freshness check.
- [x] AC-03: Create deduplicated, synchronized Planfile diagnostic tickets.

## Validation evidence

- `80 passed in 320.55s` for `tests/test_doctor.py` and
  `tests/test_doctor_dependency_diagnostics.py` with the governance pytest
  plugin and repository `addopts` disabled only for test selection.
- Ruff and `git diff --check` pass for the changed implementation and tests.
- `./project/governance-check.sh --base ff48c97d1481c73e1e75abdec31168d1982d6e3d --head HEAD --actor agent`
  passes with `0 errors, 0 warnings`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
