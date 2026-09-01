---
participant-id: agent:cursor
participant: cursor
role: agent
ticket: ticket-030
---
# Participant: cursor (AI agent)

## Understanding

Task profiles must run full policy CI on verify, not gates-only checks.
Gate resolution without topology must not enable every optional tool.

## Execution plan

1. Update task_profiles.yaml verify/baseline commands.
2. Fix resolve_gates fallback in gates.py.
3. Add doctor quality pipeline probes and regression tests.
