# Ticket 269: Address code smell: shotgun surgery data in plugin installer json loaders

- **ID**: ticket-269
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-044,
dedupe key
`code2llm:smell:shotgun_surgery:packages/koruide/src/koruide/plugin_installer.py:356`)
in `packages/koruide/src/koruide/plugin_installer.py`.

Six functions in the file assign a local named `data` from `json.loads`
(`_plugin_package_version`, `_plugin_package_name`, `_package_build_sha`,
`_vsix_build_sha`, `_active_extension_locations`,
`_installed_extension_build_sha`). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each local actually holds a different, independent JSON document (the plugin
dir's `package.json`, a repo `package.json`, the VSIX-embedded
`package.json`, and the IDE `extensions.json` registry list).

Fix: stage-accurate names for the JSON document each function parses —
`plugin_manifest` (plugin dir `package.json`: version and name loaders),
`package_manifest` (repo `package.json` build-sha loader), `vsix_manifest`
(package.json inside the built VSIX archive), `metadata_entries`
(`extensions.json` list: active locations and installed build sha). The
`data` group drops from 6 scopes to 0; the largest replacement-name group is
2 (well under the threshold). `_extract_build_sha` already used `pkg_data`
and is untouched. Pure local rename inside one module; no behavior change.

Tests: the renamed loaders are exercised by the four suites that import
`plugin_installer` (`tests/test_autopilot_plugin_installer.py`,
`tests/test_qoder_ide_support.py`, `tests/test_koruide_bridges.py`,
`tests/test_autonomous_plugin_runtime.py`); those run unchanged as the
behavioral proof of the rename.

Authorization: the operator handoff for PLF-044 explicitly requested this
refactor and its execution, recorded here as SESSION_EXECUTION_AUTHORIZATION
(agent-owned file; no `user-*.md` input used).

## Acceptance criteria

- [x] AC-01: the code2llm shotgun-surgery detector no longer reports a
  `data` mutation group for
  `packages/koruide/src/koruide/plugin_installer.py`, and the rename
  introduces no new group at the >= 5 threshold. Verified with the installed
  code2llm `DFGExtractor` run standalone on the file (deterministic ground
  truth): original content groups `data` in exactly the 6 ticket functions
  and fires; renamed content has no `data` group, an unchanged total
  mutation count (198), and largest replacement-name group of 2 scopes
  (`plugin_manifest`, `metadata_entries`). The separate pre-existing
  `proc` (7 scopes) and `resolved` (7 scopes) findings in the file are
  untouched (minimal-scope decision, same as ticket-266 left its separate
  `ticket_id` finding).
- [x] AC-02: `python3 -m pytest tests/test_autopilot_plugin_installer.py
  tests/test_qoder_ide_support.py tests/test_koruide_bridges.py
  tests/test_autonomous_plugin_runtime.py -q` passes (43 passed) and
  `ruff check packages/koruide/src/koruide/plugin_installer.py` reports
  zero errors in the ticket worktree.
- [x] AC-03: `bash project/governance-check.sh` passes with 0 errors from
  the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
