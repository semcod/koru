# koru — Documentation

This directory contains the full documentation for **koru** — a closed-loop
refactor automation system for multi-repo workspaces.

- **[`roadmap-competition.md`](./roadmap-competition.md)** (PL) — porównanie z Grit, Moderne/OpenRewrite, Gitar, Git AutoReview i kierunek roadmapy.
- **[`recipes/README.md`](./recipes/README.md)** (PL) — szkic katalogu przepisów koru (propozycje, przykłady YAML).
- **[`ci-github.md`](./ci-github.md)** (PL) — szablon thin CI na GitHub Actions (`koru-ci.yml`).
- **[`ci-gitlab.md`](./ci-gitlab.md)** (PL) — ten sam smoke na GitLab CI (przykład w `examples/ci/gitlab-ci.example.yml`).
- **[`quickstart-10min.md`](./quickstart-10min.md)** — krótka ścieżka: instalacja, `koru --init`, CI, pierwszy ticket.

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
7. **[`agent-backends-architecture.md`](./agent-backends-architecture.md)** —
   layered map: plugin+socket, MCP, vendor CLIs, OS injectors (no single
   universal “wake LLM” API).
8. **[`autopilot-quickstart.md`](./autopilot-quickstart.md)** — how to
   drive your IDE's LLM chat from a terminal (`koru autopilot`), including
   plugin install repair, version drift checks, and strict runtime gates.
   Companion design doc: [`autopilot-design.md`](./autopilot-design.md);
   formal control-plane protocol: [`IDE_PROTOCOL.md`](./IDE_PROTOCOL.md);
   open items in [`autopilot-roadmap.md`](./autopilot-roadmap.md).
9. **[`ide-router.md`](./ide-router.md)** — how koru chooses the active IDE
   lane and keeps VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed separated.
10. **[`ide-isolation.md`](./ide-isolation.md)** (PL) — granice izolacji lane/socket,
    dlaczego nie ma pełnego sandboxu między IDE i jak ustawić hardening,
    żeby uniknąć cross-lane chat/event leakage.
11. **[`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md)** (PL) — autonomia
   koru vs Cursor IDE: luka funkcjonalna i checklista wdrożeniowa.
12. **[`autodiagnostics-auto-repair.md`](./autodiagnostics-auto-repair.md)** —
   implemented doctor, guided repair, autopilot host repair, and safe
   autonomous diagnostic-ticket loops.
13. **[`project-discovery-strategy.md`](./project-discovery-strategy.md)** —
   how an idle planfile queue triggers whole-project `code2llm` discovery,
   `planfile` ticket generation, and explicit IDE LLM status handoff.
14. **[`../packages/coru/README.md`](../packages/coru/README.md)** — thin client
   layer (`coru`) that keeps user-facing commands stable while `koruenv` + `koru`
   internals can be refactored independently.
15. **[`package-extraction-plan.md`](./package-extraction-plan.md)** — practical,
   incremental plan for moving selected modules from `src` to `packages/*`.

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
| **EXECUTE** | Windsurf / Cursor, shell LLM clients via SLLM, vallm, prefact | [`llm-tools/cursor`](./llm-tools/cursor/), [`llm-tools/vallm`](./llm-tools/vallm/), [`llm-tools/prefact`](./llm-tools/prefact/) |
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
