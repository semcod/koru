# Ticket 011: Route Koru autonomous LLM calls through SubLLM

- **ID**: ticket-011
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-26

## Goal and scope

Route Koru autonomous planning, strategy selection and visual decision calls
through the public SubLLM policy instead of forcing Cursor or OpenRouter in
Koru source. Preserve legacy function names only as compatibility facades.

## Acceptance criteria

- [x] AC-01: The active user request explicitly authorizes implementation.
- [x] AC-02: Koru resolves `koru-agent/planning-assistant` without forcing a
  provider and therefore selects direct Z.AI GLM 5.3 under current policy.
- [x] AC-03: Missing SubLLM or credentials fail closed with actionable,
  secret-safe evidence.
- [x] AC-04: Focused tests and repository governance checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
