# Ticket 183: Decompose god function build_parser in cli_ci (STARTER-601)

- **ID**: ticket-183
- **Owner**: opencode
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

SESSION_EXECUTION_AUTHORIZATION: user handoff 2026-09-19 directs executing
planfile STARTER-601 (smallest refactor that removes the smell, run local
tests) after freeing the application WIP slot via the protected merge of
ticket-180 (PR #362, merged by app/ifuri-validator-agent).

Source finding: code2llm `God Function: build_parser` at
`src/koru/cli_ci.py:99` (fan-out=13, mutations=30), planfile STARTER-601.

## Goal and scope

Split build_parser into module-level subparser builders in
`src/koru/cli_ci.py` only; no behavior, help-text or public API change.
Admission: application workstream was 3/4 after the ticket-180 merge; no cap
exception used.

## Acceptance criteria

- [x] AC-01: Existing koru ci CLI tests pass unchanged.
- [x] AC-02: Lint and whitespace checks pass for the rewritten module.
- [x] AC-03: Parser parity with origin/main verified (identical Namespaces
      for all three subcommands and identical --help output).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
