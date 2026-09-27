# Ticket 270: Address code smell: shotgun surgery data locals in opencode terminals

- **ID**: ticket-270
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-045,
dedupe key
`code2llm:smell:shotgun_surgery:src/koruapi/opencode_terminals.py:458:Shotgun
Surgery: data`) in `src/koruapi/opencode_terminals.py`.

Nine functions in the file mutate a local named `data` (`load_registry`,
`_api_request`, `instance_health`, `list_sessions`, `list_providers`,
`get_instance_config`, `create_session`, `session_messages`,
`pending_requests`). The detector groups mutations by (file, variable) and
fires at >= 5 scopes — the shared *name* is the smell; each function actually
holds an independent payload (parsed registry file, encoded outbound request
bytes, health probe, or one endpoint's decoded response).

Fix: stage-accurate local names — `registry_entries`, `request_body`,
`health`, `session_payload`, `catalog_payload` (matching the provider-catalog
docstring), `config_payload`, `creation_payload`, `message_payload`,
`request_payload`. The `data` mutation group drops from 9 scopes to 0. Pure
rename of function-internal locals; the urllib `Request(data=...)` keyword and
the JSON envelope key `"data"` keep their names; no behavior change. The four
separate pre-existing shotgun findings in the file (`entry`, `url`, `out`,
`text`) are untouched by design.

Tests: every renamed scope is executed through the public functions by the
existing suites `tests/test_dashboard_terminals.py` and
`tests/test_opencode_serve_scan.py`, which run unchanged as the behavioral
proof of the rename.

Authorization: the operator handoff for PLF-045 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `data` in `src/koruapi/opencode_terminals.py`, and introduces
  no new smell for that file. Verified with the installed code2llm
  `ProjectAnalyzer.analyze_project(src/koruapi)` +
  `SmellDetector._detect_shotgun_surgery` (package-dir analysis; single-file
  analysis yields empty function scopes and silently misses smells):
  baseline content reports `Shotgun Surgery: data` at line 458 — matching the
  ticket's file, line and dedupe key exactly — from 9 mutating scopes; renamed
  content reports no `data` finding; file mutation count unchanged (310, pure
  rename); no new (file, variable) group reaches the >= 5 threshold; the four
  separate pre-existing findings (`entry`, `url`, `out`, `text`) are
  unchanged by design.
- [x] AC-02: `python3 -m pytest tests/test_dashboard_terminals.py
  tests/test_opencode_serve_scan.py -q` passes unchanged in the ticket
  worktree (both suites green on base and head, compared against a clean base
  checkout so pre-existing environmental reds are not attributed to this
  change); `ruff check src/koruapi/opencode_terminals.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from the
  ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
