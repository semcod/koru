# ADR-AD-005: Transactional workspace

- **Status:** Accepted  
- **Date:** 2026-07-18  
- **Accepted:** 2026-07-18 (queue patch transaction v1)  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §2, PR11 + PR14  
- **Subactor analogue:** release directory + atomic activate / rollback (different domain: code vs httpdocs).

## Context

Autonomous code edits today land directly in the project working tree (via IDE LLM or shell tickets). Failures after partial apply leave dirty trees and ambiguous ticket status.

## Decision

1. Code-mutating **queue patch tickets** execute inside a **transactional git worktree** (when `KORU_QUEUE_WORKTREE` is enabled and a verify command is set) bound to `run_id` and an **immutable on-disk manifest** (`.koru/runs/<run_id>/manifest.json`).
2. **Promote** applies into the main worktree only after evidence verify passes **and** the persisted manifest matches the frozen plan (HEAD + target-file digests). Drift → `promotion_conflict`, missing/tampered manifest → `manifest_not_persisted`.
3. **Rollback** discards the worktree; verify failures in direct mode revert touched files via `git checkout --`.
4. Dirty main tree on direct apply, or promote conflict, → refuse (`unsafe_direct_apply_to_dirty_workspace`, `promotion_conflict`), never silent overwrite.
5. **Promotion modes (queue):**
   - `apply` — promote verified patch into the working tree; human commits.
   - `branch` — commit onto `koru/run-<run_id>` in the worktree; main untouched (**preferred on shared checkouts**).
   - `commit` — promote then `git commit` on the current branch (requires clean repo).
   - `artifact` — write patch + manifest only; workspace unchanged.
6. Patch retry (orchestrator, max 1 by default) pins the first failure's manifest; workspace drift between attempts → `manifest_mismatch`.

## Implemented (v1)

| Area | Location |
| --- | --- |
| Manifest freeze + hash | `src/koru/queue/manifest.py` |
| Persist + pre-promote check | `persist_manifest`, `persisted_manifest_mismatch` |
| Worktree staging + dirty seed | `src/koru/queue/workspace.py` |
| Transaction + promotion | `src/koru/queue/patch_transaction.py` |
| Retry pin | `src/koru/queue/patch_retry.py` |
| Structural outcome codes | `PatchOutcome` in `patch_mode.py` |

## Deferred (not blocking v1)

- Signed execution grants + `jti` replay store (see ADR-004) for non-queue mutators (IDE drive, scan apply).
- Mandatory `workspace.mutate` capability declaration on all shell tickets.
- IDE drive routed through the same worktree manager.
- Public `PatchTransactionResult` wrapper type (callers use `PatchOutcome` today).

## Consequences

- Shell tickets that mutate files should declare capability `workspace.mutate` and go through the workspace manager (phased).
- IDE drive that writes files should prefer the same worktree when the plan is code-mutating (phased).
- Subactor `development_defect` bridge uses Koru for **code repair only** — no Plesk/DNS mutation from Koru.
