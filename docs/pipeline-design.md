# Pipeline design

How koru moves work through **detect → plan → execute → verify → heal →
repeat**, and where those stages live in the repo.

## Closed loop (product view)

```
detect        plan           execute         verify         heal
─────────     ─────────      ─────────       ─────────      ─────────
scan /        planfile       IDE drive /     regix /        doctor /
redup /       tickets        tillm /         pytest /       guided repair /
TestQL        recipes        queue loop      TestQL /       autonomous
                                             post-run
```

Entry points operators usually care about:

| Stage | CLI / surface | Code (primary) |
| ----- | ------------- | -------------- |
| Bootstrap | `koru --init`, `koru wizard` | `koru.init`, `koru.wizard` |
| Config | `koru configure` | `koru.configurator` package |
| Detect / scan | `koru scan`, idle-queue discovery | `koru.scan`, `koru.code2llm_discovery` |
| Plan | planfile tickets, recipes | external `planfile` CLI + `koru.planfile_queue` |
| Execute | `koru --queue --loop`, `koru auto`, `koru autonomous` | `koru.autonomous`, `koru.autonomy.*` |
| Drive IDE | `koru autopilot` | `koru.autopilot.*`, `koruide.*` |
| Verify | doctor, gates, post-run | `koru.doctor*`, `koru.post_run_verify` |
| Heal | `koru doctor --fix/--repair` | `koru.doctor`, healing webhook |

## Flat pipeline YAML

`koru` can import a **flat** multi-repo pipeline into planfile tickets:

```bash
koru bootstrap --from pipeline.yaml
```

Validation and materialization live in `koru.bootstrap`
(`validate_flat_pipeline`, `import_flat_pipeline`,
`materialize_to_planfile`). Practical examples:
[cli-examples.md](./cli-examples.md#bootstrap-a-project-from-a-flat-pipeline-yaml).

## Autonomy / operator pipeline

Long-running closed-loop automation is orchestrated under
`src/koru/autonomy/`:

- **Cycle** — queue scan → drive → post-drive → gate → sleep
  (`autonomy/cycle/*`)
- **Operator** — WUP, plugin wait, runtime, onboarding
  (`autonomy/operator/*`)
- **Orchestrator** — auto-pipeline profiles
  (`autonomy/orchestrator/`)

See also:

- [agent-guide.md](./agent-guide.md) — agent session workflow
- [planfile-execution-gateway.md](./planfile-execution-gateway.md) —
  planfile as execution gateway
- [autodiagnostics-auto-repair.md](./autodiagnostics-auto-repair.md) —
  doctor + safe repair loops
- [project-discovery-strategy.md](./project-discovery-strategy.md) —
  idle queue → `code2llm` discovery
- [package-extraction-plan.md](./package-extraction-plan.md) — moving
  modules from `src/` into `packages/*`

## Design debt (from `project/analysis.toon.yaml`)

Static analysis (code2llm, refreshed **2026-07-17**):

- **REFACTOR:** split 18 high-CC methods (CC>15); god-module
  `configurator.py` is already gone (now `src/koru/configurator/` package).
- **Largest hotspots** that still own pipeline I/O:

| Hotspot | Approx. size | Note |
| ------- | ------------ | ---- |
| `src/koru/integrations/vdisplay_client.py` | ~7.5k LOC | Partial split under `integrations/vdisplay/`; keep re-exports |
| `packages/coru/src/coru/cli.py` | ~3.7k LOC | Thin client surface; split carefully |
| `src/koru/scan.py` | ~1.6k LOC | Discovery / ticket emission |
| `src/koru/configurator` | package | **Done** — was god-module `configurator.py` |

Prefer incremental extractions with compatibility shims (same pattern as
`configurator/` and `integrations/vdisplay/`). See
`project/evolution.toon.yaml` for ranked NEXT actions.

## Related

- Root product overview: [README.md](../README.md)
- Docs index: [README.md](./README.md)
- Recipes sketch: [recipes/README.md](./recipes/README.md)
