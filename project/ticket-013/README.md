# Ticket 013: Close merged SubLLM migration tickets

- **ID**: ticket-013
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-26

## Goal and scope

Reconcile repository governance after the protected merges of Koru PRs #31 and
#32 by closing their completed integration and application tickets.

## Acceptance criteria

- [x] AC-01: The active user request authorizes autonomous implementation.
- [x] AC-02: Tickets 011 and 012 are closed only after their protected PRs
  were confirmed merged.
- [x] AC-03: Governance and diff checks pass without implementation changes.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
