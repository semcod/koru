# Ticket 023: Adopt POA planning and Logs event contracts

- **ID**: ticket-023
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Adopt immutable, locally vendored POA and Wellmanifest Logs contracts for
Koru's planning boundary. Resolve Registry and Strategy candidates from
hash-pinned `subactor.config-response/v1` evidence, bind a separate Policy
decision to the exact planning input, compile only inert plans, and project
the result into a verifiable Logs event chain. The scope does not execute a
plan, grant authority, contact a registry, or add a runtime dependency.

## Acceptance criteria

- [x] AC-01: The active user request explicitly authorizes implementation,
  testing and GitHub publication.
- [x] AC-02: Vendored POA process and source-registry schemas and the
  Wellmanifest Logs contract are loaded only when their exact SHA-256 pins
  match and reject malformed or secret-shaped input.
- [x] AC-03: Dynamic Registry and Strategy resolution accepts only a unique,
  ready, highest-priority binding whose source, candidate and response bytes
  match the supplied evidence.
- [x] AC-04: A Policy decision is separately bound to the exact process,
  resolution snapshot, ticket and input reference; the compiled plan remains
  explicitly non-executable and grants no authority.
- [x] AC-05: Planning results produce schema-valid, hash-linked Logs events
  with strict stream, sequence, time, causation and correlation invariants.
- [x] AC-06: Focused tests, type/lint checks, governance, diff and Docker
  configuration checks pass; unrelated repository-wide baseline failures are
  recorded without expanding this ticket.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
