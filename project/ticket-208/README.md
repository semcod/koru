# Ticket 208: Decompose god function _build_parser in cli_fleet

- **ID**: ticket-208
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Remove the code2llm `God Function: _build_parser` finding at
`src/koru/cli_fleet.py:193` (CC=1, fan-out=10, mutations=35; PLF-028).

`_build_parser` currently declares all five fleet subcommands (`up`, `ls`,
`bootstrap`, `standard-update`, `standard-inventory`) inline. Extract each
subcommand's `add_parser`/`add_argument` block into a dedicated module-level
helper next to the existing `_add_standard_scope_arguments` helper, keeping
`_build_parser` as the single composition point. The bootstrap subcommand's
ten arguments split into scope-selection (`_add_bootstrap_scope_arguments`)
and init-behaviour (`_add_bootstrap_init_arguments`) groups so no helper
exceeds the god-function thresholds.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-028 queue handoff).
- [x] AC-02: `pytest -q tests/test_cli_fleet.py tests/test_standard_fleet.py tests/test_fleet_bootstrap.py tests/test_fleet_admission.py` passes unchanged.
- [x] AC-03: code2llm smell detection reports no god_function for `_build_parser` and no new god functions in `src/koru/cli_fleet.py`.
- [x] AC-04: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
