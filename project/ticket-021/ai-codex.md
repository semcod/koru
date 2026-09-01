---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-021
---
# Participant: codex (AI agent)

## Understanding

Koru's own doctor and scan report no hard failures, but the actual CI command
surface contains a reproducible undefined name and its README examples do not
match the existing argparse option placement. This ticket is the narrowest
unfinished scope that owns those defects.

## Execution plan

1. Wait for explicit approval and for governance dependency ticket-013.
2. Move `replace` to its actual consumer without changing publication policy.
3. Correct ticket-owned lint findings and command examples.
4. Add focused regression coverage for dry-run publication overrides.
5. Run focused tests, Ruff, Koru CI, governance and Docker validation.

## Actual changes

- Audit and planning evidence only; no implementation file was changed.

## Blockers

- Human approval is required before `EDIT`.
- Ticket-013 must land before this application workstream can be reserved.
