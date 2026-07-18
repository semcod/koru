# ADR-AD-004: Immutable manifest + execution grant

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §2, PR8–PR10  
- **Subactor reference:** `subactor/docs/architecture/adr/003-approval-hitl-model.md` (HMAC grant, `plan_hash`, `jti`) — **pattern only**; local checkout `/home/tom/github/subactor/…`.

## Context

Koru mutations (queue shell, scan apply, IDE drive, repair) are gated by coarse flags and policy, not by a dry-run-bound artifact. Replay exists for observation, not anti-replay of grants.

## Decision (proposed)

1. **Dry-run** freezes an **immutable manifest** + `plan_hash` (canonical JSON over the intended effects). Apply must not re-scan freely.
2. **Execution grant** (short-lived HMAC) binds at least: `run_id`, `actor`, `intent_pack`, `plan_hash`, `artifact_sha256` (or workspace digest), `target`, `expires_at`, `risk_class`.
3. Risk classes mirror Subactor: `read_only` | `reversible` | `boundary` | `governance` with matching HITL rules.
4. **`jti`** store prevents replay; missing secret → fail-closed.
5. Master kill switch remains (env) but is **not** sufficient alone for mutate.

## Consequences

- Secrets never appear in tickets, grants body beyond refs, or NL logs.
- Crypto details can follow Subactor ADR-003 field order with Koru-specific issuer (`koru` control / local service).
