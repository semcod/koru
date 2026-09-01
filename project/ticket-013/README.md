# Ticket 013: Reconcile merged implementation tickets

- **ID**: ticket-013
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-26

## Goal and scope

Reconcile repository governance after protected implementation merges. Preserve
the prior closure evidence for PRs #31 and #32, close tickets 019 and 020 only
against their exact merged heads, and return incomplete ticket 021 to a
non-reserving planning state.

## Acceptance criteria

- [x] AC-01: The active user request authorizes autonomous implementation.
- [x] AC-02: Tickets 011 and 012 are closed only after their protected PRs
  were confirmed merged.
- [x] AC-03: Tickets 019 and 020 are closed only after their merged PR heads
  and protected checks were confirmed.
- [x] AC-04: Ticket 021 is retained as unfinished work with a valid bounded
  intent and no active write-scope reservation.
- [x] AC-05: Concurrent ticket 022 is retained as unfinished work with a valid
  bounded intent and no active write-scope reservation.
- [x] AC-06: Governance, Docker configuration and diff checks pass without
  implementation changes.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
