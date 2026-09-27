# Ticket 274: Address code smell: shotgun surgery data locals in ide adapters shared

- **ID**: ticket-274
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: data` smell (planfile ticket PLF-049,
reported for `src/koru/ide_adapters/shared.py:72`) in
`src/koru/ide_adapters/shared.py`.

Six functions in the file mutate a local named `data`
(`_read_json_object`, `read_socket_from_settings`, `fix_workspace_socket`,
`fix_user_socket`, `vscode_core_version`,
`extension_listed_in_extensions_json`). The detector groups mutations by
(file, variable) and fires at >= 5 scopes — the shared *name* is the smell;
each function actually holds an independent decoded document (a parsed
settings.json object being read or updated, the parsed `product.json` core
manifest, or the parsed `extensions.json` entry list).

Fix: stage-accurate local names — `parsed` (the decoded JSON value being
validated as a dict, in `_read_json_object`), `settings` (the settings.json
object, in `read_socket_from_settings`), `workspace_settings`
(`fix_workspace_socket`) and `user_settings` (`fix_user_socket`, the two
settings documents the socket fixers read and rewrite), `product_info`
(`vscode_core_version`, the parsed `product.json`; `product` is already bound
to the config-home Path in that function), `entries`
(`extension_listed_in_extensions_json`, the parsed `extensions.json` list).
The `data` mutation group drops from 6 scopes to 0. Pure rename of
function-internal locals; no signature, return shape or behavior change; no
other file is touched.

Tests: the suites that exercise the renamed paths
(`tests/test_ide_adapters.py`, `tests/test_ide_doctor_cli.py`,
`tests/ides/test_all_ide_strategies.py`, `tests/ides/test_cursor_strategy.py`)
run unchanged as the behavioral proof of the pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `data` in `src/koru/ide_adapters/shared.py`, and introduces no
  new (file, variable) mutation group at or beyond the threshold. Verified
  with the installed code2llm `DFGExtractor` mutation grouping on the file AST
  (standalone extract; `ProjectAnalyzer.analyze` on copies/worktrees silently
  yields empty scopes): baseline content reports `Mutation of variable 'data'
  spans 6 functions` from exactly the six scopes listed above; renamed content
  reports a `data` group of 0 scopes; file mutation record count unchanged
  (94, pure rename); every renamed local lands at 1 scope. The pre-existing
  `strategy` group (5 scopes) is untouched — it is a separate finding with its
  own planfile ticket.
- [x] AC-02: `python3 -m pytest tests/test_ide_adapters.py
  tests/test_ide_doctor_cli.py tests/ides/test_all_ide_strategies.py
  tests/ides/test_cursor_strategy.py -q` passes unchanged in the ticket
  worktree; `ruff check src/koru/ide_adapters/shared.py` reports zero errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
