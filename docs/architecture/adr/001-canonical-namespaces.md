# ADR-AD-001: Canonical namespaces (`coru` / `koru` / `koruide`)

- **Status:** Accepted
- **Date:** 2026-07-18  
- **Accepted:** 2026-07-19
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §3.1, PR1  
- **Related:** [`../../adr/adr-kide-001-koru-vs-koruide-boundary.md`](../../adr/adr-kide-001-koru-vs-koruide-boundary.md), `packages/coru/README.md`

## Context

The monorepo already ships multiple top-level packages (`koru`, `coru`, `koruide`, `korudsl`, `koruapi`, `korullm`, …) plus `.coru` / `.koru` runtime dirs. Without an ownership table, new modules land in the wrong package and registries multiply.

## Decision

| Namespace / package | Owns | Must not own |
| --- | --- | --- |
| **`coru`** | Stable end-user CLI (`ensure`, `sync`, `lane`, thin `auto`) | Queue internals, scan apply, grant crypto |
| **`koru`** | Autonomy loop, Planfile queue, scan *proposals*, policy, ExecutionPlan orchestration | Low-level IDE injectors, VQL geometry |
| **`koruide`** | IDE control-plane (daemon, protocol, plugins) | Ticket prioritization, intent registry |
| **`koruvision` / vdisplay** | Screen truth, VQL parse, geometry | Drive policy / ticket lifecycle |

Runtime dirs: project state under `.planfile/.koru/`; prefer documenting `.coru` only as legacy/compat if still required.

The machine-readable source of truth is
[`../autonomy-mutation-inventory.yaml`](../autonomy-mutation-inventory.yaml),
validated by
[`../../../schemas/autonomy-mutation-inventory.schema.json`](../../../schemas/autonomy-mutation-inventory.schema.json).
It assigns every import root to one of the four boundaries and inventories the
current autonomous side-effect entrypoints as
`actor → intent → capability → risk → executor → evidence`. `observed` means
the path still needs dispatcher/grant enforcement; `contracted` means the
current path already evaluates a capability contract.

## Consequences

- CI validates the inventory schema, unique identifiers, closed capability
  references, real entrypoint modules, and complete ownership of source roots.
- New top-level packages require an ADR amendment.
- New capability ids must be declared before code or an Intent Pack can use
  them; runtime model output can only reference an existing id.
- No runtime behavior change in the acceptance commit.
