# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Autopilot: drive an IDE's LLM chat from the terminal

- **New subsystem `koru.autopilot`** — `src/koru/autopilot/{protocol,
  injector, ide, daemon, client, cli_command}.py`. Brokers between IDE
  plugins and CLI clients over a local unix socket
  (`$XDG_RUNTIME_DIR/koru-autopilot.sock`, mode `0600`,
  `SO_PEERCRED`-enforced same-UID). Wire protocol is NDJSON with a 1
  MiB per-line cap and a fixed type whitelist (see
  [`docs/autopilot-design.md`](docs/autopilot-design.md)).
- **New CLI verb `koru autopilot`** with sub-actions `daemon`, `drive`,
  `status`, `shutdown`, `ide-list`, `doctor`. Wired in
  `src/koru/cli.py` alongside the existing `task`, `agent`, `serve`,
  `scan`, `gate`, `queue`, `gc` subcommand routes.
- **Auto-handoff** — when an IDE-side plugin emits `session.ended`,
  the daemon builds the canonical koru brief
  (`koru.context.build_context` + `render_markdown_handoff`) and
  injects it back into the chat as `chat.send`. Anti-loop cooldown
  via `--handoff-cooldown` (default 2 s); fully opt-outable with
  `--no-handoff`. Real-world smoke shipped a 5388-char brief in
  one round trip.
- **Three injection backends** (auto-picked by session type): plugin
  socket → `xdotool` (X11) → `wtype` / `ydotool` (Wayland). Per-IDE
  submit keymap (`Return` for VS Code family, `Ctrl+Return` for
  JetBrains).
- **IDE process scan** (`src/koru/autopilot/ide.py`) recognises
  Windsurf, VS Code / VSCodium / code-oss, Cursor, JetBrains IDEs
  (idea / pycharm / webstorm / phpstorm / goland / clion / rubymine),
  and Zed via `/proc/<pid>/comm` + `cmdline` matching.
- **VS Code / Windsurf / Cursor extension scaffolding**
  (`plugins/koru-autopilot-vscode/`, TypeScript): connects to the
  daemon, status bar indicator, paste-and-submit injection, auto-
  reconnect.
- **JetBrains plugin stub** (`plugins/koru-autopilot-jetbrains/`) —
  Phase 3 placeholder. JetBrains users currently get keyboard-sim.
- **Documentation:** new
  [`docs/autopilot-quickstart.md`](docs/autopilot-quickstart.md),
  [`docs/autopilot-design.md`](docs/autopilot-design.md), and
  [`docs/autopilot-roadmap.md`](docs/autopilot-roadmap.md); README
  section "Autopilot — drive your IDE from the terminal" added under
  the no-args brief description.
- **Tests:** 53 new in `tests/test_autopilot_{protocol,injector,ide,
  daemon,cli}.py` (protocol round-trip, backend selection per
  session type, IDE process scan, in-thread daemon round-trip,
  plugin-forward path, handoff happy path / disabled / cooldown,
  CLI smoke). Full suite: **343 passed, 0 regressions**.

### Changed — Autopilot refactor pass 1

- **R14 / TS compile fix** (`plugins/koru-autopilot-vscode/src/extension.ts`)
  — `Thenable<T>` has no `.catch`, which broke `npm run compile`.
  New `runCommand()` helper wraps each `vscode.commands.executeCommand`
  call in `Promise.resolve(...)` + `try/catch`, returns a `boolean`,
  and logs failures.
- **R10 / reconnect jitter** — the VS Code extension's reconnect timer
  now uses `3000 ± 500 ms` instead of a fixed 3 s, so when the daemon
  restarts with N IDE windows open they no longer dog-pile in the same
  window.
- **R8 (partial) / clipboard restore** — `injectChat` now snapshots
  the clipboard *before* the `try` block and restores it in a `finally`,
  so a thrown paste/submit no longer strands our payload in the
  user's clipboard. The long-term plan (switch to
  `vscode.chat.sendMessage` once it stabilises) is still open.
- **R1 / handler-dispatch indirection** — the module-level
  `_HANDLERS` dict and the seven `_h_*` thin wrappers are gone.
  `AutopilotDaemon._build_handler_table()` now builds a per-instance
  `{type → bound method}` dispatch table; `_dispatch` calls the bound
  method directly.
- **R9 / `_handle_drive` split** — the plugin-path and
  keyboard-simulation branches now live in dedicated
  `_drive_via_plugin` / `_drive_via_keyboard` methods, each testable
  in isolation.
- **R2 / test plumbing** — extracted `_DaemonHarness` context manager,
  `_LineReader` (stateful NDJSON parser), `_connect_plugin()` and
  `_assert_no_more_data()` helpers in
  `tests/test_autopilot_daemon.py`. Every socket-level test now uses
  the helpers; future tests will need ~5 lines instead of ~20.

Full suite still **343 passed, 0 regressions** after these changes.
Real-world smoke (`koru autopilot daemon` + scripted plugin) still
delivers the 5388-char brief in one round trip.

### Added — On-change gates triad (wup + regix + testql)

- **New brief section "On-change gates"** — `render_markdown_handoff()`
  now emits a dedicated table whenever a project has any of the three
  on-change gate packages configured. Detection markers (in
  `agents.detect_project_environment()`):
  - `wup_yaml`         → `wup.yaml` at project root
  - `regix_yaml`       → `regix.yaml` at project root
  - `testql_scenarios` → `testql-testing/scenarios/` or `testql-scenarios/`
  Section lists each gate, whether it's configured, its role, and the
  exact command to invoke it. Skipped silently when none are present
  (no noise for non-adopting projects).
- **New template** `templates/wup.yaml.template` — base file watcher
  config with debounce, gitignore-aware excludes, 2-layer test strategy
  (quick: ≤3 testql endpoints; full: only on quick-fail), and CPU
  throttling. Placeholder `__PROJECT__` substituted by the install task.
- **New install tasks**:
  - `task template:install:wup PROJECT=<name>` — copies wup.yaml
    template, substitutes `__PROJECT__`, prints next-steps (map-deps,
    testql-endpoints, watch).
  - `task template:install:on-change-gates PROJECT=<name>` — composite:
    wup.yaml + regix.yaml + reminder for testql scenarios.
- **New workflow doc** `workflows/on-change-gates.md` — full description
  of the wup→testql→regix cycle with ASCII diagram, package
  responsibilities table, bootstrap recipe, and failure-mode escape
  hatches. Documents the rationale: behaviour probe + metric gate +
  blame report = continuous per-save analogue of `quality:gate`.
- **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`)
  — read-only manual triad invocation: detect → regix gates → testql
  smoke → wup status → aggregate decision. Used by the agent before
  `planfile ticket complete`.

### Added — Onboarding & diagnostics (Phase 5)
- `koru --init [--from <yaml>] [--force]` — one-command project bootstrap.
  Creates `.planfile/{config.yaml, sprints/current.yaml}`,
  `.planfile/.koru/policy.yaml` (commented stub with safe defaults), and
  appends `.planfile/.koru/` to `.gitignore` (idempotent). Without
  `--from`, generates a 2-ticket starter scaffold (`STARTER-001` shell,
  `STARTER-002` human). Policy stub is never overwritten on `--force`.
- `koru` (no args) — bare invocation now emits the markdown LLM brief
  (`--context --format markdown`). If the project is uninitialised, the
  brief leads with **⚠ Setup required** and the exact `koru --init`
  command. Self-service commands swap to init-only vocabulary until
  the project is bootstrapped.
- `koru --doctor [--format json|text]` — read-only project diagnostics.
  Probes 8 checks: `git_repo`, `planfile_binary`, `planfile_config`,
  `planfile_sprints`, `runtime_dir`, `policy_yaml`, `gitignore`,
  `ci_command`. Exit 1 on failure, 0 on warnings-only. Human-readable
  text by default; `--format json` for machine consumption.
- Pre-flight check in `build_context`: planfile subprocess is skipped
  when the project is uninitialised (prevents planfile from auto-creating
  a half-state `config.yaml`).

### Added — Queue runner (Phases 3.5 / 3.6 / 4)
- `koru --queue --interactive` — when the next runnable ticket is a
  `human` executor, koru collects the answer on stdin (multi-line,
  Ctrl-D submit, Ctrl-C cancel) and completes the ticket via
  `planfile ticket complete` with the answer recorded in `--note` and
  `--result-json`. No more switching to the planfile CLI to satisfy
  human prompts. (`5a28201`)
- `koru --queue --loop --max-iterations N` — drains the queue
  ticket-by-ticket until idle / human input needed (without
  `--interactive`) / unsupported executor / planfile error / cap hit.
  Failed tickets do **not** halt the loop. Live progress is rendered
  with status glyphs (✓/✗/⏸/•). Composes with `--interactive` to
  drain shell + human tickets in one invocation. (`ca90446`)
- `executor.kind=llm` — Phase 4 of the gateway design is live. LLM
  tickets call any OpenAI-compatible chat-completion endpoint
  (default OpenRouter, falls back to OpenAI via `KORU_LLM_ENDPOINT`),
  capture the assistant's text as `stdout`, and embed `llm_model` +
  `llm_usage` (token counts) in the result-json for cost tracking.
  Supports `inputs.{prompt, llm_model, llm_endpoint, system_prompt,
  llm_max_tokens, llm_temperature, response_schema,
  llm_timeout_seconds}` and forwards `KORU_LLM_HTTP_REFERER` /
  `KORU_LLM_X_TITLE` to OpenRouter. Refuses to call without an API
  key (returns a clear, actionable error). (`8858505`)
- `LlmRunResult`, `QueueLoopResult`, `run_planfile_queue_loop` —
  added to the public `koru` package API.
- `docs/cli-examples.md` — three new sections:
  *Answer human-input tickets interactively*,
  *Drain the queue with --loop*,
  *Auto-answer tickets with an LLM (executor.kind=llm)*,
  each with worked PLF-067-style examples and an env-var matrix.
- 14 new unit tests (3 interactive + 6 loop + 5 LLM) +
  1 fix to `test_unsupported_executor_kind` (now uses `mcp` since
  `llm` is supported). Total: **50/50 unit tests + 6/6 smoke e2e +
  9/9 bootstrap e2e**.

### Added — Earlier today
- `docs/llm-tools/sumd/` — dokumentacja + `install.sh` dla `sumd`/`sumr`
  (LLM refactor snapshots). Siódmy tool w matrix.
- `templates/sumr-refresh.sh.template` — debounced wrapper generujący
  `SUMR.md` tylko gdy stale (≥25 commitów lub ≥7 dni).
- `templates/git-hooks/{post-merge,post-commit,install.sh}.template` —
  portable git hooks: branch-aware post-merge (async bg), lightweight
  post-commit (hint-only), idempotentny installer z marker-based
  uninstall.
- `templates/sumr-weekly.yml.template` — GitHub Actions workflow
  (weekly Monday 04:00 UTC + manual dispatch) z PR-botem
  (`peter-evans/create-pull-request@v7`, branch `automation/sumr-refresh`).
- `workflows/sumr-refresh-loop.md` — 3-layer workflow doc z 9-krokowym
  deployment checklistem dla docelowego repo.
- `docs/llm-tools/redeploy/` — dokumentacja + `install.sh` dla `redeploy`
  (multi-target deployment via markpact specs). Ósmy tool w matrix.
- `templates/redeploy/local/deployment.md.template` — local Docker
  Compose markpact spec (dev) z plugin-based testing (process_control,
  http_check, hardware_diagnostic).
- `templates/redeploy/device/{manifest.yaml,migration.md,diagnose.md}.template`
  — multi-phase SSH device deployment: hardware-init / deploy / diagnose
  / detect / fix-* fazy. Podman Quadlet rootless + Docker Compose.
- `workflows/redeploy-multi-device.md` — 9-krokowy deployment checklist
  + multi-device topologie (single device, multi device same strategy,
  multi strategy jak c2004) + drift loop z `doql adopt`.
- `docs/llm-tools/goal/` — dokumentacja + `install.sh` dla `goal`
  (automated git push + smart conventional commits + release workflow).
  Koru ma już `goal.yaml` (510 linii), brakowało doc.
- `docs/llm-tools/doql/` — dokumentacja + `install.sh` dla `doql`
  (declarative IaC, companion sumd/redeploy). Pokrywa `app.doql.less`,
  `doql adopt`, drift detection, format adapters.
- `docs/llm-tools/costs/` — dokumentacja + `install.sh` dla `costs`
  (zero-config AI cost tracker, badge w README.md per commit).
- `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3`
  (layered infra observation: physical/os/runtime/service/endpoint/
  business). Companion redeploy/doql dla deeper device snapshots.
- `docs/llm-tools/README.md` — sekcja **ORCHESTRATION** w mapie warstw
  (goal/doql/costs), 4 nowe wiersze w tabeli config, install loop +=
  goal, doql, costs, op3.

#### Fala 2 — observability + bootstrap
- `templates/observability/` — kompletny stack monitoring:
  - `docker-compose.observability.yml.template` (10 services: prometheus,
    grafana, loki, alertmanager, blackbox, node-exporter, cadvisor,
    promtail, uptime-kuma, healing-webhook)
  - `prometheus/prometheus.yml.template` + `rules/app-alerts.yml.template`
    z generic alert rules (EndpointDown, HighErrorRate, HighMemoryUsage,
    DuplicationCheck, RegressionDetected)
  - `alertmanager/alertmanager.yml.template` z webhook routing
  - `README.md` — index + manual install
- `templates/.windsurf/` — bootstrap dla Windsurf agent:
  - `rules.md.template` (workflow + tool table + anti-patterns +
    citation format)
  - `mcp_config.example.json.template` (3 MCP servers: planfile, testql, redup)
- `templates/github-workflows/{version-drift,code-quality}.yml.template` —
  GH Actions: SSOT version drift check + ruff/lizard/regix/redup/vallm
  quality gate + pytest job.
- `templates/scripts/check-version-drift.sh.template` — Python helper
  validating VERSION ↔ pyproject.toml/package.json/__init__.py/.env
- `templates/.pre-commit-config.yaml.template` — generic hygiene + ruff
  + version-drift gate + regix advisory + redsl-gate (commented)
- `docs/llm-tools/toonic/` — dokumentacja + `install.sh` dla `toonic`
  (universal TOON format converter, LLM-optimized compact YAML).
- `workflows/observability-bootstrap.md` — 9-krokowy deployment
  checklist + alert healing strategies + customization guide +
  troubleshooting.

#### Fala 3 — specialized tools + runtime templates
- `docs/llm-tools/protogate/` — migration tool dla legacy systems
  (bounded slices), built on SUMD + DOQL + testql + Taskfile.
- `docs/llm-tools/rebuild/` — historical deployment analysis +
  code intelligence (git history walker, dashboard at :7821,
  rebuild restore w healing-webhook).
- `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract
  markpact:ref, generate Mermaid diagrams, validate links).
- `docs/llm-tools/metrun/` — execution intelligence + bottleneck
  detection (turn raw cProfile data w actionable fix suggestions).
- `templates/redeploy/runtime/quadlet/` — Podman Quadlet templates
  (rootless systemd) — companion dla redeploy device deployment.
  Pliki: `app-backend.container`, `app-frontend.container`, `app.network`.
- `templates/python-monorepo/shared-compat/` — compatibility shim
  pattern dla monorepo z `packages/<APP>-shared-py/`. Helper z
  `export_backend_shared_module()` + `export_connect_module()`.
  88% size reduction w shim files (na bazie c2004).

### Changed
- `Taskfile.yml` → `install:tools` obejmuje teraz `sumd`, `code2llm`,
  `doql`, `redeploy`, `goal`, `costs`, `op3`, `toonic` (13 narzędzi total).
- `Taskfile.yml` → 5 nowych `template:install:*` tasków
  (observability, windsurf, ci, precommit + already-existing redeploy/sumr).
- `Taskfile.yml` → 8 nowych `monitor:*` tasków (net, up, up:lite, down,
  status, logs, probe, reload-prometheus).
- `README.md` + `docs/llm-tools/README.md` — toonic dodane do list.
- `Taskfile.yml` → nowe taski: `template:install:sumr`,
  `template:install:redeploy`,
  `quality:sumr:{status,auto,refresh,install-hook,uninstall-hook}`,
  `deploy:{plan,dry,local,device,diagnose,resume,drift}`.
- `README.md` + `docs/llm-tools/README.md` — sumd/sumr i redeploy dodane
  do list narzędzi i matrix konfiguracji.

## [0.1.21] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_ide.py
- Update tests/test_autopilot_injector.py
- Update tests/test_autopilot_protocol.py

### Other
- Update uv.lock

## [0.1.20] - 2026-05-11

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/README.md
- Update docs/autopilot-quickstart.md
- Update docs/autopilot-roadmap.md

### Test
- Update tests/test_autopilot_daemon.py

### Other
- Update .gitignore
- Update plugins/koru-autopilot-vscode/out/extension.js
- Update plugins/koru-autopilot-vscode/out/extension.js.map
- Update plugins/koru-autopilot-vscode/package-lock.json
- Update plugins/koru-autopilot-vscode/src/extension.ts
- Update uv.lock

## [0.1.19] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.18] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.17] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.16] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_e2e.py

### Other
- Update uv.lock

## [0.1.15] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py

### Other
- Update uv.lock

## [0.1.14] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.13] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.12] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_gc.py
- Update tests/test_queue_clean.py

### Other
- Update uv.lock

## [0.1.11] - 2026-05-11

### Docs
- Update README.md
- Update workflows/on-change-gates.md

### Test
- Update tests/test_context.py
- Update tests/test_gate.py

### Other
- Update .planfile/sprints/current.yaml
- Update VERSION
- Update templates/scripts/check-taskfile-escapes.sh.template

## [0.1.11] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.10] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.9] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_dotenv_loader.py
- Update tests/test_scan.py

### Other
- Update uv.lock

## [0.1.8] - 2026-05-11

### Docs
- Update README.md

### Test
- Update tests/test_context.py
- Update tests/test_planfile_queue.py
- Update tests/test_serve.py

### Other
- Update .planfile/sprints/current.yaml
- Update uv.lock

## [0.1.7] - 2026-05-11

### Docs
- Update README.md

### Other
- Update uv.lock

## [0.1.6] - 2026-05-11

### Docs
- Update README.md

## [0.1.5] - 2026-05-11

### Docs
- Update .windsurf/workflows/koru-gate.md
- Update CHANGELOG.md
- Update README.md
- Update docs/llm-tools/README.md
- Update workflows/on-change-gates.md

### Other
- Update Taskfile.yml
- Update templates/wup.yaml.template
- Update uv.lock

## [0.1.4] - 2026-05-10

### Docs
- Update README.md

### Test
- Update tests/e2e/init.sh
- Update tests/test_loop.py

### Other
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update pipeline.yaml
- Update uv.lock

## [0.1.3] - 2026-05-10

### Docs
- Update README.md

### Test
- Update tests/test_agents.py
- Update tests/test_runtime.py
- Update tests/test_tasks.py

### Other
- Update uv.lock

## [0.1.2] - 2026-05-10

### Docs
- Update README.md
- Update SUMR.md
- Update docs/llm-tools/README.md
- Update docs/llm-tools/costs/README.md
- Update docs/llm-tools/costs/install.sh
- Update docs/llm-tools/doql/README.md
- Update docs/llm-tools/doql/install.sh
- Update docs/llm-tools/goal/README.md
- Update docs/llm-tools/goal/install.sh
- Update docs/llm-tools/mdflow/README.md
- ... and 27 more files

### Test
- Update testql-scenarios/generated-cli-tests.testql.toon.yaml
- Update testql-scenarios/generated-from-pytests.testql.toon.yaml
- Update tests/test_bootstrap.py
- Update tests/test_watch.py

### Other
- Update .gitignore
- Update .redeployignore
- Update Taskfile.yml
- Update app.doql.less
- Update examples/bootstrap.planfile.yaml.new
- Update project/map.toon.yaml
- Update redeploy/device/manifest.yaml
- Update scripts/git-hooks/install.sh
- Update scripts/git-hooks/post-commit
- Update scripts/git-hooks/post-merge
- ... and 25 more files

## [0.1.1] - 2026-05-10

### Docs
- Update README.md

### Other
- Update .env.example
- Update .idea/.gitignore
- Update .idea/inspectionProfiles/Project_Default.xml
- Update .idea/inspectionProfiles/profiles_settings.xml
- Update .idea/koru-loop.iml
- Update .idea/modules.xml
- Update .idea/pyProjectModel.xml
- Update .idea/vcs.xml
- Update uv.lock

