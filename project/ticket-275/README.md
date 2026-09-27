# Ticket 275: Address code smell: shotgun surgery descriptor locals in env2llm registry

- **ID**: ticket-275
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: descriptor` smell (planfile ticket PLF-050,
reported for `src/koruapi/env2llm_registry.py:210`) in
`src/koruapi/env2llm_registry.py`.

Nine wrapper functions in the file each tuple-unpack
`service, descriptor = _get_service(...)` and embed that second element in
their response payload under the `"service_descriptor"` key
(`env2llm_get_registry`, `env2llm_render_registry`,
`env2llm_refresh_registry`, `env2llm_sync_after_calibration`,
`env2llm_get_desktop`, `env2llm_validate_calibration`,
`env2llm_list_commands`, `env2llm_list_uris`, `env2llm_mqtt_status`). The
detector groups mutations by (file, variable) and fires at >= 5 scopes — the
shared *name* is the smell; each function actually holds an independent
binding (the descriptor dict of the service it just built, attached to that
function's own response stage).

Fix: stage-accurate local names, one per response stage the descriptor
annotates — `registry_descriptor` (`env2llm_get_registry`, the live registry
snapshot response), `render_descriptor` (`env2llm_render_registry`, the
rendered-document response), `refresh_descriptor`
(`env2llm_refresh_registry`, the regenerate/persist result),
`sync_descriptor` (`env2llm_sync_after_calibration`, the post-calibration
sync result), `desktop_descriptor` (`env2llm_get_desktop`, the desktop probe
slice), `validation_descriptor` (`env2llm_validate_calibration`, the
calibration validation result), `commands_descriptor`
(`env2llm_list_commands`, the command-schema listing), `uris_descriptor`
(`env2llm_list_uris`, the URI index payload), `mqtt_descriptor`
(`env2llm_mqtt_status`, the MQTT bridge status). The `descriptor` mutation
group drops from 9 scopes to 0. Pure rename of function-internal locals; no
signature, return shape (the response key stays `"service_descriptor"`) or
behavior change; no other file is touched.

Tests: the suites that exercise the renamed paths
(`tests/test_env2llm_registry.py`, `tests/test_mcp_server_split.py`,
`tests/test_mcp_server.py`, `tests/test_deps_autorepair.py`) run unchanged
as the behavioral proof of the pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `descriptor` in `src/koruapi/env2llm_registry.py`, and
  introduces no new (file, variable) mutation group at or beyond the
  threshold. Verified with the installed code2llm `DFGExtractor` mutation
  grouping on the file AST (standalone extract; `ProjectAnalyzer.analyze` on
  copies/worktrees silently yields empty scopes): baseline content reports a
  `descriptor` group of exactly 9 scopes — the nine wrappers listed above —
  matching the ticket's "spans 9 functions"; renamed content reports a
  `descriptor` group of 0 scopes; file mutation record count unchanged (67,
  pure rename); every renamed local lands at 1 scope. The pre-existing
  `service` group (9 scopes, same tuple-unpack double-counting) is untouched
  — it is a separate finding with its own planfile ticket.
- [x] AC-02: `python3 -m pytest tests/test_env2llm_registry.py
  tests/test_mcp_server_split.py tests/test_mcp_server.py
  tests/test_deps_autorepair.py -q` passes unchanged in the ticket worktree;
  `ruff check src/koruapi/env2llm_registry.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
