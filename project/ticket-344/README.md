# Ticket 344: feat(telemetry): append markdown formatted console logs with codeblocks to project ticket koru log

- **ID**: ticket-344
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Persist markdown formatted console logs with codeblocks for URI, YAML and NL/DSL in project/ticket-*/koru.log.md.

## Acceptance criteria

- [x] AC-01: `src/koru/autonomy/cycle_trace.py` appends decision trace markdown codeblocks into `project/ticket-*/koru.log.md` whenever an active ticket is scoped.
- [x] AC-02: All unit tests in `tests/test_cycle_trace.py` pass and governance check passes.

## Scope limit

Changes confined to cycle_trace and unit tests.

## Validation

- 7 unit tests in `tests/test_cycle_trace.py` pass.
- Ruff check passes.
- Governance checks pass.
