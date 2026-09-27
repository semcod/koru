# Ticket 263: Address code smell: shotgun surgery config in mcp provision

- **ID**: ticket-263
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Remove the code2llm `Shotgun Surgery` reports for `src/koru/mcp_provision.py`
(planfile **PLF-040**): the generic locals `config` (6 functions) and `servers`
(7 functions) are assigned or mutated in every per-IDE provisioner plus the
remove/ensure helpers, so one change to that flow ripples across the file.
Consolidate the four copy-pasted provisioner bodies (windsurf, cursor, vscode,
zed) into a single `_upsert_koru_server` owner of the read → upsert → write
flow; each provisioner keeps only its config-path resolution and entry builder.
Same-file mutator counts drop to 3 (`config`) and 4 (`servers`), below the
detector's >=5 threshold. Behavior is unchanged; a new test pins the previously
untested Windsurf global-config fallback branch.

Scope: `src/koru/mcp_provision.py` and `tests/test_mcp_provision.py` only
(XS delivery contract in `intent.json`).

## Acceptance criteria

- [ ] AC-01: `python3 -m pytest -q tests/test_mcp_provision.py` plus the
  neighboring suites that import `mcp_provision`
  (`tests/test_ide_map_consolidation.py`, `tests/test_autonomy_environment.py`,
  `tests/test_autonomous_operator.py`) pass, including the new
  `test_provision_windsurf_falls_back_to_global_config`.
- [ ] AC-02: code2llm reports no `Shotgun Surgery` smell for
  `src/koru/mcp_provision.py` (no variable reaches 5 same-file mutators).
- [ ] AC-03: `ruff check src/koru/mcp_provision.py tests/test_mcp_provision.py`
  is clean.
- [ ] AC-04: `project/governance-check.sh` reports 0 errors.

## Session authorization

`SESSION_EXECUTION_AUTHORIZATION`: planfile handoff PLF-040 (2026-09-26)
instructed this session to implement the refactor, run local tests, and close
the ticket with `planfile ticket done` once checks pass, leaving no completed
work in `waiting_input`. Recorded by the Claude lane (agent-owned file).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
