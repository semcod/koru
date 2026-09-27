# Ticket 290: fix-test-init-autonomy-strategy-expectation

- **ID**: ticket-290
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Update `test_writes_koru_yaml_on_first_init` in `tests/test_init.py` to assert `in_flight_first` as the default autonomy strategy, aligning with the default introduced in ticket-258.

## Acceptance criteria

- [x] AC-01: Update `tests/test_init.py` line 169 to expect `"in_flight_first"`.
- [x] AC-02: Pytest on `tests/test_init.py` passes 29/29 tests.
- [x] AC-03: Governance checks pass (GOV-PASS).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
