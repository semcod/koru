# Ticket 301: Fix ruff import sorting in test_autonomous_pre_checks

- **ID**: ticket-301
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Fix unformatted and unsorted import block in `tests/test_autonomous_pre_checks.py` (ruff `I001`).
When `post_run_verify` in `koru.yaml` runs `.venv/bin/python -m ruff check src tests`, this unformatted import caused verify failures and prompted autonomous cycle finalize to report `verify_failed:reopened`, preventing clean ticket closure.

## Acceptance criteria

- [x] AC-01: `ruff check tests/test_autonomous_pre_checks.py` reports zero errors.
- [x] AC-02: `pytest tests/test_autonomous_pre_checks.py` passes all tests cleanly.
- [x] AC-03: `./project/governance-check.sh` reports GOV-PASS with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
