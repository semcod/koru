---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-015
---
# Participant: codex (AI agent)

## Understanding

The user requested one Subactor-owned model and provider configuration for
Koru. The extracted runtime still had two direct Cursor-only callers in the
queue and shell, bypassing the `korullm` provider-neutral transport.

## Execution plan

1. Replace the remaining direct Cursor calls with public `korullm` SubLLM
   helpers.
2. Preserve complete role-based messages for queue tickets.
3. Update the shell integration status to represent the central policy chain
   and retain migration from legacy `cursor` / `openrouter` settings.
4. Validate with the current SubLLM and korullm sources.

## Actual changes

- Replaced the queue's direct Cursor transport with
  `korullm.run_subllm_messages`, preserving system and user messages.
- Replaced the shell's direct Cursor transport with `korullm.run_subllm`.
- Changed the default integration display and readiness checks to `subllm`;
  stored legacy `cursor` and `openrouter` toggles are normalized to it.
- Extended the shell contract tests for the central route and verified 160
  focused tests with the local SubLLM and korullm source packages.

## Blockers

- None. Protected publication remains separate from this implementation.
