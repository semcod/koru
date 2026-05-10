# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

