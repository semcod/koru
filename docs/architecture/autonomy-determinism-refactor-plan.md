# Koru — autonomy & determinism refactor plan

**Status:** historical architecture roadmap; PR1 namespace ownership is delivered, later units require current-code review.
**Date:** 2026-07-18  
**Reviewed against code:** 2026-09-01
**Repo:** [`semcod/koru`](https://github.com/semcod/koru)  
**Current index baseline:** [`documentation-conformance.toon.yaml`](./documentation-conformance.toon.yaml), generated from the checked-out code with `autogrammar/sumd`.
**Provenance:** this document reconstructs the original 2026-07-18 assessment; current-state claims are reviewed against the repository and the conformance DSL above.

**Related (Subactor — borrow governance, not languages):**

| Subactor document | Pattern to reuse |
| --- | --- |
| [`subactor/docs/architecture/autonomy-recommended-solution.md`](https://github.com/subactor/docs/blob/main/architecture/autonomy-recommended-solution.md) | Controlled capability catalog; LLM selects, does not invent ops |
| [`subactor/docs/architecture/intent-orchestration-and-fallbacks.md`](https://github.com/subactor/docs/blob/main/architecture/intent-orchestration-and-fallbacks.md) | Intent packs as SSOT of *goal* |
| [`subactor/docs/architecture/adr/003-approval-hitl-model.md`](https://github.com/subactor/docs/blob/main/architecture/adr/003-approval-hitl-model.md) | Immutable manifest + signed grant + replay (`jti`) |
| [`subactor/docs/architecture/adr/004-publish-definition-of-done.md`](https://github.com/subactor/docs/blob/main/architecture/adr/004-publish-definition-of-done.md) | Verify as mandatory success gate |
| [`subactor/docs/plans/autonomy-implementation-roadmap.md`](https://github.com/subactor/docs/blob/main/plans/autonomy-implementation-roadmap.md) | Phased PR units; dual-run migration |

**Separate track:** Subactor **PR6 (Paramiko/SFTP + capability readiness)** is *infrastructure for docs.subactor.com publish*. It does **not** block or merge into this Koru refactor. Do not couple commits, grants, or DoD criteria across the two repos.

**ADR index (this repo):** [`adr/README.md`](./adr/README.md)

---

## 1. Assessment

### 1.1 Subactor (governance stronger than ops readiness)

Subactor already separates **Control**, **AQL**, **OQL**, **URI Process**, **connector**, and **LLM Gateway**. The model does not approve or execute plans; concrete URIs must fit an actor contract. The LLM is a typed parser / project generator with local validation and deterministic fallback. Worth adopting in Koru:

- delegation by **contract coverage** (only capabilities the actor may use),
- a **remote executor** behind mTLS, scoped by capability,
- **dry-run → immutable plan → signed grant → apply → verify → rollback**.

Do **not** copy AQL/OQL as new languages into Koru. Map the same *governance shapes* onto Koru’s existing DSL, protobuf (`koru.control.v1`, etc.), JSON Schema, Planfile, and policy YAML.

### 1.2 Koru (functionally autonomous, architecturally fragmented)

Koru already runs a rich closed loop: policy engine, decision arbiter,
checkpoints, replay, post-run verify, observability, repair, supervisor,
Planfile/MCP, and many IDE adapters. The 2026-09-01 `sumd` baseline reports
1,469 indexed modules, 264,786 lines, mean CC 3.0 and **no dependency cycles**,
but **339 critical functions** and concentrated hotspots.

**Problem is not “missing autonomy features”.** It is:

1. **No single execution contract** shared by cycle, operator, repair, and replay.
2. **Parallel registries / package names** (`koru`, `coru`, `koruide`, `korudsl`, `koruapi`, …) without one capability SSOT.
3. **Hotspot concentration** — especially
   `src/koru/integrations/vdisplay_client.py` (6,577 lines), the main CLI,
   `scan.py`, `autonomous.py`, and cycle/operator pipelines — where planning
   still reaches subprocess/GUI.

### 1.3 Honest gap matrix

| Area | Already in Koru | Missing / fragmented |
| --- | --- | --- |
| Policy | `.planfile/.koru/policy.yaml`, `policy.py`, `autonomy/policy_engine.py` | Not bound to a versioned capability catalog; no CI ⊆-check vs packs |
| Decision | `decision_arbiter.py`, ADR AUTO-002 planning LLM | Arbiter emits ad-hoc actions, not a shared `ExecutionPlan` state machine |
| Checkpoints | `autonomous_checkpoint`, session state under `.planfile/.koru/` | Checkpoint ≠ immutable manifest + `plan_hash` |
| Replay | `koru replay`, drive replay sidecars, control DSL | Replay is observational; no grant/`jti` anti-replay for mutations |
| Verify | `post_run_verify`, `verification_engine.py` | Soft reopen/block; not hard DoD with evidence bundle + rollback |
| Planfile / MCP | Queue gateway, MCP tools, ticket lifecycle | Tickets are work items, not capability-authorized execution units |
| IDE control | `koruide`, probe ladder, plugins | Ladder exists but planning layer still spawns GUI/subprocess paths |
| Namespaces | `coru` thin CLI; `koru*` packages; AD-001 inventory enforced by CI | Distribution and compatibility layers can still drift after ownership changes |
| Remote exec | Local daemon / UDS | No capability-scoped mTLS remote executor |

---

## 2. Target model (borrow governance, not languages)

```text
Intent Pack
  → Capability Contract
  → Execution Plan
  → Immutable Manifest + Execution Grant
  → Capability Dispatcher
  → Transactional Workspace
  → Evidence + Verify
  → Promote | Rollback
```

| Stage | Koru mapping (reuse existing tech) | Subactor analogue |
| --- | --- | --- |
| **Intent Pack** | Versioned JSON/YAML under e.g. `schemas/intent-packs/` or `.koru/intent-packs/`; phrases + `situation_schema` + `required_capabilities`; **no** inline ALLOW | Intent pack registry |
| **Capability Contract** | JSON Schema / protobuf capability ids (`drive.focus`, `queue.shell`, `scan.apply`, `workspace.promote`, …); actor/lane allowlists | AQL contract (concept only) |
| **Execution Plan** | Unify today’s cycle/operator/repair plans into one `ExecutionPlan` + lifecycle enums (protobuf or JSON Schema) | URI Process / recipe |
| **Immutable Manifest + Grant** | Dry-run produces file/action manifest + `plan_hash`; short-lived HMAC grant binds actor, pack, hash, target, risk class | PR5a/5b/5c |
| **Capability Dispatcher** | Sole path to shell/IDE/MCP/remote; planning layer **never** calls subprocess/GUI directly | Connector + control |
| **Transactional Workspace** | Git worktree (or equivalent) for code mutations; promote only after verify | Release dir + activate |
| **Evidence + Verify** | Bundle: git diff digest, gate commands, drive trace ids, screenshots refs; fail → reopen/rollback | Origin + public verify |
| **Promote or Rollback** | Merge/apply worktree or discard; ticket status reflects outcome | Activate previous / DNS rollback |

**Non-goals**

- Inventing AQL/OQL dialects inside Koru.
- Big-bang rewrite of `autonomous.py` in one PR.
- Coupling to Subactor Plesk/SFTP/docs.subactor.com work.

---

## 3. Key stages (ordered)

1. **Formal ADRs** + canonical `coru` / `koru` (/ `koruide`) ownership.
2. **Single SSOT** for intents and capabilities.
3. **Shared `ExecutionPlan` lifecycle** for cycle, operator, repair, replay.
4. **Remove direct subprocess/GUI from planning** (dispatcher only).
5. **Dry-run, manifest, grant, anti-replay.**
6. **Transactional worktree** for code changes.
7. **Deterministic ladder:** plugin → semantic VDisplay → trusted VQL → escalate.
8. **Hard verify**, evidence bundle, rollback.
9. **Remote executor** limited by capability + mTLS.

---

## 4. Hotspot split (proposed ownership)

Grounded in [`boundary-refactoring-proposal.md`](../boundary-refactoring-proposal.md), ADR KIDE-001, and index hotspots.

| Hotspot | Today | Target owner | Split outcome |
| --- | --- | --- | --- |
| `integrations/vdisplay_client.py` | VQL parse + geometry + actuation glue | **vdisplay** / `koruvision` for screen truth; koru keeps drive policy | ~60–70% line reduction in koru |
| `cli.py` / CLI dispatch | Monolithic entry | **`coru`** = stable UX; **`koru`** = orchestration APIs | Thin `coru` already exists — finish ownership ADR |
| `scan.py` | Detect + suggest + apply side effects | Scan = **propose** intents only; apply via dispatcher + grant | Planning cannot mutate |
| `autonomous.py` / cycle / operator | Loop + heuristics + drive | Emit/consume `ExecutionPlan`; side effects via dispatcher | One lifecycle |
| Probe / photo-VQL ladder | Scattered in drive + plugins | Documented ladder policy; no blind injector without capability | Matches stage 7 |
| Repair / supervisor | `coru.repair_registry`, fleet | Capability-tagged repair intents | Same grant/verify path |

---

## 5. ExecutionPlan lifecycle (shared)

```text
proposed
  → resolved          # intent pack + slots validated
  → preflight_passed  # capabilities ready
  → dry_run_passed    # manifest + plan_hash frozen
  → authorized        # grant issued
  → applying
  → applied
  → verified          # evidence DoD
  → completed         # promoted

# failure / control
preflight_failed | dry_run_failed | apply_failed
applied_unverified | rollback_started | rolled_back
needs_human | failed
```

APIs and MCP tools must not collapse this to a single boolean `ok`. Cycle, operator, repair, and `koru replay` all advance the **same** state machine (adapters only differ in intent sources).

---

## 6. PR sequence (~18 units)

**Convention:** “PR” = reversible implementation unit (commit series). This repo ships by **commit + push**; do **not** open GitHub pull requests for the autonomy track unless a human asks.

| PR | Scope | Depends |
| -- | --- | --- |
| **0** | This plan + ADR stubs (docs only) — **this commit** | — |
| **1** | Accept ADR-AD-001 (namespaces); inventory packages/`import` graph; CI drift note for `coru` vs `koru*` | 0 |
| **2** | Intent pack JSON Schema + registry loader (dual-run with legacy prompts/phrases) | 1 |
| **3** | Capability contract registry + CI ⊆ check (pack requires ⊆ actor allow) | 2 |
| **4** | Shared `ExecutionPlan` schema (JSON Schema and/or protobuf) + serializers | 1 |
| **5** | Wire cycle → ExecutionPlan (read-only / dual-run; no behavior change) | 4 |
| **6** | Wire operator + repair + replay onto same lifecycle | 5 |
| **7** | Capability Dispatcher façade; ban new direct `subprocess`/GUI from planning modules (lint/import-linter) | 3, 6 |
| **8** | Dry-run → immutable manifest + `plan_hash` for queue mutate / scan apply | 7 |
| **9** | Signed execution grant (HMAC) + expire + binding checks | 8 |
| **10** | Grant `jti` replay store (fail-closed) | 9 |
| **11** | Transactional git worktree workspace for code-mutating tickets | 8 |
| **12** | VDisplay/VQL ladder policy as data (plugin → semantic → trusted VQL → escalate) | 7 |
| **13** | Evidence bundle schema + hard verify gate (extends post_run_verify) | 11 |
| **14** | Promote / rollback of worktree + ticket status semantics | 13 |
| **15** | Extract remaining VQL/geometry from `vdisplay_client` per boundary proposal | 12 |
| **16** | Remote executor prototype: mTLS + capability allowlist (lab only) | 7, 9 |
| **17** | Failure-injection suite green; remove dual-run shims; docs DoD | 10–16 |

### Delivered first implementation unit

**PR1 — Canonical namespace inventory + ADR-AD-001 acceptance — delivered.**
Ownership is frozen (`coru` = thin stable client; `koru` = orchestration;
`koruide` = IDE control-plane), and
[`autonomy-mutation-inventory.yaml`](./autonomy-mutation-inventory.yaml) plus
its CI contract rejects undeclared source roots. Later units in this historical
sequence must be selected from current repository evidence rather than assumed
unfinished from their original PR number.

---

## 7. Risk matrix

| Risk | Class | Mitigation |
| --- | --- | --- |
| Dual registries diverge during migration | High | Dual-run compare (`pack_id`, slots, capabilities); CI blocks new inline resolvers |
| Grant crypto / secret mishandling | High | Fail-closed; secrets never in tickets/logs; lab fallback documented |
| Worktree promote races with human IDE edits | Medium | Lease + dirty check; `needs_human` on conflict |
| Ladder change breaks Wayland/X11 field setups | Medium | Feature flag; keep legacy path behind capability `drive.legacy_injector` |
| Scope creep into Subactor SFTP/docs | Medium | Explicit separate track (this doc §header) |
| Oversized hotspot PRs | Medium | Cap PR15 to mechanical moves already clustered by CC cleanup |
| Planning LLM invents capabilities | High | LLM may select pack + fill slots only (`llm_policy` like Subactor) |

---

## 8. Definition of Done (autonomy track)

A mutate plan may report **success** only when:

1. Intent resolved from **registry** (not ad-hoc URI/shell invented by LLM).
2. Required capabilities ⊆ actor contract; preflight green.
3. Dry-run produced **immutable manifest** + `plan_hash`.
4. Valid **execution grant** consumed (no replay).
5. Side effects went only through **Capability Dispatcher**.
6. Code changes (if any) lived in **transactional workspace** then **promoted**.
7. **Evidence bundle** present; configured verify commands pass.
8. On verify fail → **rollback** or `needs_human` / ticket — never silent `ok`.

Read-only / advisory flows may stop at `dry_run_passed` without grant.

---

## 9. Test & failure-injection matrix

### Registry / contract

- Phrase in pack resolves identically from CLI, MCP, and autonomous cycle.
- Removing a phrase removes it from all paths.
- LLM/`planning_llm` cannot return unknown `pack_id` or free-form shell.
- Invalid situation slots rejected.

### Lifecycle / dispatcher

- Cycle, operator, repair, replay advance the same state enum.
- Planning module import of `subprocess` / raw injector → lint failure.
- Legacy recipes keep halt-on-error until explicitly migrated.

### Manifest / grant

- Apply without kill-switch / grant → deny.
- Grant wrong `plan_hash` / target / expired / replayed `jti` → deny.
- Second apply with same `jti` → zero mutation.

### Workspace / verify

- Dirty main tree blocks promote; worktree discard restores clean state.
- Verify fail after apply → rollback + ticket; status ≠ completed.
- Evidence bundle missing required keys → fail-closed.

### Failure injection (mandatory before PR17)

| Injection | Expected |
| --- | --- |
| Kill dispatcher mid-apply | `apply_failed`; no partial promote |
| Corrupt manifest between dry-run and apply | `plan_hash_mismatch` |
| Replay grant | `apply_grant_replay` |
| Drop plugin, force VQL ladder | Escalation path only; no blind inject without capability |
| Fake green verify (wrong evidence) | Detected by digest mismatch |
| mTLS peer without capability | Remote exec deny |

---

## 10. Relationship to existing Koru docs

| Doc | Role vs this plan |
| --- | --- |
| [`adr/adr-auto-002-…`](../adr/adr-auto-002-autonomous-decision-llm.md) | Planner/arbiter — becomes *input* to ExecutionPlan, not a parallel executor |
| [`adr/adr-kide-001-…`](../adr/adr-kide-001-koru-vs-koruide-boundary.md) | IDE boundary — prerequisite to dispatcher purity |
| [`boundary-refactoring-proposal.md`](../boundary-refactoring-proposal.md) | Hotspot extraction (esp. vdisplay) |
| [`planfile-execution-gateway.md`](../planfile-execution-gateway.md) | Tickets remain work queue; grants authorize *how* they mutate |
| [`post-run-verify.md`](../post-run-verify.md) | Evolves into hard evidence DoD (PR13) |
| [`pipeline-design.md`](../pipeline-design.md) | Closed-loop stages align with target model |

---

## 11. Verdict

Koru does not need “more autonomy features.” It needs **Subactor-grade
governance boundaries** expressed in **Koru’s existing DSL / protobuf / JSON
Schema**, with one execution contract and unified registries. Subactor PR6
(SFTP) stays on its own publish track. PR1 is complete; any next implementation
unit must be chosen from current tests, tickets and
[`documentation-conformance.toon.yaml`](./documentation-conformance.toon.yaml),
not solely from this historical ordering.
