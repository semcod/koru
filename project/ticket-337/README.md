# Ticket 337: feat(autonomy): docker sandbox and cdp browser adapters for process uri

- **ID**: ticket-337
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

SESSION_EXECUTION_AUTHORIZATION: User requested implementation of Docker Sandbox and
CDP browser adapters for Process URI, enabling autonomous execution of arbitrary
Python packages / Git repos in isolated containers and headless browser automation.

## Goal and scope

1. Implement `DockerSandboxRunner` in `src/koru/autonomy/docker_sandbox.py`:
   - Supports `sandbox://run` and `pypi://<package>/<command>` execution.
   - Creates disposable, resource-bounded Docker containers with volume mounting.
   - Provides dry-run / inspect mode and execution result reporting.
2. Implement `CdpBrowserController` in `src/koru/autonomy/cdp_browser.py`:
   - Supports `browser://navigate`, `browser://click`, `browser://screenshot`, `browser://evaluate`.
   - Sends standard Chrome DevTools Protocol commands via JSON-RPC / WebSocket.
   - Provides mock / safe-fallback mode when headless browser is unlaunched.
3. Unit test coverage:
   - `tests/test_docker_sandbox.py`: sandbox command generation, isolation options, volume bind, timeout.
   - `tests/test_cdp_browser.py`: CDP protocol frames, browser URI routing, payload validation.

## Acceptance criteria

- [ ] AC-01: `DockerSandboxRunner` builds secure, non-privileged container commands and isolates runs.
- [ ] AC-02: `CdpBrowserController` translates action URIs to CDP protocol commands with result packaging.
- [ ] AC-03: All unit tests pass 100% and `governance-check.sh` reports `GOV-PASS`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
