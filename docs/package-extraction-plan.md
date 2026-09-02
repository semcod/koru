# Package Extraction Plan (map-driven, dependency-first)

> Updated 2026-09-02. The old rule “move `src` to `packages/*`” did not reduce
> the repository and encouraged parallel namespaces. The quantitative source
> of truth is now
> [`architecture/volume-reduction-plan.yaml`](architecture/volume-reduction-plan.yaml),
> backed by
> [`architecture/documentation-conformance.toon.yaml`](architecture/documentation-conformance.toon.yaml)
> and CI schema contracts.

Goal: reduce the Koru checkout and production surface while keeping the `koru`
and compatibility `coru` UX stable.

## Short answer

Move reusable mechanisms only to an existing, already-used dependency that owns
the capability. Moving code from `src/` to `packages/` in this repository is
not an extraction. Prefer deletion of generated state and duplicate namespaces,
then dependency-first releases with one compatibility release.

## Program progress

Order 10, `repository.generated_state`, is complete. The 49-file,
17,172,638-byte generated baseline is absent from the Git index, its versions
and digests remain in `config/artifact-registry.json`, and artifact workflow
run `33612230881` proved separate analysis, coverage and media publication.
Order 20, `runtime.shadow_packages`, was already complete; the next planned
local reduction is order 30, `namespaces.coru_koru_pairs`.

## Current state (top-level under `src`)

- `koru`
- `koruapi`
- `korudsl`
- `korumesh`
- `koruobserve`
- `koruos` *(compatibility shim → `gillm.focus`; remove after two releases)*
- `koruvision`

This list is enforced by
[`architecture/autonomy-mutation-inventory.yaml`](architecture/autonomy-mutation-inventory.yaml).
`koruenv` and `koruide` live under `packages/*/src`, while `korullm` is a
published core dependency declared in `pyproject.toml`; none is a current
top-level source root under `src/`.

## Previous extraction list (reclassified)

1. `koruide` — deferred. There is no `semcod/koruide` checkout and Koru core
   currently has 45 consumers of this namespace.

2. `koruobserve` — keep the Koru-specific process lifecycle; move only generic
   capture probing/diagnostics with the VDisplay extraction.

3. `koruvision` — replace its generic capture/provider stack with public
   `wronai/vdisplay` APIs; keep Koru-specific orchestration and mesh evidence.

4. `koruapi` and `korudsl` — keep. They are Koru facade/domain authority, not
   dependency mechanisms.

5. `korullm` — source-root extraction is complete: Koru imports the published
   `korullm>=0.1.0` dependency and must not recreate `src/korullm`. The
   remaining local `src/koru/tillm_bridge.py` adapter delegates shell-client
   mechanics to `semcod/tillm`; Koru keeps orchestration decisions and
   `ProposalEnvelope` validation.

6. `korumesh` — defer until a second non-Koru consumer establishes a protocol
   owner.

**Done:** `koruos` OS strategies moved to **`gillm.focus`** (external package). Legacy
``import koruos`` emits ``DeprecationWarning`` and redirects to gillm.

**Done:** GUI injection (`Injector`, `os_injector`, profiles) canonical in **`gillm.injection`**.
Legacy paths ``koru.autopilot.injector``, ``koru.autopilot.os_injector``, ``koruide.injector``,
``koruide.os_injector`` emit ``DeprecationWarning`` and redirect to gillm.

## Migration pattern per module

1. Add a versioned request/result contract and public API in the owner repo.
2. Pass owner-side contract tests and release that dependency.
3. Raise Koru's minimum version and run typed API versus legacy behavior in dual-run.
4. Keep one compatibility release with telemetry and no divergent fallback copy.
5. Delete the Koru implementation only after cross-repo E2E is green.
6. Regenerate the map and verify the quantitative budget in the volume DSL.

## Guardrails

- No fallback to stale in-repo implementations once package is canonical.
- Each extraction must keep CLI behavior stable from both `koru` and the
  compatibility `coru` entry point.
- A dependency may own *how*; Koru retains *whether/when/with which grant*.
- Do not claim ecosystem LOC reduction for code merely moved to another repo.
- Prefer one package extraction per ticket to keep rollback simple.

## User UX rule

`coru` remains the stable front door.
Backend package moves must not force users to learn new commands.
