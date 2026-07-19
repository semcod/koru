# ADR — autonomy & determinism (Koru)

**Cel:** krótkie ADR-y dla refaktoru autonomii/determinizmu.  
**Pełny plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md)  
**Zasada:** *borrow governance from Subactor, not AQL/OQL languages.*

| ADR | Temat | Status |
| --- | --- | --- |
| [AD-001](./001-canonical-namespaces.md) | Kanoniczne namespace’y `coru` / `koru` / `koruide` | **Accepted** (inventory DSL + CI) |
| [AD-002](./002-intent-capability-ssot.md) | Intent pack + capability contract jako SSOT | Proposed |
| [AD-003](./003-execution-plan-lifecycle.md) | Wspólny `ExecutionPlan` i lifecycle | Proposed |
| [AD-004](./004-grant-and-manifest.md) | Immutable manifest + execution grant | Proposed |
| [AD-005](./005-transactional-workspace.md) | Transakcyjne worktree / promote|rollback | **Accepted** (queue patch v1) |
| [AD-006](./006-remote-executor.md) | Zdalny executor (capability + mTLS) | Proposed |

**Powiązane ADR-y legacy (pozostają w `docs/adr/`):**

- [`adr-kide-001-koru-vs-koruide-boundary.md`](../../adr/adr-kide-001-koru-vs-koruide-boundary.md)
- [`adr-auto-002-autonomous-decision-llm.md`](../../adr/adr-auto-002-autonomous-decision-llm.md)

**Referencja Subactor (wzorce, nie kod):**  
`/home/tom/github/subactor/docs/architecture/adr/` (001–007 Accepted) — szczególnie grant/manifest (003) i verify DoD (004).

**Uwaga projektowa:** Accepted ≠ zaimplementowane. Evidence per PR w planie §6.
