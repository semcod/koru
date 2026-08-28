---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-020
---
# Participant: codex (AI agent)

## Understanding

The user explicitly requested autonomous continuation and publication. This
session authorization covers the bounded repair in `intent.json`; it is not a
trusted merge approval.

## Execution plan

1. Extract shared todo2code helpers into the lower queue layer.
2. Preserve the existing private helper names for autonomy callers.
3. Run governance, import contracts, focused tests and CI before publication.

## Actual changes

- Work started from the exact failing `main` CI evidence in issue #40.

## Blockers

- None.
