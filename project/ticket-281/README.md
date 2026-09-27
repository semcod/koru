# Ticket 281: Address code smell: Shotgun Surgery: expected_version locals in koru autopilot install checks

- **ID**: ticket-281
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Planfile**: PLF-056 (dedupe key
  `code2llm:smell:shotgun_surgery:src/koru/autopilot/install_checks.py:243:Shotgun Surgery: expected_version`)

## Goal and scope

Clear the code2llm Shotgun Surgery smell for the variable `expected_version`
in `src/koru/autopilot/install_checks.py` (reported at line 243, planfile
ticket PLF-056). Six functions in the module each assigned a generic local
`expected_version = plugin.get("expected_version")`; the code2llm
shotgun-surgery detector groups mutations by (file, variable) and fires at
>= 5 scopes, so the shared generic name read as one cross-cutting concern.

Replace the generic local in each function with a stage-accurate name for the
piece of the version comparison that stage actually consumes:

- `source_vsix_version` (`check_plugin_installed_version_mismatch_issue`,
  `check_plugin_version_mismatch_issue`) - the version the source VSIX/package
  declares, contrasted with the installed extension and the connected plugin
  respectively; both issue messages already say "the source VSIX/package".
- `expected_installed_version`
  (`check_plugin_installed_ok_but_not_connected_issue`,
  `check_plugin_socket_candidate_mismatch_issue`) - the version the on-disk
  install must match before the "installed OK but ..." secondary condition is
  considered.
- `live_host_expected_version` (`check_plugin_live_host_stale_issue`) - the
  version the live extension host is judged against when gating on the
  install match and classifying rejected reconnects as stale.
- `expected_connected_version`
  (`_plugin_live_connection_matches_expected`) - the normalized
  (str-coerced, stripped) version the live connection must report, pairing
  with `connected_version` the way `expected_build` pairs with
  `connected_build`.

Private-helper parameters named `expected_version`
(`_plugin_install_matches_expected`, `_stale_rejected_plugins`,
`_is_stale_rejected_plugin`) are function arguments, not assignments, so the
DFG mutation extractor does not count them; they keep the accurate generic
name. Pure rename: no signature, return shape, dict key or behavior change.

## Acceptance criteria

- [x] AC-01: Standalone code2llm DFGExtractor mutation grouping on the file
  AST reports the `expected_version` group dropping from 6 scopes (matching
  the ticket's "spans 6 functions") to 0, with the file mutation record count
  unchanged at 46 (pure rename) and every new name landing at 2/2/1/1 scopes,
  far below the >= 5 threshold; the untouched `installed_version` and `_`
  groups stay at 4.
- [x] AC-02: `python3 -m pytest tests/test_install_checks.py
  tests/test_autopilot_commands_manage.py -q` passes unchanged and
  `ruff check src/koru/autopilot/install_checks.py` reports zero errors -
  pure rename of function-internal locals.
- [x] AC-03: `bash project/governance-check.sh --base <merge-base>` returns
  GOV-PASS from the ticket worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
