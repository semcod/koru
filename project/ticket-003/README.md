# Ticket 003: Restore Koru Ruff baseline

- **ID**: ticket-003
- **Owner**: unresolved:human
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-08-05
- **Work classification**: `SERVICE / health`

## Goal and scope

Restore the existing `python -m ruff check src/koru` gate on unchanged
`main@5943447`. Apply Ruff's deterministic import ordering to the 31 reported
files and manually wrap the single E501 line without changing runtime behavior.

## Acceptance criteria

- [ ] AC-01: Human approves the bounded mechanical baseline repair.
- [ ] AC-02: Ruff reports zero findings under `src/koru`.
- [ ] AC-03: The 105 focused init/autopilot/todo2code tests pass.
- [ ] AC-04: Koru PR smoke passes on Python 3.12.

## Participants

- Human participant: unresolved; no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md).

## Risk boundary

Thirty-five I001 findings are mechanically fixable; one E501 line requires a
manual non-semantic wrap. No API, dependency, queue priority, governance,
Docker or generated-analysis behavior may change.
