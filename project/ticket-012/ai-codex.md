---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-012
---
# Participant: codex (AI agent)

## Understanding

Make the merged ticket-011 policy resolution reproducible in a clean Koru
install by pinning the public SubLLM distribution.

## Execution plan

1. Add the public SubLLM version floor to core dependencies.
2. Regenerate the deterministic lockfile.
3. Run dependency, focused runtime and governance checks.
4. Publish through exact-head Validator review.

## Actual changes

- Recorded SESSION_EXECUTION_AUTHORIZATION from the active user request.
- Added public `subactor-subllm>=1.4.0,<2.0` to Koru core dependencies.
- Regenerated the public-source lock and passed 39 focused tests plus
  governance with zero findings.

## Blockers

- None inside the recorded intent.
