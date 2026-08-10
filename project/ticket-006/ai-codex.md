---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-006
---
# Participant: codex (AI agent)

## Understanding

Goal 2.1.292 accepts literal writable version declarations and correctly
rejects Koru's dynamic importlib metadata fallback as an explicit carrier.
The three literal carriers are already synchronized at 0.1.459.

Fresh PyPI verification additionally showed that Koru's CLI imports
`jsonschema` unconditionally while the dependency exists only in development
groups. The zero-dependency delivery ceiling prevents the integration ticket
from declaring that repair honestly, so this governance slice raises the
ceiling to exactly one.

## Execution plan

1. Remove only the obsolete configured selector.
2. Verify Goal reports the existing complete prebump without another bump.
3. Run governance and the paired ticket-004 release gates.
4. Deliver through protected PR and exact-head validator.

## Actual changes

- Removed the one non-literal selector without reserializing goal.yaml.
- Assigned VERSION, CHANGELOG.md and package-lock.json to integration ownership
  and routing, then updated the immutable manifest digest.
- Kept every existing delivery bound while permitting one explicitly audited
  runtime dependency per slice.

## Blockers

- None; publication evidence remains owned by paired ticket-004.
