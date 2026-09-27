# Ticket 289: Add smoke tests for wizard API endpoints

- **ID**: ticket-289
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-27

## Goal and scope

Add dedicated smoke tests covering all /wizard HTTP and API endpoints:
- GET /wizard
- GET /wizard/api/state
- POST /wizard/api/ide
- POST /wizard/api/project
- POST /wizard/api/strategy
- POST /wizard/api/confirm
- POST /wizard/done
- Static assets and CSRF security verification

## Acceptance criteria

- [x] AC-01: All unit tests in `tests/test_wizard_api_smoke.py` pass 100%.
- [x] AC-02: `./project/governance-check.sh` reports GOV-PASS with 0 errors and 0 warnings.
