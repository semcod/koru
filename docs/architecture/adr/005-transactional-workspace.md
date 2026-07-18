# ADR-AD-005: Transactional workspace

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §2, PR11 + PR14  
- **Subactor analogue:** release directory + atomic activate / rollback (different domain: code vs httpdocs).

## Context

Autonomous code edits today land directly in the project working tree (via IDE LLM or shell tickets). Failures after partial apply leave dirty trees and ambiguous ticket status.

## Decision (proposed)

1. Code-mutating plans execute inside a **transactional git worktree** (or equivalent isolated tree) bound to `run_id` / `plan_hash`.
2. **Promote** merges/applies into the main worktree only after evidence verify passes.
3. **Rollback** discards the worktree (and any staged grant effects) and records `rolled_back` + ticket note.
4. Dirty main tree or promote conflict → `needs_human`, never silent overwrite.

## Consequences

- Shell tickets that mutate files must declare capability `workspace.mutate` and go through the workspace manager.
- IDE drive that writes files should prefer the same worktree when the plan is code-mutating (phased).
