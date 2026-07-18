# ADR-AD-006: Remote executor (capability + mTLS)

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §3.9, PR16  
- **Subactor pattern:** delegate by contract coverage; connector executes only allowed ops.

## Context

Koru IDE control is primarily local (UDS / plugins). Fleet and multi-host scenarios need a remote worker, but an open remote shell would bypass capability contracts.

## Decision (proposed)

1. Remote executor accepts **only** Capability Dispatcher requests authenticated with **mTLS** (client cert ↔ actor id).
2. Peer’s capability contract is loaded server-side; requests outside the contract are denied.
3. Grants remain required for mutate; remote node verifies grant + `plan_hash` locally.
4. Lab prototype before production; default deploy remains local-only.

## Consequences

- No SSH “full shell” autonomy path as a substitute for the dispatcher.
- Separate from Subactor SFTP/PR6 track (different product, different trust domain).
