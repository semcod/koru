# Ticket 309: Stage-accurate names for the ide locals in mcp server ide tools

- **ID**: ticket-309
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-044 (high priority, current
sprint), make the smallest smell-removing refactor and run the local tests
(recorded here per AGENTS.md rule 4; no human-owned `user-*.md` file was
created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: ide` smell (planfile ticket PLF-044,
reported for `src/koruapi/mcp_server_ide.py:293`, dedupe key
`code2llm:smell:shotgun_surgery:src/koruapi/mcp_server_ide.py:293:Shotgun
Surgery: ide`) in `src/koruapi/mcp_server_ide.py`. The ticket evidence
file sha256 (4f66e2c6…) matches the current file, so the report is not
stale.

Five functions in the file assign a local named `ide` — reproduced with the
installed code2llm `DFGExtractor` mutation grouping on the file AST:
`tool_ide_command_catalog` (line 234, "all"-normalized catalog filter),
`tool_strategy_prompt` (line 251, the same normalization for the strategy
prompt), `tool_ide_commands` (line 268, raw requested IDE id scoping the
store/telemetry lookups), `tool_ide_list_uris` (line 305, "auto"-defaulted
IDE lane echoed into the URI index) and `tool_ide_drive` (line 362,
"auto"-defaulted drive target). The detector groups mutations by
(file, variable) and fires at >= 5 scopes. As in the PLF-039/PLF-041/PLF-043
lanes, these are five *different* argument-handling stages that coincidentally
reuse the generic name — naming coincidence, not one coupled variable — so the
fix is per-site renaming, not centralization.

## Fix

Rename each `ide` local to the argument stage that produces it (pure local
rename, no expression, call, order or signature change; two call lines merely
reflowed to stay within the 120-column limit):

- `tool_ide_command_catalog`: `catalog_ide_filter` ("all" normalized to None
  before querying the command catalog)
- `tool_strategy_prompt`: `strategy_ide_filter` (same normalization, applied
  to the strategy prompt)
- `tool_ide_commands`: `requested_ide_id` (raw requested id that scopes the
  runtime catalog store and telemetry lookups)
- `tool_ide_list_uris`: `requested_ide_lane` (matches the schema's "IDE lane
  for socket selection" wording; echoed into the payload)
- `tool_ide_drive`: `target_ide` (matches the schema's "Target IDE" wording;
  forwarded to the daemon drive call)

The `"ide"` dict keys in response payloads, the schema entries in
`build_tool_schemas` and the `ide=` keyword argument to `client.drive(...)`
are API field names, not variable mutations, and stay as they are.

## Validation

- AC-01: standalone DFGExtractor mutation grouping on the file AST —
  baseline `ide` group = exactly the reported 5 scopes; after the refactor
  `ide` = 0 scopes, each new name = 1 scope; largest remaining group is the
  pre-existing `payload` at 3 sites (below threshold, separate variable,
  out of scope); no group newly reaches the >= 5 threshold
- AC-02: targeted pytest run over the suites exercising the koruapi MCP
  tool surface (`tests/test_mcp_server.py`, `tests/test_mcp_server_split.py`,
  `tests/test_desktop_uri.py`) — zero failures; `ruff check` clean on the
  touched file
- AC-03: `project/governance-check.sh --base <merge-base>` — GOV-PASS
  0 errors 0 warnings
