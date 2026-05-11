# koru

Closed-loop automation across semcod/* repositories.

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Interfaces](#interfaces)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Release Management (`goal.yaml`)](#release-management-goalyaml)
- [Code Analysis](#code-analysis)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Intent](#intent)

## Metadata

- **name**: `koru`
- **version**: `0.1.24`
- **python_requires**: `>=3.12`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, goal.yaml, .env.example, project/(2 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.24;
}

dependencies {
  runtime: pyyaml>=6.0;
  dev: "pytest>=8.0, ruff>=0.11, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60";
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="koru"] {

}

workflow[name="default"] {
  trigger: manual;
  step-1: run cmd=task --list-all;
}

workflow[name="version"] {
  trigger: manual;
  step-1: run cmd=echo "koru v{{.KORU_VERSION}}";
}

workflow[name="install"] {
  trigger: manual;
  step-1: run cmd=pip install -e .;
}

workflow[name="install:dev"] {
  trigger: manual;
  step-1: run cmd=pip install -e ".[dev]" || pip install -e .;
}

workflow[name="install:tools"] {
  trigger: manual;
  step-1: run cmd=pip install planfile regix redup vallm prefact pfix sumd code2llm doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun;
  step-2: run cmd=echo "✓ Core tools installed (16). For LLM-backed tools (redsl, llx, aider) install separately.";
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -v {{.CLI_ARGS}};
}

workflow[name="test:fast"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -q;
}

workflow[name="lint"] {
  trigger: manual;
  step-1: run cmd=python3 -m ruff check src tests;
}

workflow[name="lint:fix"] {
  trigger: manual;
  step-1: run cmd=python3 -m ruff check src tests --fix;
}

workflow[name="loop"] {
  trigger: manual;
  step-1: run cmd=koru --workspace "{{.WORKSPACE}}" --include "{{.INCLUDE}}" --command "{{.COMMAND}}";
}

workflow[name="queue:run"] {
  trigger: manual;
  step-1: run cmd=koru --queue --project "{{.PROJECT}}" --actor "{{.ACTOR}}" {{if eq .DRY_RUN "true"}}--dry-run{{end}};
}

workflow[name="queue:watch"] {
  trigger: manual;
  step-1: run cmd=koru --watch --ws-url "{{.WS_URL}}" {{if .MAX_EVENTS}}--max-events "{{.MAX_EVENTS}}"{{end}};
}

workflow[name="queue:autoloop"] {
  trigger: manual;
  step-1: run cmd=PROJECT="{{.PROJECT}}" \
ACTOR="{{.ACTOR}}" \
QUEUE_NAME="{{.QUEUE_NAME}}" \
MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
ENABLE_SCAN="{{.ENABLE_SCAN}}" \
ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
bash scripts/koru-autoloop.sh;
}

workflow[name="quality:regix"] {
  trigger: manual;
  step-1: run cmd=regix gate;
}

workflow[name="quality:redup"] {
  trigger: manual;
  step-1: run cmd=redup scan . --min-lines 10;
}

workflow[name="quality:redup:check"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redup-check.sh "{{.PATH | default \".\"}}";
}

workflow[name="quality:vallm"] {
  trigger: manual;
  step-1: run cmd=vallm validate -f "{{.FILE}}";
}

workflow[name="quality:vallm:semantic"] {
  trigger: manual;
  step-1: run cmd=vallm validate -f "{{.FILE}}" --semantic -v;
}

workflow[name="quality:sumr:status"] {
  trigger: manual;
  step-1: run cmd=scripts/sumr-refresh.sh --status;
}

workflow[name="quality:sumr:auto"] {
  trigger: manual;
  step-1: run cmd=scripts/sumr-refresh.sh;
}

workflow[name="quality:sumr:refresh"] {
  trigger: manual;
  step-1: run cmd=scripts/sumr-refresh.sh --force;
}

workflow[name="quality:sumr:install-hook"] {
  trigger: manual;
  step-1: run cmd=bash scripts/git-hooks/install.sh {{.HOOK | default "post-merge"}};
}

workflow[name="quality:sumr:uninstall-hook"] {
  trigger: manual;
  step-1: run cmd=bash scripts/git-hooks/install.sh --uninstall;
}

workflow[name="tickets:next"] {
  trigger: manual;
  step-1: run cmd=planfile ticket next;
}

workflow[name="tickets:list"] {
  trigger: manual;
  step-1: run cmd=planfile ticket list --status open --format yaml;
}

workflow[name="tickets:show"] {
  trigger: manual;
  step-1: run cmd=planfile ticket show "{{.TID}}";
}

workflow[name="tickets:done"] {
  trigger: manual;
  step-1: run cmd=planfile ticket update "{{.TID}}" --status done;
}

workflow[name="tickets:export"] {
  trigger: manual;
  step-1: run cmd=bash scripts/planfile-export-prompt.sh "{{.TID}}";
}

workflow[name="template:list"] {
  trigger: manual;
  step-1: run cmd=ls templates/;
}

workflow[name="template:install"] {
  trigger: manual;
  step-1: run cmd=cp templates/pyqual.yaml.template ./pyqual.yaml;
  step-2: run cmd=cp templates/redup.toml.template ./redup.toml;
  step-3: run cmd=cp templates/redsl.yaml.template ./redsl.yaml;
  step-4: run cmd=cp templates/regix.yaml.template ./regix.yaml;
  step-5: run cmd=cp templates/llx.toml.template ./llx.toml;
  step-6: run cmd=cp templates/llx.yaml.template ./llx.yaml;
  step-7: run cmd=cp templates/prefact.yaml.template ./prefact.yaml;
  step-8: run cmd=echo "✓ All templates copied. Review and edit before committing.";
}

workflow[name="template:install:single"] {
  trigger: manual;
  step-1: run cmd=cp templates/{{.TPL}}.template ./{{.TPL}} && echo "✓ {{.TPL}} copied";
}

workflow[name="template:install:compose"] {
  trigger: manual;
  step-1: run cmd=cp templates/docker-compose.quality.yml.template ./docker-compose.quality.yml;
  step-2: run cmd=echo "✓ docker-compose.quality.yml copied. Review service definitions.";
}

workflow[name="template:install:sumr"] {
  trigger: manual;
  step-1: run cmd=mkdir -p scripts scripts/git-hooks .github/workflows;
  step-2: run cmd=cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh;
  step-3: run cmd=cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge;
  step-4: run cmd=cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit;
  step-5: run cmd=cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh;
  step-6: run cmd=cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml;
  step-7: run cmd=chmod +x scripts/sumr-refresh.sh scripts/git-hooks/post-merge scripts/git-hooks/post-commit scripts/git-hooks/install.sh;
  step-8: run cmd=grep -q '^\.sumr/$' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore;
  step-9: run cmd=echo "✓ SUMR stack installed. Next: task quality:sumr:install-hook (see workflows/sumr-refresh-loop.md)";
}

workflow[name="template:install:redeploy"] {
  trigger: manual;
  step-1: run cmd=mkdir -p redeploy/local redeploy/device;
  step-2: run cmd=cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md;
  step-3: run cmd=cp templates/redeploy/device/manifest.yaml.template    redeploy/device/manifest.yaml;
  step-4: run cmd=cp templates/redeploy/device/migration.md.template     redeploy/device/migration.md;
  step-5: run cmd=cp templates/redeploy/device/diagnose.md.template      redeploy/device/diagnose.md;
  step-6: run cmd=echo "✓ redeploy templates installed at redeploy/";
  step-7: run cmd=echo "  Next: substitute placeholders (see workflows/redeploy-multi-device.md Krok 3)";
  step-8: run cmd=echo "        rename redeploy/device/ → redeploy/<your-device>/";
  step-9: run cmd=echo "        sed -i 's/<APP_NAME>/myapp/g' redeploy/local/*.md redeploy/device/*";
}

workflow[name="template:install:observability"] {
  trigger: manual;
  step-1: run cmd=mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning;
  step-2: run cmd=cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml;
  step-3: run cmd=cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml;
  step-4: run cmd=cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml;
  step-5: run cmd=cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml;
  step-6: run cmd=echo "✓ Observability stack installed.";
  step-7: run cmd=echo "  Next: substitute <APP_NAME>/<APP_PORT> placeholders, then task monitor:up";
  step-8: run cmd=echo "  See: workflows/observability-bootstrap.md";
}

workflow[name="template:install:windsurf"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .windsurf;
  step-2: run cmd=cp templates/.windsurf/rules.md.template               .windsurf/rules.md;
  step-3: run cmd=cp templates/.windsurf/mcp_config.example.json.template .windsurf/mcp_config.example.json;
  step-4: run cmd=echo "✓ .windsurf/ installed.";
  step-5: run cmd=echo "  Next: substitute <APP_NAME>/<REPO_PATH>, then merge mcp_config into ~/.codeium/windsurf/mcp_config.json";
}

workflow[name="template:install:ci"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .github/workflows;
  step-2: run cmd=cp templates/github-workflows/version-drift.yml.template   .github/workflows/version-drift.yml;
  step-3: run cmd=cp templates/github-workflows/code-quality.yml.template    .github/workflows/code-quality.yml;
  step-4: run cmd=mkdir -p scripts;
  step-5: run cmd=cp templates/scripts/check-version-drift.sh.template       scripts/check-version-drift.sh;
  step-6: run cmd=chmod +x scripts/check-version-drift.sh;
  step-7: run cmd=echo "✓ CI templates installed.";
  step-8: run cmd=echo "  Next: ensure VERSION file at repo root + commit + push";
}

workflow[name="template:install:precommit"] {
  trigger: manual;
  step-1: run cmd=cp templates/.pre-commit-config.yaml.template .pre-commit-config.yaml;
  step-2: run cmd=echo "✓ .pre-commit-config.yaml installed.";
  step-3: run cmd=echo "  Next: substitute <APP_NAME>, then: pip install pre-commit && pre-commit install";
}

workflow[name="template:install:wup"] {
  trigger: manual;
  step-1: run cmd=cp templates/wup.yaml.template ./wup.yaml;
  step-2: run cmd=if [ -n "${PROJECT:-}" ]; then
  sed -i "s/__PROJECT__/${PROJECT}/g" ./wup.yaml
  echo "✓ wup.yaml installed (project=${PROJECT})"
else
  echo "✓ wup.yaml installed (no PROJECT set; placeholder __PROJECT__ left in file)"
fi;
  step-3: run cmd=echo "  Next: 1) review wup.yaml services/paths";
  step-4: run cmd=echo "        2) wup map-deps         (build dependency map)";
  step-5: run cmd=echo "        3) wup testql-endpoints (verify scenarios reachable)";
  step-6: run cmd=echo "        4) wup watch            (start daemon, foreground)";
  step-7: run cmd=echo "  See: workflows/on-change-gates.md for the full triad cycle";
}

workflow[name="template:install:on-change-gates"] {
  trigger: manual;
  step-1: run cmd=test -f regix.yaml || cp templates/regix.yaml.template ./regix.yaml;
  step-2: run cmd=echo "✓ on-change gate triad installed (wup.yaml + regix.yaml)";
  step-3: run cmd=echo "  testql scenarios are project-specific — re-use existing testql-testing/scenarios/ or write new TOON YAML by hand";
  step-4: run cmd=echo "  Workflow guide: see koru workflows/on-change-gates.md";
  step-5: run cmd=echo "  Slash command:  /koru-gate (invokes all three on demand)";
}

workflow[name="scripts:list"] {
  trigger: manual;
  step-1: run cmd=ls scripts/;
}

workflow[name="scripts:redup:check"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redup-check.sh "{{.PATH | default \".\"}}";
}

workflow[name="scripts:redup:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redup-precommit.sh;
}

workflow[name="scripts:regix:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/regix-precommit.sh;
}

workflow[name="scripts:redsl:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redsl-gate-precommit.sh;
}

workflow[name="scripts:planfile:sync-todo"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/planfile-sync-todo.py;
}

workflow[name="deploy:plan"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --plan-only;
}

workflow[name="deploy:dry"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --dry-run;
}

workflow[name="deploy:local"] {
  trigger: manual;
  step-1: run cmd=redeploy run redeploy/local/deployment.md;
}

workflow[name="deploy:device"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE}}/migration.md";
}

workflow[name="deploy:diagnose"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/diagnose.md";
}

workflow[name="deploy:resume"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE}}/migration.md" --from-step {{.STEP}};
}

workflow[name="deploy:drift"] {
  trigger: manual;
  step-1: run cmd=doql adopt --from-device "{{.DEVICE_HOST}}" -o app.doql.less;
  step-2: run cmd=echo "✓ Intended state captured. Commit app.doql.less to lock baseline.";
}

workflow[name="monitor:net"] {
  trigger: manual;
  step-1: run cmd=NET="${MONITOR_NET:-koru-quality-net}"
docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"
echo "✓ network $NET ready";
}

workflow[name="monitor:up"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml up -d --build;
  step-2: run cmd=echo "";
  step-3: run cmd=echo "Grafana       → http://localhost:$${GRAFANA_PORT:-3000} (anonymous viewer)";
  step-4: run cmd=echo "Prometheus    → http://localhost:$${PROMETHEUS_PORT:-9090}";
  step-5: run cmd=echo "Alertmanager  → http://localhost:$${ALERTMANAGER_PORT:-9093}";
  step-6: run cmd=echo "Loki          → http://localhost:$${LOKI_PORT:-3100}";
  step-7: run cmd=echo "Uptime Kuma   → http://localhost:$${UPTIME_KUMA_PORT:-3001}";
  step-8: run cmd=echo "Healing hook  → http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health";
}

workflow[name="monitor:up:lite"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml up -d --build prometheus alertmanager grafana blackbox-exporter node-exporter cadvisor uptime-kuma healing-webhook;
}

workflow[name="monitor:down"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml down;
}

workflow[name="monitor:status"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml ps;
}

workflow[name="monitor:logs"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml logs -f --tail=50 {{.SVC | default "healing-webhook"}};
}

workflow[name="monitor:probe"] {
  trigger: manual;
  step-1: run cmd=for url in \
  "http://localhost:$${PROMETHEUS_PORT:-9090}/-/healthy" \
  "http://localhost:$${ALERTMANAGER_PORT:-9093}/-/healthy" \
  "http://localhost:$${GRAFANA_PORT:-3000}/api/health" \
  "http://localhost:$${LOKI_PORT:-3100}/ready" \
  "http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" || echo 000)
  printf '  %-3s  %s\n' "$CODE" "$url"
done;
}

workflow[name="monitor:reload-prometheus"] {
  trigger: manual;
  step-1: run cmd=curl -X POST http://localhost:$${PROMETHEUS_PORT:-9090}/-/reload && echo "✓ reloaded";
}

workflow[name="webhook:run"] {
  trigger: manual;
  step-1: run cmd=cd services/healing-webhook && python3 app.py;
}

workflow[name="webhook:docker:build"] {
  trigger: manual;
  step-1: run cmd=docker build -t koru-healing-webhook:latest services/healing-webhook/;
}

workflow[name="webhook:docker:run"] {
  trigger: manual;
  step-1: run cmd=docker run --rm -p 8810:8810 koru-healing-webhook:latest;
}

workflow[name="webhook:test"] {
  trigger: manual;
  step-1: run cmd=curl -X POST http://localhost:8810/alert -H "Content-Type: application/json" -d '{"alerts":[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Smoke test"}}]}';
}

workflow[name="docs"] {
  trigger: manual;
  step-1: run cmd=echo "Documentation: docs/README.md";
  step-2: run cmd=echo "Agent guide:   docs/agent-guide.md";
  step-3: run cmd=echo "Tool catalog:  docs/llm-tools/README.md";
  step-4: run cmd=echo "CLI examples:  docs/cli-examples.md";
}

workflow[name="docs:serve"] {
  trigger: manual;
  step-1: run cmd=cd docs && python3 -m http.server 8000;
}

workflow[name="workflow:list"] {
  trigger: manual;
  step-1: run cmd=ls workflows/;
}

workflow[name="workflow:show"] {
  trigger: manual;
  step-1: run cmd=cat workflows/{{.NAME}}.md;
}

deploy {
  target: docker;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  python_version: >=3.12;
}
```

## Interfaces

### CLI Entry Points

- `koru`

### testql Scenarios

#### `testql-scenarios/generated-cli-tests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-cli-tests.testql.toon.yaml
# SCENARIO: CLI Command Tests
# TYPE: cli
# GENERATED: true

CONFIG[2]{key, value}:
  cli_command, python -m koru
  timeout_ms, 10000

# Test 1: CLI help command
SHELL "python -m koru --help" 5000
ASSERT_EXIT_CODE 0
ASSERT_STDOUT_CONTAINS "usage"

# Test 2: CLI version command
SHELL "python -m koru --version" 5000
ASSERT_EXIT_CODE 0

# Test 3: CLI main workflow (dry-run)
SHELL "python -m koru --help" 10000
ASSERT_EXIT_CODE 0
```

#### `testql-scenarios/generated-from-pytests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-from-pytests.testql.toon.yaml
# SCENARIO: Auto-generated from Python Tests
# TYPE: integration
# GENERATED: true

CONFIG[2]{key, value}:
  base_url, ${api_url:-http://localhost:8101}
  timeout_ms, 10000

# NOTE: Python pytest files were detected but no convertible HTTP calls or assertions were found.
# To run pytest tests directly, use: pytest <test_file>
```

## Workflows

### Taskfile Tasks (`Taskfile.yml`)

```yaml markpact:taskfile path=Taskfile.yml
version: '3'

# Taskfile for koru — closed-loop refactor automation.
#
# Usage:
#   task                      # show all tasks
#   task install              # install koru in editable mode
#   task loop -- WORKSPACE=/repos COMMAND='pytest -q'
#   task tickets:next
#   task quality:regix
#   task template:install     # copy all template configs to current dir
#
# See docs/cli-examples.md for full examples.

vars:
  KORU_VERSION:
    sh: cat VERSION 2>/dev/null || echo "0.1.1"
  PYTHON: python3

tasks:
  default:
    desc: Show all available tasks
    cmds:
      - task --list-all
    silent: true

  version:
    desc: Show koru version
    cmds:
      - 'echo "koru v{{.KORU_VERSION}}"'
    silent: true

  # =====================================================================
  # Install / setup
  # =====================================================================

  install:
    desc: Install koru in editable mode
    cmds:
      - pip install -e .
    sources:
      - pyproject.toml
      - src/**/*.py

  install:dev:
    desc: Install koru with dev dependencies (pytest etc.)
    cmds:
      - pip install -e ".[dev]" || pip install -e .

  install:tools:
    desc: Install all underlying LLM tools (16 packages — planfile, regix, redup, vallm, sumd, redeploy, goal, costs, op3, toonic, protogate, rebuild, mdflow, metrun, ...)
    cmds:
      - pip install planfile regix redup vallm prefact pfix sumd code2llm doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun
      - 'echo "✓ Core tools installed (16). For LLM-backed tools (redsl, llx, aider) install separately."'

  # =====================================================================
  # Tests
  # =====================================================================

  test:
    desc: Run koru tests
    cmds:
      - python3 -m pytest tests/ -v {{.CLI_ARGS}}

  test:fast:
    desc: Run tests without verbose output
    cmds:
      - python3 -m pytest tests/ -q

  lint:
    desc: Run ruff on koru sources and tests
    cmds:
      - python3 -m ruff check src tests

  lint:fix:
    desc: Run ruff with autofix
    cmds:
      - python3 -m ruff check src tests --fix

  ci:
    desc: Local CI equivalent (lint + tests)
    cmds:
      - task: lint
      - task: test:fast

  # =====================================================================
  # Closed-loop automation (the core koru CLI)
  # =====================================================================

  loop:
    desc: 'Run closed-loop across workspace. Vars: WORKSPACE, INCLUDE, COMMAND'
    cmds:
      - koru --workspace "{{.WORKSPACE}}" --include "{{.INCLUDE}}" --command "{{.COMMAND}}"
    vars:
      WORKSPACE: '{{.WORKSPACE | default "."}}'
      INCLUDE: '{{.INCLUDE | default "**"}}'
      COMMAND: '{{.COMMAND | default "pytest -q"}}'
    interactive: true

  loop:test:
    desc: Run pytest in closed-loop mode
    cmds:
      - task: loop
        vars: {COMMAND: 'pytest -q'}

  loop:lint:
    desc: Run ruff in closed-loop mode
    cmds:
      - task: loop
        vars: {COMMAND: 'ruff check .'}

  queue:run:
    desc: 'Run one task from planfile queue. Vars: PROJECT, ACTOR, DRY_RUN'
    cmds:
      - koru --queue --project "{{.PROJECT}}" --actor "{{.ACTOR}}" {{if eq .DRY_RUN "true"}}--dry-run{{end}}
    vars:
      PROJECT: '{{.PROJECT | default "."}}'
      ACTOR: '{{.ACTOR | default "koru-shell"}}'
      DRY_RUN: '{{.DRY_RUN | default "false"}}'
    interactive: true

  queue:dry-run:
    desc: Preview one runnable planfile queue task without executing it
    cmds:
      - task: queue:run
        vars: {DRY_RUN: "true"}

  queue:watch:
    desc: 'Watch planfile WebSocket events. Vars: WS_URL, MAX_EVENTS'
    cmds:
      - koru --watch --ws-url "{{.WS_URL}}" {{if .MAX_EVENTS}}--max-events "{{.MAX_EVENTS}}"{{end}}
    vars:
      WS_URL: '{{.WS_URL | default "ws://localhost:8000/ws"}}'
      MAX_EVENTS: '{{.MAX_EVENTS | default ""}}'
    interactive: true

  queue:autoloop:
    desc: 'Continuous intake+execution loop (scan --apply + queue --loop + autopilot drive)'
    cmds:
      - |
        PROJECT="{{.PROJECT}}" \
        ACTOR="{{.ACTOR}}" \
        QUEUE_NAME="{{.QUEUE_NAME}}" \
        MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
        SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
        ENABLE_SCAN="{{.ENABLE_SCAN}}" \
        ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
        ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
        DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
        bash scripts/koru-autoloop.sh
    vars:
      PROJECT: '{{.PROJECT | default "."}}'
      ACTOR: '{{.ACTOR | default "koru-shell"}}'
      QUEUE_NAME: '{{.QUEUE_NAME | default ""}}'
      MAX_ITERATIONS: '{{.MAX_ITERATIONS | default "50"}}'
      SLEEP_SECONDS: '{{.SLEEP_SECONDS | default "120"}}'
      ENABLE_SCAN: '{{.ENABLE_SCAN | default "true"}}'
      ENABLE_AUTOPILOT_DRIVE: '{{.ENABLE_AUTOPILOT_DRIVE | default "true"}}'
      ENABLE_INTERACTIVE: '{{.ENABLE_INTERACTIVE | default "false"}}'
      DRIVE_PROMPT: '{{.DRIVE_PROMPT | default "continue with the next ticket"}}'
    interactive: true

  # =====================================================================
  # Quality gates (LLM-free, proxies to underlying tools)
  # =====================================================================

  quality:regix:
    desc: Run regix gate locally (LLM-free regression metrics)
    cmds:
      - regix gate
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:redup:
    desc: 'Run redup duplicate detection (default: current dir)'
    cmds:
      - redup scan . --min-lines 10
    preconditions:
      - sh: which redup
        msg: "redup not installed. Run: task install:tools"

  quality:redup:check:
    desc: Run redup with budget check (uses scripts/redup-check.sh)
    cmds:
      - bash scripts/redup-check.sh "{{.PATH | default \".\"}}"

  quality:vallm:
    desc: 'Validate file with vallm (FILE=path/to/file.py)'
    cmds:
      - vallm validate -f "{{.FILE}}"
    requires:
      vars: [FILE]

  quality:vallm:semantic:
    desc: 'Validate with LLM-as-judge (requires OPENROUTER_API_KEY, FILE=...)'
    cmds:
      - vallm validate -f "{{.FILE}}" --semantic -v
    requires:
      vars: [FILE]
    preconditions:
      - sh: '[ -n "$OPENROUTER_API_KEY" ]'
        msg: "OPENROUTER_API_KEY not set"

  # ── SUMR — debounced refactor snapshot (requires `task template:install:sumr`) ─

  quality:sumr:status:
    desc: Show SUMR.md staleness vs HEAD (LLM-free; exit 1 if stale)
    cmds:
      - scripts/sumr-refresh.sh --status
    preconditions:
      - sh: test -x scripts/sumr-refresh.sh
        msg: "scripts/sumr-refresh.sh missing. Run: task template:install:sumr"

  quality:sumr:auto:
    desc: Refresh SUMR.md only if stale (debounced; safe for hooks/cron)
    cmds:
      - scripts/sumr-refresh.sh

  quality:sumr:refresh:
    desc: Force-refresh SUMR.md (bumps sumd/code2llm/redup/doql + regenerates)
    cmds:
      - scripts/sumr-refresh.sh --force

  quality:sumr:install-hook:
    desc: 'Install git post-merge hook (HOOK=post-commit|both for alt)'
    cmds:
      - bash scripts/git-hooks/install.sh {{.HOOK | default "post-merge"}}

  quality:sumr:uninstall-hook:
    desc: Remove sumr-refresh git hooks (leaves foreign hooks intact)
    cmds:
      - bash scripts/git-hooks/install.sh --uninstall

  # =====================================================================
  # Tickets (planfile)
  # =====================================================================

  tickets:next:
    desc: Show highest-priority open ticket
    cmds:
      - planfile ticket next
    preconditions:
      - sh: which planfile
        msg: "planfile not installed. Run: pip install planfile"

  tickets:list:
    desc: List open tickets
    cmds:
      - planfile ticket list --status open --format yaml

  tickets:show:
    desc: 'Show ticket details (TID=PLF-XXX)'
    cmds:
      - planfile ticket show "{{.TID}}"
    requires:
      vars: [TID]

  tickets:done:
    desc: 'Mark ticket as done (TID=PLF-XXX)'
    cmds:
      - planfile ticket update "{{.TID}}" --status done
    requires:
      vars: [TID]

  tickets:export:
    desc: 'Export ticket as LLM-ready prompt (TID=PLF-XXX)'
    cmds:
      - bash scripts/planfile-export-prompt.sh "{{.TID}}"
    requires:
      vars: [TID]

  # =====================================================================
  # Templates (copy reference configs to current directory)
  # =====================================================================

  template:list:
    desc: List available templates
    cmds:
      - ls templates/

  template:install:
    desc: Copy all template configs to current directory
    cmds:
      - cp templates/pyqual.yaml.template ./pyqual.yaml
      - cp templates/redup.toml.template ./redup.toml
      - cp templates/redsl.yaml.template ./redsl.yaml
      - cp templates/regix.yaml.template ./regix.yaml
      - cp templates/llx.toml.template ./llx.toml
      - cp templates/llx.yaml.template ./llx.yaml
      - cp templates/prefact.yaml.template ./prefact.yaml
      - 'echo "✓ All templates copied. Review and edit before committing."'

  template:install:single:
    desc: 'Copy single template (TPL=pyqual.yaml|redup.toml|redsl.yaml|...)'
    cmds:
      - 'cp templates/{{.TPL}}.template ./{{.TPL}} && echo "✓ {{.TPL}} copied"'
    requires:
      vars: [TPL]

  template:install:compose:
    desc: Copy docker-compose.quality.yml template
    cmds:
      - cp templates/docker-compose.quality.yml.template ./docker-compose.quality.yml
      - 'echo "✓ docker-compose.quality.yml copied. Review service definitions."'

  template:install:sumr:
    desc: 'Copy SUMR-refresh stack (script + git hooks + weekly workflow)'
    cmds:
      - mkdir -p scripts scripts/git-hooks .github/workflows
      - cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh
      - cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge
      - cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit
      - cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh
      - cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml
      - chmod +x scripts/sumr-refresh.sh scripts/git-hooks/post-merge scripts/git-hooks/post-commit scripts/git-hooks/install.sh
      - |
        grep -q '^\.sumr/$' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore
      - 'echo "✓ SUMR stack installed. Next: task quality:sumr:install-hook (see workflows/sumr-refresh-loop.md)"'

  template:install:redeploy:
    desc: 'Copy redeploy templates (local + device baseline) to redeploy/'
    cmds:
      - mkdir -p redeploy/local redeploy/device
      - cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md
      - cp templates/redeploy/device/manifest.yaml.template    redeploy/device/manifest.yaml
      - cp templates/redeploy/device/migration.md.template     redeploy/device/migration.md
      - cp templates/redeploy/device/diagnose.md.template      redeploy/device/diagnose.md
      - 'echo "✓ redeploy templates installed at redeploy/"'
      - 'echo "  Next: substitute placeholders (see workflows/redeploy-multi-device.md Krok 3)"'
      - 'echo "        rename redeploy/device/ → redeploy/<your-device>/"'
      - 'echo "        sed -i ''s/<APP_NAME>/myapp/g'' redeploy/local/*.md redeploy/device/*"'

  template:install:observability:
    desc: 'Copy observability stack (Prometheus + Grafana + Loki + Alertmanager + healing-webhook)'
    cmds:
      - mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning
      - cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml
      - cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml
      - cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml
      - cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml
      - 'echo "✓ Observability stack installed."'
      - 'echo "  Next: substitute <APP_NAME>/<APP_PORT> placeholders, then task monitor:up"'
      - 'echo "  See: workflows/observability-bootstrap.md"'

  template:install:windsurf:
    desc: 'Copy .windsurf/ bootstrap (rules.md + mcp_config.example.json)'
    cmds:
      - mkdir -p .windsurf
      - cp templates/.windsurf/rules.md.template               .windsurf/rules.md
      - cp templates/.windsurf/mcp_config.example.json.template .windsurf/mcp_config.example.json
      - 'echo "✓ .windsurf/ installed."'
      - 'echo "  Next: substitute <APP_NAME>/<REPO_PATH>, then merge mcp_config into ~/.codeium/windsurf/mcp_config.json"'

  template:install:ci:
    desc: 'Copy GH Actions templates (version-drift + code-quality) to .github/workflows/'
    cmds:
      - mkdir -p .github/workflows
      - cp templates/github-workflows/version-drift.yml.template   .github/workflows/version-drift.yml
      - cp templates/github-workflows/code-quality.yml.template    .github/workflows/code-quality.yml
      - mkdir -p scripts
      - cp templates/scripts/check-version-drift.sh.template       scripts/check-version-drift.sh
      - chmod +x scripts/check-version-drift.sh
      - 'echo "✓ CI templates installed."'
      - 'echo "  Next: ensure VERSION file at repo root + commit + push"'

  template:install:precommit:
    desc: 'Copy .pre-commit-config.yaml template'
    cmds:
      - cp templates/.pre-commit-config.yaml.template .pre-commit-config.yaml
      - 'echo "✓ .pre-commit-config.yaml installed."'
      - 'echo "  Next: substitute <APP_NAME>, then: pip install pre-commit && pre-commit install"'

  template:install:wup:
    desc: 'Copy wup.yaml template (on-change file watcher feeding testql gates)'
    cmds:
      - cp templates/wup.yaml.template ./wup.yaml
      - |
        if [ -n "${PROJECT:-}" ]; then
          sed -i "s/__PROJECT__/${PROJECT}/g" ./wup.yaml
          echo "✓ wup.yaml installed (project=${PROJECT})"
        else
          echo "✓ wup.yaml installed (no PROJECT set; placeholder __PROJECT__ left in file)"
        fi
      - 'echo "  Next: 1) review wup.yaml services/paths"'
      - 'echo "        2) wup map-deps         (build dependency map)"'
      - 'echo "        3) wup testql-endpoints (verify scenarios reachable)"'
      - 'echo "        4) wup watch            (start daemon, foreground)"'
      - 'echo "  See: workflows/on-change-gates.md for the full triad cycle"'

  template:install:on-change-gates:
    desc: 'Bootstrap on-change gate triad configs (wup.yaml + regix.yaml)'
    cmds:
      - task: template:install:wup
        vars: {PROJECT: '{{.PROJECT}}'}
      - test -f regix.yaml || cp templates/regix.yaml.template ./regix.yaml
      - 'echo "✓ on-change gate triad installed (wup.yaml + regix.yaml)"'
      - 'echo "  testql scenarios are project-specific — re-use existing testql-testing/scenarios/ or write new TOON YAML by hand"'
      - 'echo "  Workflow guide: see koru workflows/on-change-gates.md"'
      - 'echo "  Slash command:  /koru-gate (invokes all three on demand)"'

  # =====================================================================
  # Scripts wrappers
  # =====================================================================

  scripts:list:
    desc: List available scripts
    cmds:
      - ls scripts/

  scripts:redup:check:
    desc: 'Run redup-check.sh (PATH=. by default)'
    cmds:
      - bash scripts/redup-check.sh "{{.PATH | default \".\"}}"

  scripts:redup:precommit:
    desc: Run redup precommit hook
    cmds:
      - bash scripts/redup-precommit.sh

  scripts:regix:precommit:
    desc: Run regix precommit hook
    cmds:
      - bash scripts/regix-precommit.sh

  scripts:redsl:precommit:
    desc: Run redsl gate precommit hook
    cmds:
      - bash scripts/redsl-gate-precommit.sh

  scripts:planfile:sync-todo:
    desc: Sync planfile tickets with TODO.md
    cmds:
      - python3 scripts/planfile-sync-todo.py

  # =====================================================================
  # Deploy (redeploy + markpact specs — local + multi-device)
  # =====================================================================
  # Templates: templates/redeploy/   |   Workflow: workflows/redeploy-multi-device.md
  # Bootstrap: task template:install:redeploy

  deploy:plan:
    desc: 'Plan deploy without changes — DEVICE=<name> SPEC=<file> (defaults: local + deployment.md)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --plan-only
    preconditions:
      - sh: which redeploy
        msg: "redeploy not installed. Run: task install:tools (or pip install --user redeploy)"

  deploy:dry:
    desc: 'Dry run deploy (preview commands) — DEVICE=<name>'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --dry-run

  deploy:local:
    desc: Deploy locally via Docker Compose
    cmds:
      - redeploy run redeploy/local/deployment.md
    preconditions:
      - sh: test -f redeploy/local/deployment.md
        msg: "redeploy/local/deployment.md missing. Run: task template:install:redeploy"

  deploy:device:
    desc: 'Deploy to remote device — DEVICE=<name> (e.g. pi109, edge01)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE}}/migration.md"
    requires:
      vars: [DEVICE]
    preconditions:
      - sh: test -f "redeploy/{{.DEVICE}}/migration.md"
        msg: "redeploy/{{.DEVICE}}/migration.md missing. Copy from templates/redeploy/device/ and customize."

  deploy:diagnose:
    desc: 'Read-only diagnose — DEVICE=<name> (default: local)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/diagnose.md"

  deploy:resume:
    desc: 'Resume failed deploy — DEVICE=<name> STEP=<step_id>'
    cmds:
      - redeploy run "redeploy/{{.DEVICE}}/migration.md" --from-step {{.STEP}}
    requires:
      vars: [DEVICE, STEP]

  deploy:drift:
    desc: 'Snapshot device state into app.doql.less (drift baseline) — DEVICE_HOST=<user@host>'
    cmds:
      - doql adopt --from-device "{{.DEVICE_HOST}}" -o app.doql.less
      - 'echo "✓ Intended state captured. Commit app.doql.less to lock baseline."'
    requires:
      vars: [DEVICE_HOST]
    preconditions:
      - sh: which doql
        msg: "doql not installed. Run: pip install --user doql"

  # =====================================================================
  # Observability stack (Prometheus + Grafana + Loki + Alertmanager + healing-webhook)
  # =====================================================================
  # Templates: templates/observability/  |  Workflow: workflows/observability-bootstrap.md
  # Bootstrap: task template:install:observability

  monitor:net:
    desc: Ensure the shared quality-net docker network exists
    cmds:
      - |
        NET="${MONITOR_NET:-koru-quality-net}"
        docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"
        echo "✓ network $NET ready"

  monitor:up:
    desc: Bring up the full observability + self-healing stack (10 services)
    deps: [monitor:net]
    cmds:
      - docker compose -f docker-compose.observability.yml up -d --build
      - echo ""
      - 'echo "Grafana       → http://localhost:$${GRAFANA_PORT:-3000} (anonymous viewer)"'
      - 'echo "Prometheus    → http://localhost:$${PROMETHEUS_PORT:-9090}"'
      - 'echo "Alertmanager  → http://localhost:$${ALERTMANAGER_PORT:-9093}"'
      - 'echo "Loki          → http://localhost:$${LOKI_PORT:-3100}"'
      - 'echo "Uptime Kuma   → http://localhost:$${UPTIME_KUMA_PORT:-3001}"'
      - 'echo "Healing hook  → http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"'
    preconditions:
      - sh: test -f docker-compose.observability.yml
        msg: "docker-compose.observability.yml missing. Run: task template:install:observability"

  monitor:up:lite:
    desc: Bring up observability without Loki/Promtail (skip if disk is tight)
    deps: [monitor:net]
    cmds:
      - docker compose -f docker-compose.observability.yml up -d --build
          prometheus alertmanager grafana blackbox-exporter
          node-exporter cadvisor uptime-kuma healing-webhook

  monitor:down:
    desc: Stop the observability stack
    cmds:
      - docker compose -f docker-compose.observability.yml down

  monitor:status:
    desc: Show status of observability containers
    cmds:
      - docker compose -f docker-compose.observability.yml ps

  monitor:logs:
    desc: 'Tail logs of one observability service — SVC=<name> (default: healing-webhook)'
    cmds:
      - docker compose -f docker-compose.observability.yml logs -f --tail=50 {{.SVC | default "healing-webhook"}}

  monitor:probe:
    desc: 'Sanity check — curl health endpoints of all observability services'
    cmds:
      - |
        for url in \
          "http://localhost:$${PROMETHEUS_PORT:-9090}/-/healthy" \
          "http://localhost:$${ALERTMANAGER_PORT:-9093}/-/healthy" \
          "http://localhost:$${GRAFANA_PORT:-3000}/api/health" \
          "http://localhost:$${LOKI_PORT:-3100}/ready" \
          "http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"; do
          CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" || echo 000)
          printf '  %-3s  %s\n' "$CODE" "$url"
        done

  monitor:reload-prometheus:
    desc: Hot-reload Prometheus rules (no restart)
    cmds:
      - 'curl -X POST http://localhost:$${PROMETHEUS_PORT:-9090}/-/reload && echo "✓ reloaded"'

  # =====================================================================
  # Healing-webhook (generic alert → ticket service)
  # =====================================================================

  webhook:run:
    desc: 'Run healing-webhook locally on port 8810'
    cmds:
      - cd services/healing-webhook && python3 app.py
    interactive: true

  webhook:docker:build:
    desc: Build healing-webhook Docker image
    cmds:
      - docker build -t koru-healing-webhook:latest services/healing-webhook/

  webhook:docker:run:
    desc: Run healing-webhook in Docker (port 8810)
    cmds:
      - docker run --rm -p 8810:8810 koru-healing-webhook:latest

  webhook:test:
    desc: Send test alertmanager payload to local webhook
    cmds:
      - 'curl -X POST http://localhost:8810/alert -H "Content-Type: application/json" -d ''{"alerts":[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Smoke test"}}]}'''

  # =====================================================================
  # Documentation
  # =====================================================================

  docs:
    desc: Open documentation index
    cmds:
      - 'echo "Documentation: docs/README.md"'
      - 'echo "Agent guide:   docs/agent-guide.md"'
      - 'echo "Tool catalog:  docs/llm-tools/README.md"'
      - 'echo "CLI examples:  docs/cli-examples.md"'
    silent: true

  docs:serve:
    desc: 'Serve docs over HTTP (port 8000)'
    cmds:
      - cd docs && python3 -m http.server 8000

  # =====================================================================
  # Workflows (slash-commands ported from .windsurf/workflows/)
  # =====================================================================

  workflow:list:
    desc: List available workflows (markdown instructions for agents)
    cmds:
      - ls workflows/

  workflow:show:
    desc: 'Show workflow content (NAME=testql-autoloop|aider-docker-autoloop|...)'
    cmds:
      - 'cat workflows/{{.NAME}}.md'
    requires:
      vars: [NAME]
```

## Configuration

```yaml
project:
  name: koru
  version: 0.1.24
  env: local
```

## Dependencies

### Runtime

```text markpact:deps python
pyyaml>=6.0
```

### Development

```text markpact:deps python scope=dev
pytest>=8.0
ruff>=0.11
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
```

## Deployment

```bash markpact:run
pip install koru

# development install
pip install -e .[dev]
```

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `*(not set)*` | Required: OpenRouter API key (https://openrouter.ai/keys) |
| `LLM_MODEL` | `openrouter/qwen/qwen3-coder-next` | Model (default: openrouter/qwen/qwen3-coder-next) |
| `PFIX_AUTO_APPLY` | `true` | true = apply fixes without asking |
| `PFIX_AUTO_INSTALL_DEPS` | `true` | true = auto pip/uv install |
| `PFIX_AUTO_RESTART` | `false` | true = os.execv restart after fix |
| `PFIX_MAX_RETRIES` | `3` |  |
| `PFIX_DRY_RUN` | `false` |  |
| `PFIX_ENABLED` | `true` |  |
| `PFIX_GIT_COMMIT` | `false` | true = auto-commit fixes |
| `PFIX_GIT_PREFIX` | `pfix:` | commit message prefix |
| `PFIX_CREATE_BACKUPS` | `false` | false = disable .pfix_backups/ directory |

## Release Management (`goal.yaml`)

- **versioning**: `semver`
- **commits**: `conventional` scope=`koru`
- **changelog**: `keep-a-changelog`
- **build strategies**: `python`, `nodejs`, `rust`
- **version files**: `VERSION`, `pyproject.toml:version`, `venv/lib/python3.13/site-packages/matplotlib/__init__.py:__version__`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# koru | 94f 20159L | python:62,shell:29,less:1,javascript:1,typescript:1 | 2026-05-11
# stats: 396 func | 113 cls | 94 mod | CC̄=4.8 | critical:41 | cycles:0
# alerts[5]: CC main=59; CC render_markdown_handoff=45; CC build_context=41; CC validate_flat_pipeline=28; CC run_gc=26
# hotspots[5]: main fan=33; build_context fan=25; create_planfile_ticket fan=23; run_next_planfile_task fan=16; do_from_todo fan=15
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[94]:
  app.doql.less,469
  docs/llm-tools/aider/install.sh,56
  docs/llm-tools/claude-code/install.sh,61
  docs/llm-tools/costs/install.sh,50
  docs/llm-tools/cursor/install.sh,89
  docs/llm-tools/doql/install.sh,53
  docs/llm-tools/goal/install.sh,54
  docs/llm-tools/llx/install.sh,54
  docs/llm-tools/mdflow/install.sh,39
  docs/llm-tools/metrun/install.sh,39
  docs/llm-tools/op3/install.sh,54
  docs/llm-tools/pfix/install.sh,53
  docs/llm-tools/planfile/install.sh,42
  docs/llm-tools/prefact/install.sh,50
  docs/llm-tools/protogate/install.sh,39
  docs/llm-tools/rebuild/install.sh,39
  docs/llm-tools/redeploy/install.sh,88
  docs/llm-tools/redsl/install.sh,54
  docs/llm-tools/redup/install.sh,42
  docs/llm-tools/regix/install.sh,53
  docs/llm-tools/sumd/install.sh,81
  docs/llm-tools/testql/install.sh,50
  docs/llm-tools/toonic/install.sh,50
  docs/llm-tools/vallm/install.sh,56
  plugins/koru-autopilot-vscode/out/extension.js,249
  plugins/koru-autopilot-vscode/src/extension.ts,214
  project.sh,48
  scripts/koru-autoloop.sh,112
  scripts/planfile-export-prompt.sh,82
  scripts/planfile-sync-todo.py,220
  services/healing-webhook/app.py,674
  services/healing-webhook/ticket_builder.py,224
  src/koru/__init__.py,68
  src/koru/agents.py,223
  src/koru/autopilot/__init__.py,39
  src/koru/autopilot/audit.py,156
  src/koru/autopilot/cli_command.py,538
  src/koru/autopilot/client.py,80
  src/koru/autopilot/config.py,124
  src/koru/autopilot/daemon.py,517
  src/koru/autopilot/ide.py,189
  src/koru/autopilot/injector.py,256
  src/koru/autopilot/protocol.py,201
  src/koru/bootstrap.py,397
  src/koru/cli.py,1304
  src/koru/context.py,870
  src/koru/doctor.py,426
  src/koru/dotenv_loader.py,105
  src/koru/events.py,91
  src/koru/gate.py,205
  src/koru/gc.py,327
  src/koru/init.py,318
  src/koru/loop.py,132
  src/koru/planfile_queue.py,706
  src/koru/policy.py,241
  src/koru/queue_clean.py,356
  src/koru/run_log.py,125
  src/koru/runtime.py,104
  src/koru/scan.py,516
  src/koru/semcod_tools.py,130
  src/koru/serve.py,530
  src/koru/tasks.py,140
  src/koru/watch.py,84
  tests/e2e/bootstrap.sh,94
  tests/e2e/init.sh,29
  tests/e2e/smoke.sh,112
  tests/test_agents.py,50
  tests/test_autopilot_audit.py,124
  tests/test_autopilot_cli.py,299
  tests/test_autopilot_config.py,156
  tests/test_autopilot_daemon.py,480
  tests/test_autopilot_ide.py,121
  tests/test_autopilot_injector.py,183
  tests/test_autopilot_protocol.py,154
  tests/test_bootstrap.py,296
  tests/test_cli.py,222
  tests/test_context.py,442
  tests/test_doctor.py,383
  tests/test_dotenv_loader.py,117
  tests/test_e2e.py,903
  tests/test_events.py,67
  tests/test_gate.py,167
  tests/test_gc.py,277
  tests/test_init.py,163
  tests/test_loop.py,95
  tests/test_planfile_queue.py,848
  tests/test_policy.py,183
  tests/test_queue_clean.py,309
  tests/test_run_log.py,139
  tests/test_runtime.py,131
  tests/test_scan.py,303
  tests/test_serve.py,123
  tests/test_tasks.py,51
  tests/test_watch.py,102
D:
  scripts/planfile-sync-todo.py:
    e: run_planfile,load_tickets,build_auto_section,replace_auto_section,do_from_planfile,do_from_todo,_llm_stub,main
    run_planfile()
    load_tickets()
    build_auto_section(tickets)
    replace_auto_section(current;new_section)
    do_from_planfile(check)
    do_from_todo(heading;check)
    _llm_stub(item;heading)
    main()
  services/healing-webhook/app.py:
    e: _rate_limit_ok,_record_action,create_planfile_ticket,_run_docker,heal_redsl_gate,heal_redsl_improve,heal_rebuild_restore,heal_annotate,_run_vallm_check,_run_vallm_validate,_resolve_affected_files,heal_vallm_validate,_run_redup_check,heal_redup_check,_resolve_strategy,healthz,metrics,get_history,alertmanager_webhook,probe_failure,get_tickets
    _rate_limit_ok()
    _record_action(action;outcome;component;detail)
    create_planfile_ticket(alert)
    _run_docker(image;cmd;timeout)
    heal_redsl_gate(component;detail)
    heal_redsl_improve(component;detail)
    heal_rebuild_restore(component;detail)
    heal_annotate(component;detail)
    _run_vallm_check(file_path;timeout)
    _run_vallm_validate(file_path;model;timeout)
    _resolve_affected_files(component;labels;max_files)
    heal_vallm_validate(component;detail)
    _run_redup_check(timeout)
    heal_redup_check(component;detail)
    _resolve_strategy(strategy_name)
    healthz()
    metrics()
    get_history()
    alertmanager_webhook(request)
    probe_failure(request)
    get_tickets()
  services/healing-webhook/ticket_builder.py:
    e: _git_commit,_infer_paths,_format_paths,_default_acceptance,_format_acceptance,_reproduction_for,build_ticket_payload
    _git_commit(repo)
    _infer_paths(component;labels)
    _format_paths(paths)
    _default_acceptance(instance)
    _format_acceptance(items)
    _reproduction_for(labels;failures)
    build_ticket_payload(alert)
  src/koru/__init__.py:
  src/koru/agents.py:
    e: _which,_marker,detect_agent_options,detect_project_environment,detect_agent_environment,select_agent,save_agent_prompt,launch_agent,AgentOption
    AgentOption: to_dict(0)
    _which(command)
    _marker(project)
    detect_agent_options(project)
    detect_project_environment(project)
    detect_agent_environment(project)
    select_agent(agents)
    save_agent_prompt(project;prompt)
    launch_agent(agent;project;prompt)
  src/koru/autopilot/__init__.py:
    e: default_socket_path
    default_socket_path()
  src/koru/autopilot/audit.py:
    e: default_log_path,_isoformat_utc,_JSONFormatter,AuditLog
    _JSONFormatter: format(1)  # Emit ``record.msg`` verbatim — we hand it in pre-serialised.
    AuditLog: __init__(0),record(1),close(0)  # Append-only audit log for autopilot events.
    default_log_path()
    _isoformat_utc(ts)
  src/koru/autopilot/cli_command.py:
    e: _build_parser,_client,_action_daemon,_action_drive,_action_status,_action_shutdown,_action_ide_list,_action_doctor,_build_brief,_action_handoff,_format_tail_entry,_action_tail,_systemd_user_dir,_resolve_koru_bin,_render_unit,_action_install_unit,autopilot_main
    _build_parser()
    _client(args)
    _action_daemon(args)
    _action_drive(args)
    _action_status(args)
    _action_shutdown(args)
    _action_ide_list(_args)
    _action_doctor(args)
    _build_brief(project)
    _action_handoff(args)
    _format_tail_entry(entry)
    _action_tail(args)
    _systemd_user_dir()
    _resolve_koru_bin()
    _render_unit(koru_bin)
    _action_install_unit(args)
    autopilot_main(argv)
  src/koru/autopilot/client.py:
    e: AutopilotClient
    AutopilotClient: __init__(0),_connect(0),request(1),is_running(0),drive(1),status(0),shutdown(0)  # Connect, send one message, read one reply, disconnect.
  src/koru/autopilot/config.py:
    e: default_config_path,_merge_submit_keys,load_config,cached_config,clear_config_cache,AutopilotConfig
    AutopilotConfig: submit_key_for(1)  # In-memory view of ``autopilot.toml`` (or defaults).
    default_config_path()
    _merge_submit_keys(raw)
    load_config(path)
    cached_config()
    clear_config_cache()
  src/koru/autopilot/daemon.py:
    e: _load_context_module,_default_handoff,_peer_uid,_Client,AutopilotDaemon
    _Client:  # In-memory state for one connected socket.
    AutopilotDaemon: __init__(0),start(0),serve_forever(0),stop(0),_shutdown(0),_accept(0),_on_readable(1),_dispatch(2),_send(2),_drop(1),_plugin_for(1),_handle_drive(2),_drive_via_plugin(5),_drive_via_keyboard(5),_handle_hello(2),_handle_status(2),_handle_ack(2),_handle_session_event(2),_handle_shutdown(2),_handle_ping(2),_build_handler_table(0)  # Selector-based unix-socket broker.
    _load_context_module()
    _default_handoff(project)
    _peer_uid(sock)
  src/koru/autopilot/ide.py:
    e: _iter_proc_pids,_read_comm,_read_cmdline,_matches,detect_running_ides,pick_target,is_linux,detect_running_ides_cached,clear_detect_cache,RunningIDE
    RunningIDE: to_dict(0)  # A single IDE process discovered on the system.
    _iter_proc_pids()
    _read_comm(pid)
    _read_cmdline(pid)
    _matches(comm;cmdline;patterns)
    detect_running_ides()
    pick_target(detected)
    is_linux()
    detect_running_ides_cached()
    clear_detect_cache()
  src/koru/autopilot/injector.py:
    e: _submit_key_for,_which,_session_type,_default_runner,BackendStatus,InjectionResult,InjectorError,Injector
    BackendStatus: to_dict(0)  # Result of probing a single backend.
    InjectionResult: to_dict(0)
    InjectorError:  # No usable backend, or the backend call failed.
    Injector: probe(0),select_backend(0),type_text(1),_probe_one(1),_call(1),_press_wtype(1)  # Pick the best available backend and type text through it.
    _submit_key_for(ide)
    _which(name)
    _session_type()
    _default_runner(cmd;stdin)
  src/koru/autopilot/protocol.py:
    e: _filter_extras,decode,hello,chat_send,drive,ack,error,session_started,session_ended,ProtocolError,Message
    ProtocolError:  # Raised when a line cannot be decoded into a valid message.
    Message: to_dict(0),encode(0)  # A single protocol envelope.
    _filter_extras(msg_type;obj)
    decode(line)
    hello()
    chat_send(text)
    drive(text)
    ack(reply_to)
    error(reply_to;message)
    session_started()
    session_ended()
  src/koru/bootstrap.py:
    e: load_flat_pipeline,validate_flat_pipeline,_detect_cycle,materialize_to_planfile,_normalise_task,_next_id_after,import_flat_pipeline,_infer_prefix,ValidationError,ImportReport
    ValidationError: __str__(0)
    ImportReport: summary(0)
    load_flat_pipeline(path)
    validate_flat_pipeline(tasks)
    _detect_cycle(tasks)
    materialize_to_planfile(flat_tasks;project_dir)
    _normalise_task(task)
    _next_id_after(tasks;prefix)
    import_flat_pipeline(flat_path;project_dir)
    _infer_prefix(tasks)
  src/koru/cli.py:
    e: _command_value,_build_parser,_build_task_parser,_build_serve_parser,_build_scan_parser,_render_scan_text,_render_scan_markdown,_scan_main,_build_gate_parser,_gate_main,_build_gc_parser,_gc_main,_build_queue_parser,_render_clean_report_text,_queue_main,_build_agent_parser,_task_main,_serve_main,_agent_main,_is_bare_invocation,main
    _command_value(value)
    _build_parser()
    _build_task_parser()
    _build_serve_parser()
    _build_scan_parser()
    _render_scan_text(result)
    _render_scan_markdown(result)
    _scan_main(argv)
    _build_gate_parser()
    _gate_main(argv)
    _build_gc_parser()
    _gc_main(argv)
    _build_queue_parser()
    _render_clean_report_text(report)
    _queue_main(argv)
    _build_agent_parser()
    _task_main(argv)
    _serve_main(argv)
    _agent_main(argv)
    _is_bare_invocation(args)
    main()
  src/koru/context.py:
    e: _is_fixture_ticket,_resolve_include_fixtures,_load_project_dotenv,_planfile_command_base,_planfile_env,_fetch_all_tickets,_run_planfile,_safe_json,_git_probe,build_context,_auto_promote_blocking_tickets,_build_instructions,_build_setup_instructions,_build_shared_rules,_build_self_service,render_markdown_handoff
    _is_fixture_ticket(ticket)
    _resolve_include_fixtures(explicit)
    _load_project_dotenv(project)
    _planfile_command_base()
    _planfile_env()
    _fetch_all_tickets(project)
    _run_planfile(project;args;runner)
    _safe_json(text)
    _git_probe(project)
    build_context()
    _auto_promote_blocking_tickets(project;runner)
    _build_instructions(policy;ticket)
    _build_setup_instructions()
    _build_shared_rules(policy;ticket)
    _build_self_service(policy;ticket)
    render_markdown_handoff(context)
  src/koru/doctor.py:
    e: run_diagnostics,_check_git_repo,_check_planfile_binary,_check_planfile_config,_check_planfile_sprints,_check_planfile_sprints_yaml,_check_runtime_dir,_check_policy_yaml,_check_gitignore,_resolve_pytest_collect_timeout,_check_pytest_collect,_check_ci_command,render_text,Check,DoctorReport
    Check: to_dict(0)  # A single diagnostic outcome.
    DoctorReport: has_failures(0),has_warnings(0),summary(0),to_dict(0)  # Aggregate result of ``run_diagnostics``.
    run_diagnostics(project)
    _check_git_repo(project)
    _check_planfile_binary(_project)
    _check_planfile_config(project)
    _check_planfile_sprints(project)
    _check_planfile_sprints_yaml(project)
    _check_runtime_dir(project)
    _check_policy_yaml(project)
    _check_gitignore(project)
    _resolve_pytest_collect_timeout()
    _check_pytest_collect(project)
    _check_ci_command(project)
    render_text(report)
  src/koru/dotenv_loader.py:
    e: _parse_value,parse_dotenv,load_dotenv
    _parse_value(raw)
    parse_dotenv(text)
    load_dotenv(project)
  src/koru/events.py:
    e: emit_management_event,main
    emit_management_event()
    main()
  src/koru/gate.py:
    e: parse_authorizations,_resolve_actor,_planfile_base,authorize_gate,GateAuthorization
    GateAuthorization: to_note(0)  # Parsed gate-authorization record extracted from a ticket not
    parse_authorizations(notes)
    _resolve_actor(explicit)
    _planfile_base()
    authorize_gate(ticket_id)
  src/koru/gc.py:
    e: _now_utc,_parse_ts,_planfile_env,_run_planfile,_load_tickets_from_sprint,_archive_tickets,collect_gc_candidates,run_gc,GcCandidate,GcResult
    GcCandidate:  # A ticket eligible for garbage collection.
    GcResult: summary(0)  # Outcome of a gc run.
    _now_utc()
    _parse_ts(raw)
    _planfile_env()
    _run_planfile(args;project;runner)
    _load_tickets_from_sprint(project;sprint)
    _archive_tickets(tickets;project)
    collect_gc_candidates(project)
    run_gc(project)
  src/koru/init.py:
    e: init_project,_write_policy_stub_if_absent,_ensure_gitignore_entry,InitReport
    InitReport: summary(0)  # Summary of what ``init_project`` actually changed on disk.
    init_project(project)
    _write_policy_stub_if_absent(project)
    _ensure_gitignore_entry(project)
  src/koru/loop.py:
    e: _search_root_for_include,discover_repositories,_default_runner,run_closed_loop,CommandResult,RunRecord,LoopReport
    CommandResult:  # Protocol for subprocess-like command results.
    RunRecord:  # Single command execution result for one repository in one at
    LoopReport:  # Aggregated execution report for a full closed-loop run.
    _search_root_for_include(workspace;include_pattern)
    discover_repositories(workspace;include_pattern)
    _default_runner(command;repository)
    run_closed_loop()
  src/koru/planfile_queue.py:
    e: _planfile_env,_run_process,_run_shell_command,_run_api_request,_run_llm_request,_planfile_command,_parse_next_ticket,_ticket_command,_ticket_llm_request,_ticket_api_request,_default_human_prompt,_result_json,run_next_planfile_task,run_planfile_queue_loop,CommandResult,QueueRunResult,QueueLoopResult,ApiRunResult,LlmRunResult
    CommandResult:  # Protocol for subprocess-like command results.
    QueueRunResult:  # Result of a single queue tick.
    QueueLoopResult: summary(0)  # Aggregate result of draining the planfile queue with run_pla
    ApiRunResult:  # Result of a direct HTTP API executor call.
    LlmRunResult:  # Result of an OpenRouter (or compatible) chat-completion call
    _planfile_env()
    _run_process(command;project)
    _run_shell_command(command;project)
    _run_api_request(request;_project)
    _run_llm_request(request;_project)
    _planfile_command(project;args;runner)
    _parse_next_ticket(stdout)
    _ticket_command(ticket)
    _ticket_llm_request(ticket)
    _ticket_api_request(ticket)
    _default_human_prompt(prompt;ticket_id)
    _result_json(result)
    run_next_planfile_task()
    run_planfile_queue_loop()
  src/koru/policy.py:
    e: policy_path,load_policy,policy_violations,Policy
    Policy: to_dict(0)  # Resolved policy for an LLM agent operating on a koru project
    policy_path(project)
    load_policy(project)
    policy_violations(policy;command)
  src/koru/queue_clean.py:
    e: _planfile_base,_parse_age_days,_matched_rules,find_candidates,_build_close_note,_list_tickets,_close_ticket,clean_queue,CleanupCandidate,CleanupReport
    CleanupCandidate: explanation(0)  # A planfile ticket selected for cleanup, with the reasons why
    CleanupReport: to_dict(0)  # Outcome of a (dry-run or applied) sweep.
    _planfile_base()
    _parse_age_days(ticket)
    _matched_rules(ticket)
    find_candidates(tickets)
    _build_close_note(candidate;reason)
    _list_tickets(project;runner)
    _close_ticket(project;candidate;reason;runner)
    clean_queue(project)
  src/koru/run_log.py:
    e: open_run_log,open_run_log_eagerly,_iso,RunLogWriter
    RunLogWriter: _emit(1),write_header(0),write_iteration(0),write_footer(0)  # Append-only JSONL writer with best-effort durability.
    open_run_log(project)
    open_run_log_eagerly(project)
    _iso(epoch)
  src/koru/runtime.py:
    e: planfile_dir,runtime_dir,runs_dir,new_run_id,ensure_runs_dir
    planfile_dir(project)
    runtime_dir(project)
    runs_dir(project)
    new_run_id(prefix)
    ensure_runs_dir(project)
  src/koru/scan.py:
    e: scan_pytest_collect,scan_todo_markers,scan_missing_gates,scan_missing_tools,scan_gitignore_drift,collect_suggestions,_existing_scan_titles,_create_ticket,run_scan,Suggestion,ScanResult
    Suggestion: to_dict(0)  # One proposed planfile ticket derived from a repo signal.
    ScanResult: to_dict(0)  # Aggregate output of ``run_scan``.
    scan_pytest_collect(project)
    scan_todo_markers(project)
    scan_missing_gates(project)
    scan_missing_tools(project)
    scan_gitignore_drift(project)
    collect_suggestions(project)
    _existing_scan_titles(project)
    _create_ticket(project;suggestion)
    run_scan(project)
  src/koru/semcod_tools.py:
    e: _read_pyproject,_config_present,detect_semcod_tools,SemcodTool
    SemcodTool: to_dict(0)  # One detected (or absent) semcod tool.
    _read_pyproject(project)
    _config_present(pyproject;tool_id)
    detect_semcod_tools(project)
  src/koru/serve.py:
    e: _build_handler,build_server,serve,ServeConfig
    ServeConfig:
    _build_handler(config)
    build_server(config)
    serve(config)
  src/koru/tasks.py:
    e: create_nl_task,_title_from_text,_read_config,_read_sprint,_write_yaml,CreatedTask
    CreatedTask:
    create_nl_task(project;text)
    _title_from_text(text)
    _read_config(path)
    _read_sprint(path)
    _write_yaml(path;data)
  src/koru/watch.py:
    e: format_queue_event,_default_connect,watch_planfile_events
    format_queue_event(event)
    _default_connect(ws_url)
    watch_planfile_events(ws_url)
  tests/test_agents.py:
    e: TestAgentDetection
    TestAgentDetection: test_detects_project_hints_without_cli(0),test_detects_openrouter_lane_from_env(0),test_select_agent_prefers_launchable_when_noninteractive(0)
  tests/test_autopilot_audit.py:
    e: _read_lines,test_disabled_audit_is_silent,test_record_writes_ndjson,test_record_drops_none_values,test_log_file_is_owner_only,test_directory_is_owner_only,test_default_log_path_uses_xdg_state,test_default_log_path_falls_back_to_home,test_multiple_records_appear_in_order,test_rotation_caps_file_size,test_unwritable_directory_disables_silently
    _read_lines(path)
    test_disabled_audit_is_silent(tmp_path)
    test_record_writes_ndjson(tmp_path)
    test_record_drops_none_values(tmp_path)
    test_log_file_is_owner_only(tmp_path)
    test_directory_is_owner_only(tmp_path)
    test_default_log_path_uses_xdg_state(tmp_path;monkeypatch)
    test_default_log_path_falls_back_to_home(monkeypatch)
    test_multiple_records_appear_in_order(tmp_path)
    test_rotation_caps_file_size(tmp_path)
    test_unwritable_directory_disables_silently(tmp_path;capsys;monkeypatch)
  tests/test_autopilot_cli.py:
    e: test_autopilot_parser_requires_action,test_drive_without_daemon_errors,test_drive_dry_run_direct,test_ide_list_empty,test_doctor_json_output,test_status_when_no_daemon,test_shutdown_when_no_daemon,test_handoff_dry_run_prints_brief_and_skips_daemon,test_handoff_requires_running_daemon,test_handoff_drives_brief_through_client,_write_audit_log,test_tail_text_format_renders_entries,test_tail_json_format_returns_array,test_tail_n_limits_output,test_tail_missing_log_errors_cleanly,test_tail_skips_malformed_lines,test_install_unit_print_renders_execstart,test_install_unit_writes_to_xdg_default_path,test_install_unit_refuses_overwrite_without_force,test_resolve_koru_bin_falls_back_to_sys_executable_sibling
    test_autopilot_parser_requires_action()
    test_drive_without_daemon_errors(capsys;tmp_path)
    test_drive_dry_run_direct(capsys;monkeypatch)
    test_ide_list_empty(capsys;monkeypatch)
    test_doctor_json_output(capsys;monkeypatch)
    test_status_when_no_daemon(capsys;tmp_path)
    test_shutdown_when_no_daemon(capsys;tmp_path)
    test_handoff_dry_run_prints_brief_and_skips_daemon(tmp_path;capsys;monkeypatch)
    test_handoff_requires_running_daemon(tmp_path;capsys;monkeypatch)
    test_handoff_drives_brief_through_client(tmp_path;capsys;monkeypatch)
    _write_audit_log(path;entries)
    test_tail_text_format_renders_entries(tmp_path;capsys)
    test_tail_json_format_returns_array(tmp_path;capsys)
    test_tail_n_limits_output(tmp_path;capsys)
    test_tail_missing_log_errors_cleanly(tmp_path;capsys)
    test_tail_skips_malformed_lines(tmp_path;capsys)
    test_install_unit_print_renders_execstart(capsys;monkeypatch)
    test_install_unit_writes_to_xdg_default_path(tmp_path;capsys;monkeypatch)
    test_install_unit_refuses_overwrite_without_force(tmp_path;capsys)
    test_resolve_koru_bin_falls_back_to_sys_executable_sibling(tmp_path;monkeypatch)
  tests/test_autopilot_config.py:
    e: test_load_config_returns_defaults_when_file_missing,test_load_config_user_keys_override_defaults,test_load_config_malformed_toml_falls_back_to_defaults,test_load_config_skips_non_string_entries,test_load_config_ignores_unrelated_sections,test_submit_key_for_falls_back_to_default,test_submit_key_for_uses_explicit_default_when_present,test_submit_key_for_falls_back_when_no_default_key,test_default_config_path_uses_xdg_when_set,test_default_config_path_falls_back_to_home,test_cached_config_is_memoised
    test_load_config_returns_defaults_when_file_missing(tmp_path)
    test_load_config_user_keys_override_defaults(tmp_path)
    test_load_config_malformed_toml_falls_back_to_defaults(tmp_path;capsys)
    test_load_config_skips_non_string_entries(tmp_path)
    test_load_config_ignores_unrelated_sections(tmp_path)
    test_submit_key_for_falls_back_to_default()
    test_submit_key_for_uses_explicit_default_when_present()
    test_submit_key_for_falls_back_when_no_default_key()
    test_default_config_path_uses_xdg_when_set(tmp_path;monkeypatch)
    test_default_config_path_falls_back_to_home(monkeypatch)
    test_cached_config_is_memoised(monkeypatch)
  tests/test_autopilot_daemon.py:
    e: _patch_no_running_ides,_daemon,_connect_plugin,_assert_no_more_data,running_daemon,test_ping_round_trip,test_is_running_true_when_daemon_alive,test_drive_falls_back_to_injector_when_no_plugin,test_drive_reports_injector_failure,test_drive_empty_text_returns_error,test_drive_unknown_type_returns_error,test_status_reports_socket_and_plugins,test_accept_rejects_foreign_peer_uid,test_plugin_hello_then_drive_forwards,test_default_handoff_builds_brief_for_uninitialised_project,test_session_ended_triggers_handoff_chat_send,test_session_ended_no_handoff_when_disabled,test_session_ended_skipped_during_cooldown,test_session_started_event_just_acks,test_shutdown_stops_daemon,_StubInjector,_LineReader,_DaemonHarness
    _StubInjector: __init__(0),type_text(1),probe(0),select_backend(0)  # Replaces :class:`koru.autopilot.injector.Injector` for tests
    _LineReader: __init__(1),read_line(0),read_message(0)  # Stateful NDJSON line reader over a blocking socket.
    _DaemonHarness: __init__(1),start(0),stop(0),client(1)  # Spin up :class:`AutopilotDaemon` on a thread and tear it dow
    _patch_no_running_ides(monkeypatch)
    _daemon(tmp_path;monkeypatch)
    _connect_plugin(sock_path)
    _assert_no_more_data(sock)
    running_daemon(tmp_path;monkeypatch)
    test_ping_round_trip(running_daemon)
    test_is_running_true_when_daemon_alive(running_daemon)
    test_drive_falls_back_to_injector_when_no_plugin(running_daemon)
    test_drive_reports_injector_failure(tmp_path;monkeypatch)
    test_drive_empty_text_returns_error(running_daemon)
    test_drive_unknown_type_returns_error(running_daemon)
    test_status_reports_socket_and_plugins(running_daemon)
    test_accept_rejects_foreign_peer_uid(tmp_path;monkeypatch)
    test_plugin_hello_then_drive_forwards(tmp_path;monkeypatch)
    test_default_handoff_builds_brief_for_uninitialised_project(tmp_path)
    test_session_ended_triggers_handoff_chat_send(tmp_path;monkeypatch)
    test_session_ended_no_handoff_when_disabled(tmp_path;monkeypatch)
    test_session_ended_skipped_during_cooldown(tmp_path;monkeypatch)
    test_session_started_event_just_acks(tmp_path;monkeypatch)
    test_shutdown_stops_daemon(tmp_path;monkeypatch)
  tests/test_autopilot_ide.py:
    e: fake_proc,test_detect_running_ides_finds_windsurf_and_jetbrains,test_detect_running_ides_deduplicates_same_ide,test_detect_running_ides_skips_unknown_processes,test_pick_target_prefers_user_choice,test_pick_target_returns_none_when_pref_not_running,test_pick_target_defaults_to_first,test_pick_target_empty_list_returns_none,test_detect_cached_uses_cache_within_ttl,test_detect_cached_ttl_zero_always_refreshes,test_clear_detect_cache_forces_refresh
    fake_proc(tmp_path;monkeypatch)
    test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc)
    test_detect_running_ides_deduplicates_same_ide(fake_proc)
    test_detect_running_ides_skips_unknown_processes(fake_proc)
    test_pick_target_prefers_user_choice(fake_proc)
    test_pick_target_returns_none_when_pref_not_running(fake_proc)
    test_pick_target_defaults_to_first(fake_proc)
    test_pick_target_empty_list_returns_none()
    test_detect_cached_uses_cache_within_ttl(monkeypatch)
    test_detect_cached_ttl_zero_always_refreshes(monkeypatch)
    test_clear_detect_cache_forces_refresh(monkeypatch)
  tests/test_autopilot_injector.py:
    e: _fake_runner,_which_factory,test_select_backend_x11_prefers_xdotool,test_select_backend_wayland_prefers_wtype_over_ydotool,test_select_backend_wayland_falls_back_to_ydotool,test_select_backend_no_tools_returns_none,test_type_text_dry_run_does_not_call_runner,test_type_text_xdotool_types_and_submits,test_type_text_wtype_uses_modifiers_for_jetbrains,test_type_text_no_submit_only_types,test_type_text_propagates_runner_error,test_type_text_empty_raises,test_type_text_no_backend_raises,test_probe_marks_unavailable_when_missing_tool,test_probe_marks_unavailable_on_wrong_session,test_wtype_rejects_multi_modifier_submit_key,test_wtype_single_modifier_still_works
    _fake_runner(commands)
    _which_factory(present)
    test_select_backend_x11_prefers_xdotool()
    test_select_backend_wayland_prefers_wtype_over_ydotool()
    test_select_backend_wayland_falls_back_to_ydotool()
    test_select_backend_no_tools_returns_none()
    test_type_text_dry_run_does_not_call_runner()
    test_type_text_xdotool_types_and_submits()
    test_type_text_wtype_uses_modifiers_for_jetbrains()
    test_type_text_no_submit_only_types()
    test_type_text_propagates_runner_error()
    test_type_text_empty_raises()
    test_type_text_no_backend_raises()
    test_probe_marks_unavailable_when_missing_tool()
    test_probe_marks_unavailable_on_wrong_session()
    test_wtype_rejects_multi_modifier_submit_key(monkeypatch)
    test_wtype_single_modifier_still_works()
  tests/test_autopilot_protocol.py:
    e: test_encode_round_trip_minimal,test_encode_strips_reserved_keys_from_data,test_decode_rejects_unknown_type,test_decode_rejects_malformed_json,test_decode_rejects_oversized_line,test_decode_rejects_non_object_top_level,test_decode_requires_type_field,test_decode_id_must_be_string_when_present,test_decode_extra_fields_land_in_data,test_builders_produce_valid_envelopes,test_ack_default_ok_true,test_error_carries_message,test_decode_drops_unknown_fields_for_strict_type,test_decode_drops_unknown_fields_on_chat_send,test_decode_drops_all_extras_on_zero_field_type,test_decode_keeps_arbitrary_extras_for_ack,test_decode_keeps_arbitrary_extras_for_error,test_drive_with_unknown_ide_field_value_passes_known_fields
    test_encode_round_trip_minimal()
    test_encode_strips_reserved_keys_from_data()
    test_decode_rejects_unknown_type()
    test_decode_rejects_malformed_json()
    test_decode_rejects_oversized_line()
    test_decode_rejects_non_object_top_level()
    test_decode_requires_type_field()
    test_decode_id_must_be_string_when_present()
    test_decode_extra_fields_land_in_data()
    test_builders_produce_valid_envelopes()
    test_ack_default_ok_true()
    test_error_carries_message()
    test_decode_drops_unknown_fields_for_strict_type()
    test_decode_drops_unknown_fields_on_chat_send()
    test_decode_drops_all_extras_on_zero_field_type()
    test_decode_keeps_arbitrary_extras_for_ack()
    test_decode_keeps_arbitrary_extras_for_error()
    test_drive_with_unknown_ide_field_value_passes_known_fields()
  tests/test_bootstrap.py:
    e: _write_yaml,TestLoadFlatPipeline,TestValidateFlatPipeline,TestMaterializeToPlanfile,TestImportFlatPipeline,TestImportReport,TestValidationError
    TestLoadFlatPipeline: test_loads_header_and_tasks(0),test_missing_file_raises(0),test_missing_tasks_raises(0)
    TestValidateFlatPipeline: test_valid_pipeline_has_no_errors(0),test_missing_id_reported(0),test_duplicate_id_reported(0),test_invalid_executor_kind(0),test_invalid_priority_reported(0),test_unknown_blocked_by_reference(0),test_cycle_detected(0),_load(1)
    TestMaterializeToPlanfile: test_creates_planfile_structure(0),test_default_execution_state_ready_for_unblocked(0),test_default_execution_state_pending_for_blocked(0),test_overwrite_protection(0)
    TestImportFlatPipeline: test_full_round_trip(0),test_invalid_pipeline_raises_value_error(0)
    TestImportReport: test_summary_includes_key_facts(0)
    TestValidationError: test_str_format(0)
    _write_yaml(path;content)
  tests/test_cli.py:
    e: _tmp_git_project,_run_main,TestBareInvocation,TestDoctorDispatch,TestInitDispatch,TestContextDispatch,TestBareEmitsMarkdown,TestSubcommandDispatch
    TestBareInvocation: _parse(0),test_no_args_is_bare(0),test_project_only_is_bare(0),test_init_is_not_bare(0),test_doctor_is_not_bare(0),test_context_is_not_bare(0),test_queue_is_not_bare(0),test_watch_is_not_bare(0),test_bootstrap_is_not_bare(0),test_command_is_not_bare(0)  # ``koru`` with no action flag should route to markdown brief.
    TestDoctorDispatch: setUp(0),tearDown(0),test_doctor_default_is_text(0),test_doctor_json(0),test_doctor_exit_0_on_no_failures(0)  # --doctor uses text by default, json when --format json.
    TestInitDispatch: setUp(0),tearDown(0),test_init_creates_planfile(0),test_init_duplicate_rejected(0)  # --init creates project scaffold.
    TestContextDispatch: setUp(0),tearDown(0),test_context_json_default(0),test_context_markdown(0)  # --context emits JSON or markdown.
    TestBareEmitsMarkdown: setUp(0),tearDown(0),test_bare_produces_markdown(0)  # Bare ``koru`` should produce a markdown brief.
    TestSubcommandDispatch: test_table_contains_all_documented_subcommands(0),test_table_values_are_callables(0),test_each_subcommand_routes_to_its_handler(0),test_unknown_first_arg_falls_through_to_argparse(0),test_empty_argv_does_not_call_any_handler(0)  # R6: routing through ``_SUBCOMMANDS`` dispatch table.
    _tmp_git_project(prefix)
    _run_main()
  tests/test_context.py:
    e: _ok,_fail,_no_git,_init_planfile,TestBuildContext,TestMarkdownHandoff,TestSetupRequired
    TestBuildContext: test_brief_with_runnable_ticket(0),test_brief_when_queue_idle(0),test_brief_when_planfile_errors(0),test_specific_ticket_uses_show(0),test_instructions_include_no_commit_rule(0),test_instructions_include_ci_command_when_set(0),test_self_service_includes_concrete_ticket_commands(0),test_brief_is_json_serialisable(0),test_files_in_scope_appear_in_instructions(0),test_fixture_tickets_are_skipped_by_default(0),test_real_ticket_picked_over_fixture_in_mixed_queue(0),test_include_fixtures_flag_brings_them_back(0),test_single_object_fixture_is_filtered(0),test_explicit_ticket_id_bypasses_fixture_filter(0),test_all_tickets_are_populated_from_list(0)
    TestMarkdownHandoff: test_renders_ticket_section(0),test_renders_policy_table(0),test_renders_idle_brief_without_crash(0)
    TestSetupRequired: test_instructions_swap_to_setup_guide(0),test_self_service_exposes_init_only(0),test_environment_planfile_initialised_false(0),test_markdown_renders_setup_required_block(0)  # When planfile is not initialised, the brief must steer to ko
    _ok(stdout)
    _fail(stderr)
    _no_git(_project)
    _init_planfile(project)
  tests/test_doctor.py:
    e: _scaffold,_run,_named,TestHappyPath,TestGitRepoCheck,TestPlanfileBinary,TestPlanfileConfigCheck,TestSprintsCheck,TestPolicyYamlCheck,TestGitignoreCheck,TestCiCommandCheck,TestPytestCollectProbe,TestReportShape
    TestHappyPath: test_full_scaffold_passes_all_required_checks(0)
    TestGitRepoCheck: test_warns_when_no_git(0)
    TestPlanfileBinary: test_explicit_env_var_resolves(0),test_missing_binary_fails(0)
    TestPlanfileConfigCheck: test_missing_config_fails(0),test_malformed_config_fails(0)
    TestSprintsCheck: test_empty_sprint_warns(0),test_no_sprints_dir_fails(0)
    TestPolicyYamlCheck: test_absent_policy_passes(0),test_malformed_policy_fails(0),test_string_truthy_value_warns(0)
    TestGitignoreCheck: test_warns_when_runtime_not_ignored(0)
    TestCiCommandCheck: test_empty_warns(0),test_resolved_passes(0)
    TestPytestCollectProbe: _scaffold_with_pyproject(1),test_pass_when_collection_succeeds_with_count(0),test_pass_when_count_not_parseable(0),test_warn_when_zero_tests_collected(0),test_warn_when_collection_errors(0),test_fail_when_collection_times_out(0),test_skip_when_pytest_not_installed(0),test_probe_skipped_entirely_when_no_pyproject_and_no_tests(0),test_env_var_overrides_timeout(0)  # Behaviour of the ``pytest_collect`` doctor probe.
    TestReportShape: test_to_dict_keys_stable(0),test_render_text_groups_status(0),test_summary_counts_match_checks(0)
    _scaffold(project)
    _run(project)
    _named(report;name)
  tests/test_dotenv_loader.py:
    e: TestParseDotenv,TestLoadDotenv
    TestParseDotenv: test_simple_pairs(0),test_export_prefix_supported(0),test_double_quoted_with_escapes(0),test_single_quoted_literal(0),test_inline_comments_stripped(0),test_skips_blank_and_comment_lines(0),test_invalid_lines_silently_skipped(0),test_openrouter_realworld_line(0)
    TestLoadDotenv: setUp(0),tearDown(0),test_no_dotenv_returns_empty(0),test_loads_keys_into_environ(0),test_does_not_override_existing_env(0),test_override_flag_replaces_existing(0),test_env_local_overrides_env(0),test_openrouter_key_propagated(0)
  tests/test_e2e.py:
    e: _tmp_git_project,_run_main,_write_sprint,_write_config,_ts,_done_ticket,_init_project,_extract_json,TestE2EInitDoctorContext,TestE2ETask,TestE2EGc,TestE2EScan,TestE2EQueueLoop,TestE2EQueueLoopMode,TestE2EBootstrap,TestE2EGate,TestE2EFullLifecycle,TestE2EInitFromPipeline,TestE2EHumanTicket,TestE2EContextFixtureFiltering
    TestE2EInitDoctorContext: setUp(0),tearDown(0),test_init_then_doctor_passes(0),test_init_then_bare_koru_emits_markdown(0),test_init_then_context_json_has_policy(0),test_init_then_context_markdown_has_ticket(0),test_doctor_json_format(0),test_doctor_fails_on_empty_project(0),test_double_init_rejected(0)  # Full lifecycle: init → doctor → bare koru → context JSON.
    TestE2ETask: setUp(0),tearDown(0),test_task_creates_ticket(0),test_task_increments_id(0),test_task_empty_text_fails(0),test_task_with_priority(0)  # koru task "..." creates a ticket in the sprint YAML.
    TestE2EGc: setUp(0),tearDown(0),test_gc_dry_run_text(0),test_gc_dry_run_json(0),test_gc_keep_last_protects_newest(0),test_gc_custom_statuses(0),test_gc_no_stale_tickets_message(0),test_gc_apply_with_fake_runner(0)  # koru gc: dry-run, apply, archive, keep-last.
    TestE2EScan: setUp(0),tearDown(0),test_scan_detects_todo_markers(0),test_scan_json_format(0),test_scan_with_limit(0),test_scan_clean_project_no_suggestions(0)  # koru scan detects project issues and suggests tickets.
    TestE2EQueueLoop: setUp(0),tearDown(0),test_queue_dry_run(0),test_queue_processes_next_ticket(0),test_queue_idle_when_no_runnable_tickets(0)  # koru --queue processes shell tickets end-to-end.
    TestE2EQueueLoopMode: setUp(0),tearDown(0),test_loop_finds_and_processes_tickets(0),test_loop_reports_completed_count(0)  # koru --queue --loop drains multiple tickets.
    TestE2EBootstrap: setUp(0),tearDown(0),test_bootstrap_creates_planfile_structure(0),test_bootstrap_ticket_count(0),test_bootstrap_rejects_without_force(0),test_bootstrap_force_overwrites(0)  # koru --bootstrap imports a flat pipeline YAML.
    TestE2EGate: setUp(0),tearDown(0),test_gate_authorize_dry_run(0),test_gate_authorize_json_format(0)  # koru gate authorize writes a structured note.
    TestE2EFullLifecycle: setUp(0),tearDown(0),test_full_lifecycle(0)  # Simulate a complete project lifecycle through the CLI.
    TestE2EInitFromPipeline: setUp(0),tearDown(0),test_init_from_custom_pipeline(0)  # koru --init --from <yaml> imports a custom pipeline.
    TestE2EHumanTicket: setUp(0),tearDown(0),test_human_ticket_returns_waiting_input(0)  # koru --queue on a human ticket returns waiting_input.
    TestE2EContextFixtureFiltering: setUp(0),tearDown(0),test_context_without_fixtures_skips_synthetic(0),test_context_with_fixtures_includes_all(0)  # --include-fixtures / --no-include-fixtures controls ticket f
    _tmp_git_project(prefix)
    _run_main()
    _write_sprint(project;tickets;sprint)
    _write_config(project;prefix;next_id)
    _ts(days_ago)
    _done_ticket(name;days_ago)
    _init_project(project)
    _extract_json(text)
  tests/test_events.py:
    e: FakeResponse,TestManagementEvents
    FakeResponse: __enter__(0),__exit__(0)
    TestManagementEvents: test_emit_management_event_posts_expected_payload(0),test_emit_management_event_is_disabled_without_url(0)
  tests/test_gate.py:
    e: _ok,_fail,test_authorize_gate_records_structured_note,test_authorize_gate_rejects_unknown_mode,test_authorize_gate_requires_reason,test_authorize_gate_propagates_planfile_failure,test_parse_authorizations_round_trip,test_parse_authorizations_ignores_malformed_or_unrelated_notes,test_parse_authorizations_returns_records_in_insertion_order,test_valid_modes_constant_matches_documented_set
    _ok(stdout)
    _fail(stderr)
    test_authorize_gate_records_structured_note(tmp_path)
    test_authorize_gate_rejects_unknown_mode(tmp_path)
    test_authorize_gate_requires_reason(tmp_path)
    test_authorize_gate_propagates_planfile_failure(tmp_path)
    test_parse_authorizations_round_trip()
    test_parse_authorizations_ignores_malformed_or_unrelated_notes()
    test_parse_authorizations_returns_records_in_insertion_order()
    test_valid_modes_constant_matches_documented_set()
  tests/test_gc.py:
    e: _write_sprint,_ts,_ticket,TestCollectGcCandidates,TestRunGc
    TestCollectGcCandidates: test_finds_old_done_tickets(0),test_includes_failed_and_blocked(0),test_no_candidates_when_all_recent(0),test_missing_timestamp_treated_as_old(0),test_empty_sprint(0),test_custom_statuses(0)
    TestRunGc: test_dry_run_does_not_delete(0),test_keep_last_protects_recent(0),test_keep_last_larger_than_candidates_keeps_all(0),test_apply_calls_planfile_delete(0),test_apply_creates_archive(0),test_no_archive_flag(0),test_no_candidates_returns_empty_result(0),test_delete_failure_records_error(0),test_summary_string(0)
    _write_sprint(project;tickets;sprint)
    _ts(days_ago)
    _ticket(name;status;exec_state;days_ago)
  tests/test_init.py:
    e: TestStarterInit,TestForceAndConflicts,TestFromExternalPipeline,TestRuntimeContract
    TestStarterInit: test_creates_planfile_layout(0),test_writes_policy_stub_and_loads_safe_defaults(0),test_policy_stub_constant_is_valid_yaml(0),test_appends_gitignore_entry(0),test_gitignore_idempotent(0),test_preserves_existing_gitignore_content(0),test_policy_stub_not_overwritten_on_force(0),test_no_starter_yaml_left_behind(0)
    TestForceAndConflicts: test_re_init_without_force_raises(0),test_re_init_with_force_succeeds(0)
    TestFromExternalPipeline: test_imports_user_supplied_pipeline(0)
    TestRuntimeContract: test_init_does_not_leave_files_outside_planfile(0)
  tests/test_loop.py:
    e: TestKoruLoop
    TestKoruLoop: test_search_root_for_include_uses_literal_prefix(0),test_discover_repositories_with_pattern(0),test_run_closed_loop_retries_failed_repositories(0),test_run_closed_loop_single_round_when_all_succeed(0),test_command_value_rejects_blank_value(0)
  tests/test_planfile_queue.py:
    e: _ok,_ticket_args,TestPlanfileQueue,TestPlanfileQueueLlm,TestPlanfileQueueLoop
    TestPlanfileQueue: test_shell_ticket_runs_lifecycle_commands(0),test_human_ticket_returns_waiting_input(0),test_shell_failure_marks_ticket_failed(0),test_api_ticket_runs_lifecycle_commands(0),test_api_failure_marks_ticket_failed(0),test_idle_when_planfile_returns_no_ticket(0),test_planfile_error_propagates(0),test_dry_run_returns_command_without_executing(0),test_unsupported_executor_kind(0),test_shell_ticket_without_command_requests_input(0),test_api_ticket_without_endpoint_requests_input(0),test_interactive_human_ticket_completes_with_answer(0),test_interactive_human_ticket_cancellation_leaves_ticket(0),test_interactive_with_dry_run_does_not_prompt(0)
    TestPlanfileQueueLlm: _llm_ticket(0),test_llm_ticket_runs_lifecycle_commands(0),test_llm_ticket_failure_marks_failed(0),test_llm_ticket_without_prompt_requests_input(0),test_llm_dry_run_returns_request_without_calling(0),test_llm_default_runner_without_api_key_returns_clear_error(0)  # Tests for the executor.kind=llm path.
    TestPlanfileQueueLoop: _make_runner(1),test_loop_drains_three_shell_tickets_to_idle(0),test_loop_breaks_on_waiting_input_without_interactive(0),test_loop_continues_past_failed_ticket(0),test_loop_respects_max_iterations_cap(0),test_loop_with_interactive_drains_human_tickets(0),test_loop_validates_max_iterations(0)  # Tests for run_planfile_queue_loop — the queue-draining drive
    _ok(stdout)
    _ticket_args(command)
  tests/test_policy.py:
    e: _write_policy,TestDefaults,TestLoad,TestViolations
    TestDefaults: test_defaults_are_strict(0),test_default_forbidden_paths_include_critical(0),test_default_shell_patterns_include_critical(0),test_to_dict_keys_are_sorted(0)
    TestLoad: test_missing_file_returns_defaults(0),test_malformed_yaml_falls_back_to_defaults(0),test_top_level_non_mapping_falls_back_to_defaults(0),test_string_truthy_value_is_rejected(0),test_explicit_loosening_is_honoured(0),test_zero_or_negative_timeout_falls_back_to_default(0),test_unknown_keys_are_ignored(0)
    TestViolations: test_git_commit_blocked_by_default(0),test_git_push_blocked_by_default(0),test_force_push_double_flag(0),test_branch_create_blocked(0),test_rm_rf_root_blocked(0),test_safe_command_passes(0),test_empty_command_passes(0),test_loosened_policy_allows_commit(0),test_path_helper_resolves(0)
    _write_policy(project;content)
  tests/test_queue_clean.py:
    e: _ok,_fail,test_label_match_picks_only_fixture_labelled_tickets,test_name_heuristic_only_runs_when_explicit,test_name_heuristic_does_not_match_real_tickets_with_test_word,test_active_tickets_skipped_by_default_but_surfaced,test_include_active_promotes_skipped_back_to_candidates,test_max_age_modifies_but_never_alone,test_age_calculation_handles_z_suffix_and_naive_dates,_list_response,test_clean_queue_dry_run_lists_but_does_not_close,test_clean_queue_apply_closes_each_candidate_with_audit_note,test_clean_queue_records_failures_per_ticket,test_clean_queue_propagates_list_failure_as_runtime_error,test_clean_queue_handles_empty_list_gracefully,test_cleanup_candidate_explanation_is_human_readable,test_report_to_dict_is_json_serialisable
    _ok(stdout)
    _fail(stderr;code)
    test_label_match_picks_only_fixture_labelled_tickets()
    test_name_heuristic_only_runs_when_explicit()
    test_name_heuristic_does_not_match_real_tickets_with_test_word()
    test_active_tickets_skipped_by_default_but_surfaced()
    test_include_active_promotes_skipped_back_to_candidates()
    test_max_age_modifies_but_never_alone()
    test_age_calculation_handles_z_suffix_and_naive_dates()
    _list_response(tickets)
    test_clean_queue_dry_run_lists_but_does_not_close(tmp_path)
    test_clean_queue_apply_closes_each_candidate_with_audit_note(tmp_path)
    test_clean_queue_records_failures_per_ticket(tmp_path)
    test_clean_queue_propagates_list_failure_as_runtime_error(tmp_path)
    test_clean_queue_handles_empty_list_gracefully(tmp_path)
    test_cleanup_candidate_explanation_is_human_readable()
    test_report_to_dict_is_json_serialisable()
  tests/test_run_log.py:
    e: _result,TestOpenRunLog,TestWriteEvents,TestErrorTolerance
    TestOpenRunLog: test_constructor_does_not_create_file(0),test_eager_creates_runs_dir_only(0),test_path_is_under_planfile_dot_koru_runs(0)
    TestWriteEvents: test_header_iteration_footer_round_trip(0),test_each_line_is_json(0),test_keys_are_sorted_in_output(0),test_message_truncation_500_chars(0)
    TestErrorTolerance: test_io_error_does_not_propagate(0)
    _result()
  tests/test_runtime.py:
    e: TestPathHelpers,TestRunIdGenerator,TestEnsureRunsDir
    TestPathHelpers: test_planfile_dir_is_under_project(0),test_runtime_dir_is_under_planfile(0),test_runs_dir_is_under_runtime_dir(0),test_path_helpers_do_not_create_directories(0),test_path_helpers_resolve_relative_input(0)  # Path resolvers must be pure: no filesystem mutation.
    TestRunIdGenerator: test_run_id_format(0),test_run_id_custom_prefix(0),test_run_ids_sort_chronologically(0),test_run_id_does_not_contain_path_separators(0)
    TestEnsureRunsDir: test_creates_full_subtree(0),test_writes_readme_stub_on_first_call(0),test_idempotent_does_not_overwrite_readme(0),test_does_not_write_outside_planfile(0)
  tests/test_scan.py:
    e: _ok,TestScanPytestCollect,TestScanTodoMarkers,TestScanMissingGates,TestScanMissingTools,TestScanGitignoreDrift,TestRunScan
    TestScanPytestCollect: test_returns_empty_when_no_tests_and_no_pyproject(0),test_empty_on_clean_collect(0),test_parses_per_file_collection_errors(0),test_falls_back_to_umbrella_import_ticket(0),test_collection_timeout_emits_diagnostic_ticket(0),test_timeout_value_is_reflected_in_ticket(0),test_pytest_not_installed_stays_silent(0)
    TestScanTodoMarkers: test_filters_files_below_threshold(0),test_groups_markers_per_file(0)
    TestScanMissingGates: test_no_suggestions_when_tool_missing(0),test_skips_when_config_already_present(0)
    TestScanMissingTools: test_no_pyproject_returns_empty(0),test_skips_tools_not_in_registry(0)
    TestScanGitignoreDrift: test_no_gitignore_returns_empty(0),test_present_entry_skips_suggestion(0),test_missing_entry_suggests(0)
    TestRunScan: test_dry_run_returns_suggestions_no_apply(0),test_apply_creates_tickets_and_skips_duplicates(0),test_apply_create_failure_is_skipped(0),test_limit_caps_suggestions(0),test_priority_ordering_critical_first(0)
    _ok(stdout;returncode;stderr)
  tests/test_serve.py:
    e: _free_port,_start,_get,TestServe
    TestServe: setUp(0),tearDown(0),test_health_endpoint(0),test_dashboard_html_served_on_root(0),test_api_context_returns_brief(0),test_api_handoff_returns_markdown(0),test_unknown_path_returns_404(0)
    _free_port()
    _start(project;port)
    _get(port;path)
  tests/test_tasks.py:
    e: TestNaturalLanguageTask
    TestNaturalLanguageTask: test_creates_planfile_ticket_from_sentence(0),test_increments_next_id(0),test_rejects_empty_text(0)
  tests/test_watch.py:
    e: FakeWebSocket,TestWatch
    FakeWebSocket: __init__(1),__aenter__(0),__aexit__(0),recv(0)
    TestWatch: test_format_queue_event_for_execution_change(0),test_format_management_event(0),test_watch_planfile_events_prints_compact_lines(0)
```

## Call Graph

*228 nodes · 247 edges · 35 modules · CC̄=5.1*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `render_markdown_handoff` *(in src.koru.context)* | 45 ⚠ | 5 | 163 | **168** |
| `print` *(in scripts.planfile-export-prompt)* | 0 | 144 | 0 | **144** |
| `main` *(in src.koru.cli)* | 59 ⚠ | 0 | 105 | **105** |
| `validate_flat_pipeline` *(in src.koru.bootstrap)* | 28 ⚠ | 1 | 58 | **59** |
| `load_policy` *(in src.koru.policy)* | 9 | 2 | 43 | **45** |
| `run_next_planfile_task` *(in src.koru.planfile_queue)* | 24 ⚠ | 2 | 40 | **42** |
| `build_context` *(in src.koru.context)* | 41 ⚠ | 6 | 36 | **42** |
| `create_planfile_ticket` *(in services.healing-webhook.app)* | 24 ⚠ | 2 | 39 | **41** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.10s
# nodes: 228 | edges: 247 | modules: 35
# CC̄=5.1

HUBS[20]:
  src.koru.context.render_markdown_handoff
    CC=45  in:5  out:163  total:168
  scripts.planfile-export-prompt.print
    CC=0  in:144  out:0  total:144
  src.koru.cli.main
    CC=59  in:0  out:105  total:105
  src.koru.bootstrap.validate_flat_pipeline
    CC=28  in:1  out:58  total:59
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.planfile_queue.run_next_planfile_task
    CC=24  in:2  out:40  total:42
  src.koru.context.build_context
    CC=41  in:6  out:36  total:42
  services.healing-webhook.app.create_planfile_ticket
    CC=24  in:2  out:39  total:41
  src.koru.autopilot.cli_command._build_parser
    CC=1  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koru.serve._build_handler
    CC=1  in:1  out:30  total:31
  src.koru.events.emit_management_event
    CC=8  in:23  out:7  total:30
  src.koru.agents.detect_agent_options
    CC=9  in:2  out:28  total:30
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.cli._gc_main
    CC=18  in:0  out:28  total:28
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  services.healing-webhook.app._run_redup_check
    CC=15  in:1  out:24  total:25
  src.koru.context._auto_promote_blocking_tickets
    CC=25  in:1  out:24  total:25
  src.koru.agents.detect_project_environment
    CC=4  in:1  out:22  total:23

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [24 funcs]
    activate  CC=3  out:7
    app  CC=1  out:1
    bridge  CC=2  out:3
    clearTimeout  CC=2  out:0
    connect  CC=1  out:9
    delay  CC=2  out:3
    detectIde  CC=4  out:2
    disconnect  CC=4  out:2
    dispatch  CC=6  out:2
    idx  CC=2  out:3
  scripts.planfile-export-prompt  [1 funcs]
    print  CC=0  out:0
  scripts.planfile-sync-todo  [7 funcs]
    build_auto_section  CC=9  out:17
    do_from_planfile  CC=10  out:14
    do_from_todo  CC=12  out:20
    load_tickets  CC=6  out:5
    main  CC=2  out:9
    replace_auto_section  CC=4  out:6
    run_planfile  CC=2  out:4
  services.healing-webhook.app  [16 funcs]
    _rate_limit_ok  CC=3  out:3
    _record_action  CC=1  out:7
    _resolve_affected_files  CC=11  out:24
    _resolve_strategy  CC=3  out:1
    _run_docker  CC=1  out:3
    _run_redup_check  CC=15  out:24
    _run_vallm_check  CC=10  out:15
    alertmanager_webhook  CC=5  out:19
    create_planfile_ticket  CC=24  out:39
    heal_annotate  CC=1  out:1
  services.healing-webhook.ticket_builder  [5 funcs]
    _default_acceptance  CC=2  out:1
    _format_paths  CC=2  out:1
    _infer_paths  CC=7  out:1
    _reproduction_for  CC=5  out:5
    build_ticket_payload  CC=11  out:25
  src.koru.agents  [8 funcs]
    _marker  CC=1  out:2
    _which  CC=1  out:1
    detect_agent_environment  CC=6  out:7
    detect_agent_options  CC=9  out:28
    detect_project_environment  CC=4  out:22
    launch_agent  CC=4  out:8
    save_agent_prompt  CC=1  out:3
    select_agent  CC=14  out:8
  src.koru.autopilot  [1 funcs]
    default_socket_path  CC=3  out:5
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.autopilot.cli_command  [16 funcs]
    _action_daemon  CC=9  out:15
    _action_doctor  CC=10  out:16
    _action_drive  CC=8  out:17
    _action_handoff  CC=9  out:18
    _action_ide_list  CC=3  out:3
    _action_install_unit  CC=6  out:18
    _action_shutdown  CC=3  out:7
    _action_status  CC=3  out:7
    _action_tail  CC=10  out:13
    _build_brief  CC=1  out:2
  src.koru.autopilot.client  [2 funcs]
    __init__  CC=2  out:1
    request  CC=5  out:11
  src.koru.autopilot.config  [4 funcs]
    _merge_submit_keys  CC=7  out:5
    cached_config  CC=1  out:2
    default_config_path  CC=2  out:3
    load_config  CC=4  out:10
  src.koru.autopilot.daemon  [13 funcs]
    __init__  CC=7  out:8
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=5  out:19
    _drive_via_plugin  CC=2  out:9
    _handle_ack  CC=5  out:6
    _handle_hello  CC=5  out:12
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=6  out:11
  src.koru.autopilot.ide  [7 funcs]
    _iter_proc_pids  CC=4  out:6
    _matches  CC=7  out:5
    _read_cmdline  CC=2  out:5
    _read_comm  CC=2  out:3
    detect_running_ides  CC=11  out:7
    detect_running_ides_cached  CC=4  out:2
    pick_target  CC=5  out:0
  src.koru.autopilot.injector  [2 funcs]
    type_text  CC=12  out:14
    _submit_key_for  CC=1  out:2
  src.koru.autopilot.protocol  [5 funcs]
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    chat_send  CC=1  out:1
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koru.bootstrap  [5 funcs]
    _detect_cycle  CC=10  out:13
    import_flat_pipeline  CC=9  out:12
    load_flat_pipeline  CC=9  out:12
    materialize_to_planfile  CC=6  out:16
    validate_flat_pipeline  CC=28  out:58
  src.koru.cli  [16 funcs]
    _agent_main  CC=7  out:14
    _build_gate_parser  CC=1  out:11
    _build_gc_parser  CC=1  out:14
    _build_queue_parser  CC=1  out:11
    _build_scan_parser  CC=1  out:8
    _build_serve_parser  CC=1  out:9
    _build_task_parser  CC=1  out:7
    _gate_main  CC=5  out:12
    _gc_main  CC=18  out:28
    _is_bare_invocation  CC=7  out:0
  src.koru.context  [14 funcs]
    _auto_promote_blocking_tickets  CC=25  out:24
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _fetch_all_tickets  CC=9  out:5
    _is_fixture_ticket  CC=4  out:6
    _load_project_dotenv  CC=3  out:2
    _planfile_command_base  CC=3  out:3
    _planfile_env  CC=1  out:0
  src.koru.doctor  [9 funcs]
    _check_ci_command  CC=5  out:6
    _check_planfile_config  CC=4  out:7
    _check_planfile_sprints  CC=10  out:17
    _check_planfile_sprints_yaml  CC=6  out:8
    _check_policy_yaml  CC=11  out:13
    _check_pytest_collect  CC=8  out:5
    _check_runtime_dir  CC=6  out:6
    _resolve_pytest_collect_timeout  CC=4  out:3
    run_diagnostics  CC=6  out:11
  src.koru.dotenv_loader  [3 funcs]
    _parse_value  CC=5  out:7
    load_dotenv  CC=7  out:5
    parse_dotenv  CC=5  out:7
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.gate  [2 funcs]
    _resolve_actor  CC=4  out:1
    authorize_gate  CC=9  out:16
  src.koru.gc  [8 funcs]
    _archive_tickets  CC=2  out:6
    _load_tickets_from_sprint  CC=7  out:7
    _now_utc  CC=1  out:1
    _parse_ts  CC=3  out:2
    _planfile_env  CC=1  out:0
    _run_planfile  CC=6  out:9
    collect_gc_candidates  CC=9  out:21
    run_gc  CC=26  out:22
  src.koru.init  [3 funcs]
    _ensure_gitignore_entry  CC=8  out:12
    _write_policy_stub_if_absent  CC=3  out:6
    init_project  CC=6  out:15
  src.koru.loop  [3 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
    run_closed_loop  CC=12  out:18
  src.koru.planfile_queue  [7 funcs]
    _default_human_prompt  CC=5  out:12
    _parse_next_ticket  CC=9  out:7
    _planfile_command  CC=3  out:4
    _planfile_env  CC=1  out:0
    _run_process  CC=1  out:2
    run_next_planfile_task  CC=24  out:40
    run_planfile_queue_loop  CC=12  out:8
  src.koru.policy  [2 funcs]
    load_policy  CC=9  out:43
    policy_path  CC=1  out:1
  src.koru.queue_clean  [8 funcs]
    _build_close_note  CC=1  out:4
    _close_ticket  CC=5  out:6
    _list_tickets  CC=11  out:11
    _matched_rules  CC=14  out:16
    _parse_age_days  CC=8  out:10
    _planfile_base  CC=4  out:3
    clean_queue  CC=5  out:7
    find_candidates  CC=15  out:19
  src.koru.run_log  [7 funcs]
    _emit  CC=3  out:5
    write_footer  CC=4  out:12
    write_header  CC=1  out:4
    write_iteration  CC=3  out:9
    _iso  CC=1  out:2
    open_run_log  CC=1  out:4
    open_run_log_eagerly  CC=1  out:2
  src.koru.runtime  [5 funcs]
    ensure_runs_dir  CC=2  out:5
    new_run_id  CC=1  out:3
    planfile_dir  CC=1  out:2
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [8 funcs]
    _create_ticket  CC=5  out:5
    _existing_scan_titles  CC=11  out:15
    collect_suggestions  CC=2  out:11
    run_scan  CC=7  out:11
    scan_gitignore_drift  CC=4  out:3
    scan_missing_gates  CC=5  out:6
    scan_missing_tools  CC=13  out:15
    scan_todo_markers  CC=8  out:10
  src.koru.semcod_tools  [3 funcs]
    _config_present  CC=3  out:2
    _read_pyproject  CC=3  out:3
    detect_semcod_tools  CC=7  out:9
  src.koru.serve  [3 funcs]
    _build_handler  CC=1  out:30
    build_server  CC=1  out:2
    serve  CC=4  out:12
  src.koru.tasks  [4 funcs]
    _read_config  CC=4  out:7
    _read_sprint  CC=4  out:11
    _write_yaml  CC=1  out:3
    create_nl_task  CC=5  out:17
  src.koru.watch  [2 funcs]
    format_queue_event  CC=19  out:35
    watch_planfile_events  CC=7  out:7

EDGES:
  src.koru.runtime.runtime_dir → src.koru.runtime.planfile_dir
  src.koru.runtime.runs_dir → src.koru.runtime.runtime_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runs_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runtime_dir
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._format_paths
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._default_acceptance
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._reproduction_for
  src.koru.watch.watch_planfile_events → plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect
  src.koru.watch.watch_planfile_events → src.koru.watch.format_queue_event
  src.koru.context._fetch_all_tickets → src.koru.context._safe_json
  src.koru.context._fetch_all_tickets → src.koru.context._run_planfile
  src.koru.context._fetch_all_tickets → src.koru.context._is_fixture_ticket
  src.koru.context._run_planfile → src.koru.context._planfile_command_base
  src.koru.context._run_planfile → src.koru.context._planfile_env
  src.koru.context.build_context → src.koru.context._load_project_dotenv
  src.koru.context.build_context → src.koru.runtime.planfile_dir
  src.koru.context.build_context → src.koru.context._auto_promote_blocking_tickets
  src.koru.context.build_context → src.koru.context._build_instructions
  src.koru.context.build_context → src.koru.context._build_self_service
  src.koru.context.build_context → src.koru.policy.load_policy
  src.koru.context._auto_promote_blocking_tickets → src.koru.runtime.planfile_dir
  src.koru.context._auto_promote_blocking_tickets → scripts.planfile-export-prompt.print
  src.koru.context._build_instructions → src.koru.context._build_setup_instructions
  src.koru.context._build_instructions → src.koru.context._build_shared_rules
  src.koru.semcod_tools.detect_semcod_tools → src.koru.semcod_tools._read_pyproject
  src.koru.semcod_tools.detect_semcod_tools → src.koru.semcod_tools._config_present
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.ticket_builder.build_ticket_payload
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.app._resolve_affected_files
  services.healing-webhook.app.heal_redsl_gate → services.healing-webhook.app._run_docker
  services.healing-webhook.app.heal_redsl_gate → services.healing-webhook.app._record_action
  services.healing-webhook.app.heal_redsl_improve → services.healing-webhook.app._run_docker
  services.healing-webhook.app.heal_redsl_improve → services.healing-webhook.app._record_action
  services.healing-webhook.app.heal_redsl_improve → services.healing-webhook.app._rate_limit_ok
  services.healing-webhook.app.heal_rebuild_restore → services.healing-webhook.app._run_docker
  services.healing-webhook.app.heal_rebuild_restore → services.healing-webhook.app._record_action
  services.healing-webhook.app.heal_rebuild_restore → services.healing-webhook.app._rate_limit_ok
  services.healing-webhook.app.heal_annotate → services.healing-webhook.app._record_action
  services.healing-webhook.app._resolve_affected_files → services.healing-webhook.ticket_builder._infer_paths
  services.healing-webhook.app.heal_vallm_validate → services.healing-webhook.app._resolve_affected_files
  services.healing-webhook.app.heal_vallm_validate → services.healing-webhook.app._record_action
  services.healing-webhook.app.heal_vallm_validate → services.healing-webhook.app._run_vallm_check
  services.healing-webhook.app.heal_redup_check → services.healing-webhook.app._run_redup_check
  services.healing-webhook.app.heal_redup_check → services.healing-webhook.app._record_action
  services.healing-webhook.app.alertmanager_webhook → services.healing-webhook.app._resolve_strategy
  services.healing-webhook.app.probe_failure → services.healing-webhook.app.create_planfile_ticket
  src.koru.policy.policy_path → src.koru.runtime.runtime_dir
  src.koru.policy.load_policy → src.koru.policy.policy_path
  src.koru.dotenv_loader.parse_dotenv → src.koru.dotenv_loader._parse_value
  src.koru.dotenv_loader.load_dotenv → src.koru.dotenv_loader.parse_dotenv
  src.koru.scan.collect_suggestions → src.koru.scan.scan_todo_markers
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

Closed-loop automation across semcod/* repositories.
