# Ticket 251: Address code smell: shotgun surgery command in dsl2koru argv

- **ID**: ticket-251
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

code2llm reports `Shotgun Surgery: command` for
`packages/dsl2koru/src/dsl2koru/handlers/argv.py:62` (planfile ticket
PLF-041): seven `_build_*_args` builders each grow a local `command` list
via `append`/`extend`, so changing how flags are appended ripples across
the whole module.

Replace the mutating builders with pure `return [...]` expressions over
three shared argv-fragment helpers (`_flag_args`, `_value_args`,
`_positional_args`), keeping every produced argv byte-identical. Scope is
`argv.py` plus a new `packages/dsl2koru/tests/test_argv.py` pinning
`to_cli_args` for every dispatched verb.

## Acceptance criteria

- [x] AC-01: No `command = ...` assignment or `command.append/extend`
      mutation remains in `argv.py`.
- [x] AC-02: `to_cli_args` argv output for every dispatched verb and the
      unknown-verb fallback is pinned by `test_argv.py` (captured against
      the pre-refactor implementation) and passes unchanged.
- [x] AC-03: The full `packages/dsl2koru/tests/` and
      `packages/dsl2coru/tests/` suites pass with no baseline regression.
- [x] AC-04: `project/governance-check.sh` reports 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
