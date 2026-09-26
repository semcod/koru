# Ticket 223: Decompose god function prepare_workspace

- **ID**: ticket-223
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: explicit planfile handoff for PLF-049
(code2llm god-function report) instructing this session to refactor
`prepare_workspace` in `src/koru/ticket_command/workspace.py`
(CC=10, fan-out=23, mutations=17), run local tests and close the planfile
ticket.

Scope, budgets and non-goals are bound by `intent.json`.

## Acceptance criteria

- [ ] AC-01: `prepare_workspace` no longer exceeds god-function thresholds
      (fan-out > 10, mutations > 6, CC > 12) per code2llm/regix analysis.
- [ ] AC-02: Behavior is preserved — exact check order, error messages, lease
      bytes and public contract (`service.py` imports unchanged).
- [ ] AC-03: Local ticket-command test suite passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
