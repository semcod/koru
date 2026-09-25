# Ticket 214: Decompose god function build_parser in cli_work

- **ID**: ticket-214
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Address code smell: `God Function: build_parser` in
`src/koru/cli_work.py:129` (PLF-032).

Convert `build_parser` to table-driven subparser construction: the per-subcommand
`add_argument` calls move into module-level spec tuples applied by a single
`_add_subcommand` helper, so no function in the module performs more than a
handful of mutating builder calls. The CLI surface (flags, defaults, help
strings, `set_defaults(func=...)` dispatch) stays byte-identical.

The smell is driven by the code2llm mutation heuristic counting every
`add_argument`/`set_defaults`/`add_parser` call, so a plain per-subcommand
helper split would stay above the thresholds; the spec tables remove the
builder-call fan-out from code entirely.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (planfile PLF-032 queue handoff).
- [x] AC-02: `build_parser` and the new `_add_subcommand` helper fall under the
  god-function thresholds (CC <= 12, fan-out <= 10, mutations <= 6).
- [x] AC-03: `pytest -q tests/test_work_lifecycle.py` passes plus a new parser
  regression test covering every subcommand's flags, defaults and dispatch.
- [x] AC-04: code2llm analysis of the changed file reports no function above the
  god-function thresholds introduced by this change.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation evidence (2026-09-26)

- AC-02/AC-04: code2llm ProjectAnalyzer probe on the changed file:
  `build_parser` CC=2 / fan-out=5 / mutations=5 (was fan-out=11 / mutations=33);
  `_add_subcommand` CC=2 / fan-out=3 / mutations=4. Only remaining above-threshold
  function is the pre-existing, separately ticketed `_action_next` (unchanged).
- AC-03: `pytest -q tests/test_work_lifecycle.py` → 8 passed (3 existing + 5 new
  parser regression tests). `tests/test_cli.py` shows the same 4 failures before
  and after the change (venv-reexec environmental + docs drift, pre-existing at HEAD).
- Parser equivalence: old vs new `build_parser` produce identical `-h` output for
  the main parser and all three subcommands and identical Namespace results for
  6 representative argvs.
- AC-05: `bash project/governance-check.sh` over the changed files → GOV-PASS.
