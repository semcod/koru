# Ticket 276: Address code smell: shotgun surgery entry locals in opencode terminals

- **ID**: ticket-276
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Clear the code2llm `Shotgun Surgery: entry` smell (planfile ticket PLF-051,
reported for `src/koruapi/opencode_terminals.py:1170`) in
`src/koruapi/opencode_terminals.py`.

Nine functions in the file mutate a local named `entry`
(`register_instance`, `set_auto_answer`, `discover_instances`,
`get_available_models`, `_resolve_terminal_target`, `terminal_detail`,
`terminal_messages`, `terminal_prompt`, `terminal_reply`). The detector
groups mutations by (file, variable) and fires at >= 5 scopes — the shared
*name* is the smell; each function actually holds an independent binding
(a persisted registry record, a scanned `/proc` serve process, a merged
instance record, a provider/model route, or the instance addressed by an
incoming request).

Fix: stage-accurate local names, one per stage the variable serves —
`existing` and `new_record` (`register_instance`, the registry record matched
by URL and the freshly built one appended), `registered`
(`set_auto_answer`, the persisted record whose `auto_answer` flag flips),
`scanned` and `instance` (`discover_instances`, a `/proc`-scanned serve
process and the merged instance records it contributes to), `model_route`
plus `default_route` (`get_available_models`, one offered provider/model
pair and the config-declared default), `target`
(`_resolve_terminal_target` and `terminal_prompt`, the resolved prompt
target — same stage naming as the pre-existing `target` in
`stop_instance`), and `instance` (`terminal_detail`, `terminal_messages`,
`terminal_reply`, the located instance each endpoint addresses). The
`entry` mutation group drops from 9 scopes to 0. Pure rename of
function-internal locals; no signature, return shape or behavior change;
no other file is touched.

Tests: the suites that exercise the renamed paths
(`tests/test_opencode_serve_scan.py`, `tests/test_dashboard_terminals.py`)
run unchanged as the behavioral proof of the pure rename.

## Acceptance criteria

- [x] AC-01: code2llm smell re-scan no longer reports `shotgun_surgery` for
  the variable `entry` in `src/koruapi/opencode_terminals.py`, and introduces
  no new (file, variable) mutation group at or beyond the threshold.
  Verified with the installed code2llm `DFGExtractor` mutation grouping on
  the file AST (standalone extract; `ProjectAnalyzer.analyze` on
  copies/worktrees silently yields empty scopes): baseline content reports
  `Mutation of variable 'entry' spans 9 functions` from exactly the nine
  scopes listed above; renamed content reports an `entry` group of 0 scopes;
  file mutation record count unchanged (310, pure rename); no renamed local
  lands above 4 scopes (`instance` 4, `target` 4 — the renamed prompt-target
  pair joins the two pre-existing `target` scopes in `stop_instance` and
  `_file_part_chunk`). The pre-existing `url` (6), `out` (5) and `text`
  (5) groups are untouched — separate findings with their own planfile
  tickets.
- [x] AC-02: `python3 -m pytest tests/test_opencode_serve_scan.py
  tests/test_dashboard_terminals.py -q` passes unchanged in the ticket
  worktree; `ruff check src/koruapi/opencode_terminals.py` reports zero
  errors.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` passes
  with 0 errors from the ticket worktree (GOV-PASS, 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
