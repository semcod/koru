# Ticket 015: Move Koru LLM runtime modules to korullm

- **ID**: ticket-015
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-26

## Goal and scope

Move the LLM boundary out of Koru after ticket-014 declares the published
`korullm` dependency. Koru retains only its task orchestration and compatibility facades.

## Acceptance criteria

- [x] AC-01: Koru imports provider routing only from korullm.
- [x] AC-02: Focused LLM tests pass against the public package source and the
  current SubLLM transport contract.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
