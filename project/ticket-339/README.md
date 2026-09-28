# Ticket 339: CI: do not report verified success when zero checks ran

- **ID**: ticket-339
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: resolve issue #560: do not report verified success when zero checks ran. Distinguish no checks/not verified from passed; completion and publication consumers must reject empty evidence; report skipped gate coverage in text and JSON while preserving nonzero command failures and timeouts.

## Acceptance criteria

- [x] AC-01: When zero checks run (empty policy ci.command and gates skipped), run_local_ci reports overall_status='not_verified' with explicit skipped stages, and CLI exits non-zero.
- [x] AC-02: Quality gate skip coverage is reported in stages; publication/work completion rejects unverified CI; test suite and governance pass.

## Scope limit

Changes confined to CI runner, publication validation, work lifecycle verification, and CI pipeline unit tests.

## Validation

- 28 unit tests in `tests/test_ci_pipeline.py` and `tests/test_work_lifecycle.py` pass.
- Ruff checks on all modified files pass.
- Managed governance check passes cleanly.
