# Package Extraction Plan (`src` -> `packages/*`)

Goal: make reusable parts independently versioned while keeping `coru` UX stable.

## Short answer

Yes, moving selected modules from `src` into `packages/*` is the right direction.
Do it incrementally, module-by-module, with compatibility shims and CI gates.

## Current state (top-level under `src`)

- `koru`
- `koruapi`
- `korudsl`
- `koruenv` (already extracted, stale leftovers should not be canonical)
- `koruide`
- `korullm`
- `korumesh`
- `koruobserve`
- `koruos` *(deprecated shim → `gillm.focus`; remove after two releases)*
- `koruvision`

## Extraction order (recommended)

1. `koruide`
Reason: clear boundary (IDE adapters and socket/control logic), already used by lane workflows.

2. `koruobserve`
Reason: observability concerns are separable and often reused across tools.

3. `koruvision`
Reason: optional capability with distinct dependencies (`mss`), good fit for optional package install.

4. `koruapi` and `korudsl`
Reason: CLI-facing APIs can become stable standalone tools with independent release cadence.

5. `korullm`
Reason: model/provider integration tends to churn; package boundary reduces blast radius.

6. `korumesh`
Reason: lower priority unless reused by multiple modules or need separate release lifecycle.

**Done:** `koruos` OS strategies moved to **`gillm.focus`** (external package). Legacy
``import koruos`` emits ``DeprecationWarning`` and redirects to gillm.

**Done:** GUI injection (`Injector`, `os_injector`, profiles) canonical in **`gillm.injection`**.
Legacy paths ``koru.autopilot.injector``, ``koru.autopilot.os_injector``, ``koruide.injector``,
``koruide.os_injector`` emit ``DeprecationWarning`` and redirect to gillm.

## Migration pattern per module

1. Create `packages/<name>/pyproject.toml` and move canonical code there.
2. Keep temporary compatibility wrappers in `src/<name>/` that re-export from package.
3. Add package-local tests in `packages/<name>/tests`.
4. Add dedicated CI workflow `.<github/workflows>/<name>-ci.yml`.
5. Update imports in monorepo to package namespace.
6. Remove wrappers only after two successful releases/smokes.

## Guardrails

- No fallback to stale in-repo implementations once package is canonical.
- Each extraction must keep CLI behavior stable from the `coru` perspective.
- Prefer one package extraction per ticket to keep rollback simple.

## User UX rule

`coru` remains the stable front door.
Backend package moves must not force users to learn new commands.
