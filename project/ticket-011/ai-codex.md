---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-011
---
# Participant: codex (AI agent)

## Understanding

Replace provider-specific autonomous calls with one SubLLM-resolved transport
while preserving Koru's existing call seams and fail-closed behavior.

## Execution plan

1. Add a provider-neutral SubLLM/LiteLLM transport.
2. Route planning and legacy OpenRouter facades through it.
3. Test policy resolution and missing-runtime behavior.
4. Run governed publication through exact-head validation.

## Actual changes

- Recorded SESSION_EXECUTION_AUTHORIZATION from the active user request.
- Added the SubLLM transport and routed autonomous planning through it.
- Preserved legacy facade names without retaining provider authority.
- Passed 58 focused tests and governance with zero findings.

## Blockers

- None inside the recorded intent.
