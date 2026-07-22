# koru — Documentation

This directory contains the full documentation for **koru** — a closed-loop
refactor automation system for multi-repo workspaces.

**Project root:** [`README.md`](../README.md) · **Release notes:** [`CHANGELOG.md`](../CHANGELOG.md) · **Open work:** [`TODO.md`](../TODO.md)

## Choose a path

| Need | Start here | Continue with |
|---|---|---|
| Install and run Koru | [`quickstart-10min.md`](./quickstart-10min.md) | [`cli-examples.md`](./cli-examples.md) |
| Operate an autonomous agent | [`agent-guide.md`](./agent-guide.md) | [`autopilot-quickstart.md`](./autopilot-quickstart.md) |
| Understand queue lifecycle and retries | [`planfile-execution-gateway.md`](./planfile-execution-gateway.md) | [`planfile-llm-guide.md`](./planfile-llm-guide.md) |
| Run Subactor development repair | [`subactor-development-repair-template.md`](./subactor-development-repair-template.md) | [`architecture/dependency-boundary-inventory.yaml`](./architecture/dependency-boundary-inventory.yaml) |
| Change autonomy architecture | [`architecture/autonomy-determinism-refactor-plan.md`](./architecture/autonomy-determinism-refactor-plan.md) | [`architecture/adr/README.md`](./architecture/adr/README.md) |

`TODO.md` is only for active work. Completed implementation and documentation
changes are recorded in `CHANGELOG.md`.

## Architecture (autonomy / determinism)

- **[`architecture/autonomy-determinism-refactor-plan.md`](./architecture/autonomy-determinism-refactor-plan.md)** — Subactor-like governance for Koru (intent → grant → verify); ~18 PRs; **docs only until PR1**.
- **[`architecture/adr/`](./architecture/adr/README.md)** — ADR stubs AD-001…AD-006 (namespaces, SSOT, ExecutionPlan, grant/manifest, worktree, remote mTLS).

- **[`koru-fleet.md`](./koru-fleet.md)** — `koru fleet bootstrap` / `up` / `ls`:
  multi-project workspace init + one supervisor for every koru-managed project
  running a `koru autonomous up` child per koru-managed project on the
  machine (mermaid + ASCII architecture diagrams, systemd deployment, and
  the `--replace-existing` cross-project-kill bug it surfaced).
- **[`roadmap-competition.md`](./roadmap-competition.md)** (PL) — porównanie z Grit, Moderne/OpenRewrite, Gitar, Git AutoReview i kierunek roadmapy.
- **[`recipes/README.md`](./recipes/README.md)** (PL) — szkic katalogu przepisów koru (propozycje, przykłady YAML).
- **[`ci-github.md`](./ci-github.md)** (PL) — szablon thin CI na GitHub Actions (`koru-ci.yml`).
- **[`ci-gitlab.md`](./ci-gitlab.md)** (PL) — ten sam smoke na GitLab CI (przykład w `examples/ci/gitlab-ci.example.yml`).
- **[`quickstart-10min.md`](./quickstart-10min.md)** — krótka ścieżka: instalacja, `koru --init`, CI, pierwszy ticket.
- **[`pipeline-design.md`](./pipeline-design.md)** — closed-loop stages (detect→plan→execute→verify→heal), flat pipeline YAML, autonomy layout, design-debt hotspots.
- **[`docker-e2e-testing.md`](./docker-e2e-testing.md)** — Docker / shell e2e map: suites, installs, IDE-matrix stubs, Xvfb, **noVNC lab** (`docker/novnc/`).
- **[`goal-tags-and-releases.md`](./goal-tags-and-releases.md)** — why git tags advance while GitHub Releases can stick on an old version (goal + `create_on_tag`).
- **[`llm-provider-configuration.md`](./llm-provider-configuration.md)** (PL) — globalny wybór
  klienta tillm (`aider`, `claude-code`), providera API (`openrouter`, `z.ai`, …),
  modeli per rola i pliki `.env` / `urirun/.env`.
- **[`desktop-uri-orchestration.md`](./desktop-uri-orchestration.md)** (PL) — MCP bridge do nlp2uri: desktop, getv://, SystemMap URI, orchestracja z planfile.
- **[`ide-control-architecture.md`](./ide-control-architecture.md)** (PL) — jak działa sterowanie IDE: koruide, pluginy, fallbacki i rola nlp2uri.
- **[`plans/nlp2uri-koruide-integration-refactor-plan.md`](./plans/nlp2uri-koruide-integration-refactor-plan.md)** (PL) — plan refaktoryzacji integracji nlp2uri ↔ kontrola IDE Koru.

## Reading order

For LLM agents starting a session in a koru-driven repository:

1. **[`agent-guide.md`](./agent-guide.md)** — full agent workflow guide
   (ticket lifecycle, validation gates, anti-patterns, troubleshooting).
   **Start here** if you are an LLM agent (Windsurf, Cursor, Claude Code).
2. **[`planfile-llm-guide.md`](./planfile-llm-guide.md)** — ticket-driven
   development with the `planfile` CLI. Covers ticket schema, labels,
   priority, sprint workflow.
3. **[`planfile-execution-gateway.md`](./planfile-execution-gateway.md)** —
   design for making `planfile.yaml` the execution gateway for shell, MCP,
   API, human, and LLM actors.
4. **[`cli-examples.md`](./cli-examples.md)** — practical Taskfile + CLI
   examples for every common scenario (bootstrap, fix-alert, OpenRouter
   lane, multi-repo refactor).
5. **[`llm-tools/`](./llm-tools/)** — per-tool docs and install scripts
   for every component in the koru pipeline.
6. **[`semcod-ticket-sources.md`](./semcod-ticket-sources.md)** — which semcod
   analysis tools can generate Planfile tickets directly or through Koru
   artifact adapters.
7. **[`llm-provider-configuration.md`](./llm-provider-configuration.md)** —
   global LLM/client/provider selection for headless drive (`KORU_TILLM_*`,
   `TILLM_PROVIDER`, tillm store, if-uri `urirun/.env`).
8. **[`agent-backends-architecture.md`](./agent-backends-architecture.md)** —
   layered map: plugin+socket, MCP, vendor CLIs, OS injectors (no single
   universal “wake LLM” API).
9. **[`autopilot-quickstart.md`](./autopilot-quickstart.md)** — how to
   drive your IDE's LLM chat from a terminal (`koru autopilot`), including
   plugin install repair, version drift checks, and strict runtime gates.
   Companion design doc: [`autopilot-design.md`](./autopilot-design.md);
   formal control-plane protocol: [`IDE_PROTOCOL.md`](./IDE_PROTOCOL.md);
   open items in [`autopilot-roadmap.md`](./autopilot-roadmap.md).
10. **[`ide-router.md`](./ide-router.md)** — how koru chooses the active IDE
   lane and keeps VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed separated.
11. **[`ide-isolation.md`](./ide-isolation.md)** (PL) — granice izolacji lane/socket,
    dlaczego nie ma pełnego sandboxu między IDE i jak ustawić hardening,
    żeby uniknąć cross-lane chat/event leakage.
12. **[`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md)** (PL) — autonomia
   koru vs Cursor IDE: luka funkcjonalna i checklista wdrożeniowa.
13. **[`photo-vql-jetbrains-wayland.md`](./photo-vql-jetbrains-wayland.md)** (PL) —
   pętla **vdisplay + koru photo-VQL** (observe→decide→act→verify), skrypty
   `koru-drive-photo-vql.sh`, guardy, PyCharm/Wayland — **użyj tego do chat drive na pulpicie**.
14. **[`autodiagnostics-auto-repair.md`](./autodiagnostics-auto-repair.md)** —
   implemented doctor, guided repair, autopilot host repair, and safe
   autonomous diagnostic-ticket loops.
15. **[`project-discovery-strategy.md`](./project-discovery-strategy.md)** —
   how an idle planfile queue triggers whole-project `code2llm` discovery,
   `planfile` ticket generation, and explicit IDE LLM status handoff.
16. **[`../packages/coru/README.md`](../packages/coru/README.md)** — thin client
   layer (`coru`) that keeps user-facing commands stable while `koruenv` + `koru`
   internals can be refactored independently.
17. **[`package-extraction-plan.md`](./package-extraction-plan.md)** — practical,
   incremental plan for moving selected modules from `src` to `packages/*`.
18. **[`architecture/dependency-boundary-inventory.yaml`](./architecture/dependency-boundary-inventory.yaml)** —
   validated DSL for dependency ownership, typed boundary contracts and the
   dependency-first extraction order across `semcod/*`, `wronai/*` and TestQL.

For human operators / DevOps:

1. **[`../README.md`](../README.md)** — top-level project description and
   architecture overview.
2. **[`ci-github.md`](./ci-github.md)** / **[`ci-gitlab.md`](./ci-gitlab.md)** — minimalne pipeline’y smoke (Epic 2).
3. **[`llm-tools/README.md`](./llm-tools/README.md)** — tool catalog and
   when to use which.
4. **IDE matrix workflows** — top-level README documents Docker Linux coverage
   plus native Ubuntu/Windows/macOS smoke workflows for all supported IDE lanes.
5. **[`../templates/`](../templates/)** — copy-paste config templates for
   `pyqual.yaml`, `redup.toml`, `redsl.yaml`, `regix.yaml`.

## The two-mode philosophy

koru deliberately splits work into two modes:

| Mode | Purpose | LLM | Cost |
|---|---|---|---|
| **Default: IDE-native** | normal ticket-driven dev work | your IDE's LLM (Windsurf/Cursor/Claude Code) | $0 (already paid for IDE) |
| **Opt-in: OpenRouter automation lane** | scheduled smoke tests, headless auto-fix, infra validation | OpenRouter (`redsl improve`, `vallm validate --semantic`) | metered |

This split is what makes koru economically viable for daily development:
the heavy lifting happens in your IDE LLM (already a sunk cost), while
the OpenRouter lane is reserved for things that genuinely benefit from
out-of-band, automated, headless processing.

## Pipeline phases

| Phase | Tools | Doc |
|---|---|---|
| **DETECT** | Prometheus alertmanager, blackbox-exporter, TestQL probes, redup, regix | [`llm-tools/redup`](./llm-tools/redup/), [`llm-tools/regix`](./llm-tools/regix/), [`llm-tools/testql`](./llm-tools/testql/) |
| **PLAN** | planfile (ticket backlog), healing-webhook (auto-tickets) | [`llm-tools/planfile`](./llm-tools/planfile/), [`planfile-llm-guide.md`](./planfile-llm-guide.md) |
| **EXECUTE** | Windsurf / Cursor, shell LLM clients via TILLM, vallm, prefact | [`llm-tools/cursor`](./llm-tools/cursor/), [`llm-tools/vallm`](./llm-tools/vallm/), [`llm-tools/prefact`](./llm-tools/prefact/) |
| **VERIFY** | regix, ruff, pytest, TestQL, vallm tier-1/2 | [`llm-tools/regix`](./llm-tools/regix/), [`llm-tools/vallm`](./llm-tools/vallm/) |
| **HEAL** | healing-webhook, retry strategies | (see reference deployment c2004) |
| **AUTO** *(opt-in)* | redsl improve, llx fix | [`llm-tools/redsl`](./llm-tools/redsl/), [`llm-tools/llx`](./llm-tools/llx/) |

## Quick reference for agents

```bash
# Entry point — pick the highest-priority ticket
task tickets:next

# Read ticket details
planfile ticket show PLF-XXX

# Edit code (your IDE's LLM does the work)
# ...

# Validate locally (no LLM API calls)
task quality:regix:local
task test
task monitor:probe

# Commit (pre-commit hooks do final validation)
git commit

# Mark done
task tickets:done -- PLF-XXX
```

## Caveats

- The **default ticket-driven path** is more stable than the **opt-in
  OpenRouter automation lane**. If `task quality:improve` or
  `task monitor:test-heal` fails but `redsl improve <path>` works locally,
  treat it as an infrastructure problem (compose / webhook wiring), not a
  product bug.
- Configuration in `templates/` is from a real production deployment
  (`maskservice/c2004`). Adjust `redup.toml` `max_groups` / `max_lines` to
  your project size before adopting blindly.

## Full catalog (`docs/*`)

Complete index of documentation in this directory. Start with
[`README.md`](../README.md) for the project overview and
[`CHANGELOG.md`](../CHANGELOG.md) for release notes.

### Onboarding & operators

| Doc | Summary |
|-----|---------|
| [`quickstart-10min.md`](./quickstart-10min.md) | Install, `koru --init`, first ticket, CI smoke |
| [`agent-guide.md`](./agent-guide.md) | LLM agent workflow (tickets, gates, anti-patterns) |
| [`cli-examples.md`](./cli-examples.md) | Taskfile + CLI recipes |
| [`ci-github.md`](./ci-github.md) | Thin GitHub Actions smoke template |
| [`ci-gitlab.md`](./ci-gitlab.md) | GitLab CI equivalent |
| [`wizard-ux-spec.md`](./wizard-ux-spec.md) | `koru wizard` UX specification |
| [`roadmap-competition.md`](./roadmap-competition.md) | Competitive landscape (PL) |
| [`recipes/README.md`](./recipes/README.md) | Future recipe catalog sketch (PL) |

### Planfile & tickets

| Doc | Summary |
|-----|---------|
| [`planfile-llm-guide.md`](./planfile-llm-guide.md) | Ticket schema, labels, sprint workflow |
| [`planfile-execution-gateway.md`](./planfile-execution-gateway.md) | `planfile.yaml` as execution gateway |
| [`semcod-ticket-sources.md`](./semcod-ticket-sources.md) | Tools that generate planfile tickets |
| [`project-discovery-strategy.md`](./project-discovery-strategy.md) | Idle queue → code2llm discovery |
| [`post-run-verify.md`](./post-run-verify.md) | Post-ticket verification checklist |

### Autopilot & IDE lanes

| Doc | Summary |
|-----|---------|
| [`autopilot-quickstart.md`](./autopilot-quickstart.md) | `koru autopilot` production setup |
| [`autopilot-design.md`](./autopilot-design.md) | Control-plane design |
| [`autopilot-daemon-runtime.md`](./autopilot-daemon-runtime.md) | Daemon lifecycle & sockets |
| [`autopilot-roadmap.md`](./autopilot-roadmap.md) | Open autopilot items |
| [`IDE_PROTOCOL.md`](./IDE_PROTOCOL.md) | Formal plugin↔daemon protocol |
| [`ide-router.md`](./ide-router.md) | Lane selection (Cursor/VS Code/…) |
| [`ide-isolation.md`](./ide-isolation.md) | Lane/socket isolation (PL) |
| [`ide-control-architecture.md`](./ide-control-architecture.md) | IDE control stack: koruide, plugins, nlp2uri (PL) |
| [`ide-control-surfaces.md`](./ide-control-surfaces.md) | IDE command surfaces |
| [`ide-command-api-map.md`](./ide-command-api-map.md) | Command API map (+ [`ide-command-api-map.yaml`](./ide-command-api-map.yaml)) |
| [`ide-strategy-contract.md`](./ide-strategy-contract.md) | Strategy contract per IDE |
| [`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md) | Koru autonomy vs Cursor (PL) |
| [`photo-vql-jetbrains-wayland.md`](./photo-vql-jetbrains-wayland.md) | vdisplay photo-VQL loop, chat drive (PL) |
| [`autodiagnostics-auto-repair.md`](./autodiagnostics-auto-repair.md) | Doctor, repair, diagnostic loops |
| [`mcp-ide-flow.md`](./mcp-ide-flow.md) | MCP ↔ IDE integration flow |
| [`llm-provider-configuration.md`](./llm-provider-configuration.md) | Global LLM/client/provider config (PL) |
| [`agent-backends-architecture.md`](./agent-backends-architecture.md) | Plugin, MCP, CLI, OS injector layers |
| [`../packages/coru/README.md`](../packages/coru/README.md) | `coru` client (`calibration`, `doctor`, `auto`) |

### DSL, API & architecture

| Doc | Summary |
|-----|---------|
| [`koru-drive-dsl.md`](./koru-drive-dsl.md) | Per-step autopilot drive trace (`[DSL]` lines) |
| [`koru-control-command-dsl.md`](./koru-control-command-dsl.md) | Control-command DSL |
| [`korudsl-koruapi.md`](./korudsl-koruapi.md) | Dashboard / koruapi module map |
| [`koru_auto_vs_observe_up.md`](./koru_auto_vs_observe_up.md) | `koru auto` vs `koru observe up` |
| [`autonomy-interface-surface.md`](./autonomy-interface-surface.md) | Autonomy public interfaces |
| [`cqrs-event-sourcing.md`](./cqrs-event-sourcing.md) | CQRS + event sourcing in koru |
| [`deployment-events.md`](./deployment-events.md) | `DeploymentEvent` telemetry |
| [`hexagonal-poc.md`](./hexagonal-poc.md) | Hexagonal architecture POC |
| [`local-service.md`](./local-service.md) | Local service deployment notes |
| [`desktop-uri-orchestration.md`](./desktop-uri-orchestration.md) | nlp2uri MCP bridge (PL) |
| [`plans/nlp2uri-koruide-integration-refactor-plan.md`](./plans/nlp2uri-koruide-integration-refactor-plan.md) | nlp2uri ↔ koruide refactor plan (PL) |
| [`package-extraction-plan.md`](./package-extraction-plan.md) | `packages/*` extraction plan |
| [`architecture/dependency-boundary-inventory.yaml`](./architecture/dependency-boundary-inventory.yaml) | Validated ownership/contracts/extraction DSL |

### Tooling & pipeline

| Doc | Summary |
|-----|---------|
| [`llm-tools/README.md`](./llm-tools/README.md) | Per-tool install docs (planfile, regix, testql, …) |
| [`../testql-scenarios/README.md`](../testql-scenarios/README.md) | Scenario index (WUP-safe vs manual, desktop calibration) |
| [`ai-tool-support-roadmap-2026.md`](./ai-tool-support-roadmap-2026.md) | 2026 AI tool registry roadmap |
| [`ai-tool-registry-2026.yaml`](./ai-tool-registry-2026.yaml) | Machine-readable tool registry |

### ADRs & specs

| Doc | Summary |
|-----|---------|
| [`adr/adr-kide-001-koru-vs-koruide-boundary.md`](./adr/adr-kide-001-koru-vs-koruide-boundary.md) | koru ↔ koruide boundary |
| [`adr/adr-auto-002-autonomous-decision-llm.md`](./adr/adr-auto-002-autonomous-decision-llm.md) | Autonomous decision LLM |
| [`specs/kide-002-koruide-api-v1.md`](./specs/kide-002-koruide-api-v1.md) | koruide API v1 |
| [`specs/kide-003-koruide-api-v2.md`](./specs/kide-003-koruide-api-v2.md) | koruide API v2 (planned) |
| [`interfaces/koru-interface-registry.yaml`](./interfaces/koru-interface-registry.yaml) | Interface registry |

### Plans & refactoring

| Doc | Summary |
|-----|---------|
| [`refactoring/REFACTORING_PLAN.md`](./refactoring/REFACTORING_PLAN.md) | KIDE refactor phases |
| [`refactoring_plan.md`](./refactoring_plan.md) | Legacy refactoring notes |
| [`refactor/ide-bridge-2026.md`](./refactor/ide-bridge-2026.md) | IDE bridge refactor (2026) |
| [`refactor/autonomy-refactor-continuation-plan-2026-05.md`](./refactor/autonomy-refactor-continuation-plan-2026-05.md) | Autonomy refactor continuation |
| [`plans/capture-providers-refactor.md`](./plans/capture-providers-refactor.md) | Capture provider refactor |
| [`plans/observation-mesh-plan.md`](./plans/observation-mesh-plan.md) | Observation mesh plan |
| [`plans/nlp2uri-koruide-integration-refactor-plan.md`](./plans/nlp2uri-koruide-integration-refactor-plan.md) | nlp2uri IDE control integration (PL) |
