# ADR-AD-001: Canonical namespaces (`coru` / `koru` / `koruide`)

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §3.1, PR1  
- **Related:** [`../../adr/adr-kide-001-koru-vs-koruide-boundary.md`](../../adr/adr-kide-001-koru-vs-koruide-boundary.md), `packages/coru/README.md`

## Context

The monorepo already ships multiple top-level packages (`koru`, `coru`, `koruide`, `korudsl`, `koruapi`, `korullm`, …) plus `.coru` / `.koru` runtime dirs. Without an ownership table, new modules land in the wrong package and registries multiply.

## Decision (proposed)

| Namespace / package | Owns | Must not own |
| --- | --- | --- |
| **`coru`** | Stable end-user CLI (`ensure`, `sync`, `lane`, thin `auto`) | Queue internals, scan apply, grant crypto |
| **`koru`** | Autonomy loop, Planfile queue, scan *proposals*, policy, ExecutionPlan orchestration | Low-level IDE injectors, VQL geometry |
| **`koruide`** | IDE control-plane (daemon, protocol, plugins) | Ticket prioritization, intent registry |
| **`koruvision` / vdisplay** | Screen truth, VQL parse, geometry | Drive policy / ticket lifecycle |

Runtime dirs: project state under `.planfile/.koru/`; prefer documenting `.coru` only as legacy/compat if still required.

## Consequences

- PR1 publishes an inventory + import-linter (or docs table) enforcing owners.
- New top-level packages require an ADR amendment.
- No runtime behavior change in the acceptance commit.
