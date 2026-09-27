# Ticket 285: Address code smell: Shotgun Surgery: files locals in koru scan artifacts

- **ID**: ticket-285
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Session authority

SESSION_EXECUTION_AUTHORIZATION: the operator handed this lane over with an
explicit request to work planfile ticket PLF-039 (high priority, default
queue), implement the smallest smell-removing refactor and run the local
regression gates (recorded here per AGENTS.md rule 4; no human-owned
`user-*.md` file was created or edited).

## Goal and scope

Clear the code2llm `Shotgun Surgery: files` smell (planfile ticket PLF-039,
reported for `src/koru/scan_artifacts.py:493`) in
`src/koru/scan_artifacts.py`.

Six functions in the file mutate a local named `files`
(`_location_from_cc_ticket`, `_planfile_dup_groups_are_extern_mirrors`,
`_should_skip_code2llm_dup_ticket`, `_parse_high_cc_suggestions`,
`_count_pfix_diagnose_issues`, `_scan_pfix_report`; reproduced with the
installed code2llm `DFGExtractor` mutation grouping on the file AST: 6
mutation scopes). The detector groups mutations by (file, variable) and
fires at >= 5 scopes — the shared *name* is the smell; each function binds
an independent list/tuple that only coincidentally shares the generic name.

Fix: stage-accurate renames, one per binding stage, same lane shape as the
merged ticket-279/ticket-284 rename lanes:

- `ticket_files` — the `files` field of a planfile ticket
  (`_location_from_cc_ticket` for `code2llm_cc`, `_should_skip_code2llm_dup_ticket`
  for `code2llm_dup`), matching the pre-existing `ticket_files` local in
  `_parse_layer_hotspot_suggestions`
- `group_files` — one dup ticket's file group collected into `groups`
  (`_planfile_dup_groups_are_extern_mirrors`; trailing comprehension target
  renamed to `group` for in-function consistency)
- `located_files` — the file parts of the located `file:line` entries
  attached to a high-CC suggestion (`_parse_high_cc_suggestions`)
- `failed_paths` — normalized paths of failed pfix diagnose issues
  (`_count_pfix_diagnose_issues` returns them, `_scan_pfix_report` unpacks
  them for the affected-paths hint)

Not renamed: `Suggestion(files=...)` keyword arguments and the read-only
parameters named `files` in `_is_extern_mirror_file_group` /
`_files_byte_identical` — call-site arguments and parameters are not
mutations, and the detector does not count them.

## Acceptance criteria

- [x] AC-01: DFGExtractor mutation grouping on the file AST reports the
      `files` group at 0 scopes after the rename (baseline 6 scopes, exactly
      the ticket's "spans 6 functions"); total mutation record count
      unchanged at 247 (pure rename); every renamed local below the >= 5
      threshold; no other group newly reaches it.
- [x] AC-02: `tests/test_scan_artifacts.py tests/test_scan_split.py
      tests/test_scan.py` pass unchanged and `ruff check
      src/koru/scan_artifacts.py` is clean.
- [x] AC-03: `project/governance-check.sh --base <merge-base>` reports
      GOV-PASS from this worktree.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
