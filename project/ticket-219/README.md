# Ticket 219: decompose god function main in uri2koru cli

- **ID**: ticket-219
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Address code smell: `God Function: main` in
`packages/uri2koru/src/uri2koru/cli.py:14` (PLF-037).

Extract the argparse construction into `_add_decode`/`_add_run`/`_add_resolve`
subcommand registrars plus `_build_parser`, and route dispatch through
`_cmd_decode`/`_cmd_run`/`_cmd_resolve` handlers, so `main` drops from
CC=12 / fan-out=16 / mutations=19 to CC=4 / fan-out=5 / mutations=1.
The registrars are split per subcommand because code2llm counts every
`add_*` argparse call as a mutation; a single builder would keep 16.
The public `main(argv) -> int` contract, the `uri2koru` console-script
binding and the stdout/stderr/exit-code behavior stay identical.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner (SESSION_EXECUTION_AUTHORIZATION).
- [x] AC-02: code2llm reports no god function defined in `cli.py`; `cli.main` and every new helper sit below CC 12 / fan-out 10 / mutations 6.
- [x] AC-03: `python3 -m pytest -q packages/uri2koru/tests/test_uri2koru.py` passes with new main() dispatch regression tests (decode, run text/--json, resolve text/--json, unknown-command exit).
- [x] AC-04: Public interface unchanged: `uri2koru.cli:main` console script and `main(argv) -> int` signature.
- [x] AC-05: `bash project/governance-check.sh` passes with 0 errors.

## Tracking boundary

SESSION_EXECUTION_AUTHORIZATION: the PLF-037 planfile handoff instructs
to refactor, run local tests and close the ticket (user message 2026-09-26).

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
