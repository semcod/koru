---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-003
---
# Participant: codex (AI agent)

## Understanding

Koru's PR smoke fails before tests because unchanged main contains 35 I001
import-order findings across 31 files and one E501 line in `src/koru/init.py`.
Ruff marks all I001 fixes safe and deterministic.

## Execution plan

1. After approval, transition to `IN_PROGRESS / EDIT`.
2. Apply only Ruff's safe I001 fixes and the one manual line wrap.
3. Inspect the full diff for semantic changes.
4. Run Ruff plus the 105 focused Koru tests and publish a ticket-scoped PR.
5. Merge the repair, refresh adoption PR #14, and delete the repair branch.

## Actual changes

- None; waiting for approval.

## Blockers

- Human approval is required before modifying runtime files.
