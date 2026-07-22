# ADR-AD-003: Shared ExecutionPlan lifecycle

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §5, PR4–PR6  
- **Related:** ADR AUTO-002 (arbiter/planning LLM become plan *inputs*)

## Context

Cycle, operator, repair, and replay each carry partial “plan” shapes (`ActionPlan`, drive traces, repair registry entries). Status collapses to booleans or ticket states, so verify/rollback cannot be shared.

## Decision (proposed)

1. One **`ExecutionPlan`** schema (JSON Schema and/or protobuf) is the SSOT for runnable work across cycle, operator, repair, and replay.
2. Lifecycle states follow the plan doc (§5): `proposed` → … → `completed`, plus explicit failure/control states (`needs_human`, `rolled_back`, …).
3. Planning LLM / arbiter **propose**; they do not mutate the workspace or drive IDE except by emitting plans consumed by the dispatcher after grant (when required).
4. Public APIs/MCP must expose lifecycle status richer than `ok: true|false`.

## Consequences

- Dual-run: existing loops emit ExecutionPlan alongside legacy structures before cutover.
- Import-linter eventually forbids planning modules from calling subprocess/GUI directly (ADR-AD-004 + dispatcher PR).
