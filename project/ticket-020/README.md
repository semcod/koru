# Ticket 020: Restore queue lower-layer import contract

- **ID**: ticket-020
- **Owner**: unresolved:human
- **GitHub issue**: #40
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-28

## Goal and scope

Restore the declared dependency direction by moving shared todo2code process
helpers below both queue and autonomy consumers without changing behavior.

## Acceptance criteria

- [ ] AC-01: `lint-imports` keeps all declared contracts.
- [ ] AC-02: Focused todo2code and ticket hydration tests pass.
- [ ] AC-03: No queue module imports `koru.autonomy`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
