# Ticket 297: add-service-contract-tests-for-local-manager-and-remote-clients

- **ID**: ticket-297
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Add comprehensive service contract and unit test coverage for previously unverified service client modules in `semcod/koru`:
- `src/koru/local_manager_client.py`: `LocalManagerClient` and `LocalManagerSession` environment discovery, request serialization, error/timeout handling, registration, claim, heartbeat, and completion lifecycle.
- `src/koru/remote/client.py`: `KoruRemoteClient` URL building (HTTP/HTTPS), request dispatch, HTTP 4xx/5xx structured and fallback error handling, connection failures, log retrieval, drive commands, and IDE/plugin listing helpers.

## Acceptance criteria

- [x] AC-01: Service contract unit tests in `tests/test_local_manager_client_contract.py` and `tests/test_remote_client_contract.py` pass 100%.
- [x] AC-02: `./project/governance-check.sh` reports GOV-PASS with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
