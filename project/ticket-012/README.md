# Ticket 012: Pin public SubLLM runtime for Koru

- **ID**: ticket-012
- **Owner**: agent:codex under SESSION_EXECUTION_AUTHORIZATION
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-26

## Goal and scope

Pin the public SubLLM execution policy as a core Koru runtime dependency so
autonomous planning never relies on an ambient host copy of the policy.

## Acceptance criteria

- [x] AC-01: The active user request explicitly authorizes implementation.
- [x] AC-02: A clean Koru dependency resolution installs
  `subactor-subllm>=1.4.0`.
- [x] AC-03: The lockfile and governance checks pass.

## Participants

- Human participant: authorization was supplied in the active session; no
  `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
