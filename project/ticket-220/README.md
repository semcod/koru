# Ticket 220: Decompose god function main in nlp2koru cli

- **ID**: ticket-220
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: main` in
`packages/nlp2koru/src/nlp2koru/cli.py:14` (PLF-038).

Move argparse construction into declarative `ArgumentSpec` tables registered
by `_add_arguments`/`_build_parser`, and route dispatch through
`_cmd_to_dsl`/`_cmd_apply`/`_cmd_workflow`/`_cmd_rewrite` handlers, so `main`
drops from CC=12 / fan-out=16 / mutations=31 to CC=4 / fan-out=6 /
mutations=1. The spec tables are used instead of ticket-219-style
per-subcommand registrars because to-dsl and apply each take 5 arguments and
code2llm counts every `add_*` argparse call as a mutation: a registrar would
hold 7 mutations and stay above the threshold. The public `main(argv) -> int`
contract, the `nlp2koru`/`nlp2coru` console-script bindings and the
stdout/stderr/exit-code behavior stay identical.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: code2llm reports no god function defined in `cli.py`; `cli.main` and every new helper sit below CC 12 / fan-out 10 / mutations 6.
- [x] AC-03: `PYTHONPATH=packages/dsl2koru/src:packages/uri2koru/src:packages/nlpshim/src:packages/nlp2koru/src python3 -m pytest -q packages/nlp2koru/tests/test_nlp2koru.py` passes with new main() dispatch regression tests (to-dsl text/--json, to-dsl error exit, apply --json, workflow, rewrite-chat); `test_apply_validate_lane` failure is pre-existing on main (environmental dispatch).
- [x] AC-04: Public interface unchanged: `nlp2koru.cli:main` console script and `main(argv) -> int` signature.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-038 planfile handoff instructs
to refactor, run local tests and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
