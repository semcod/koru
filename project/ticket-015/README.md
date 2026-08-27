# Ticket 015: Move Koru LLM runtime modules to korullm

- **ID**: ticket-015
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
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

## Closure evidence

The implementation was merged to `main` by pull request #34 at
`d4a7ecfddd4208a65af835afc1f47b2ac2e9358d`; both acceptance criteria were
already checked before merge.
