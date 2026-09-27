# Ticket 312: Decompose provenance_from_result in evidence to reduce cyclomatic complexity

- **ID**: ticket-312
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Refactor `provenance_from_result` (CC=18) in `src/koru/queue/evidence.py` to reduce its Cyclomatic Complexity down to <=5.

1. Extract `_provenance_git_metadata`.
2. Extract `_provenance_artifact_records`.
3. Extract `_provenance_execution_metadata`.
4. Retain 100% backward compatibility and test coverage.

## Acceptance criteria

- [x] AC-01: All tests in `tests/test_queue_evidence.py` pass cleanly.
- [x] AC-02: Cyclomatic complexity of `provenance_from_result` drops to <=5.
- [x] AC-03: Ruff reports zero lint/formatting errors.
- [x] AC-04: `./project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
