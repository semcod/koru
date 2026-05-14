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
- **version**: `0.1.81`
- **python_requires**: `>=3.12`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, project/(2 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.81;
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
USE_ALL_QUEUES="{{.USE_ALL_QUEUES}}" \
MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
MAX_CYCLES="{{.MAX_CYCLES}}" \
SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
INITIAL_DELAY_SECONDS="{{.INITIAL_DELAY_SECONDS}}" \
ENABLE_SCAN="{{.ENABLE_SCAN}}" \
TICKET_SOURCES="{{.TICKET_SOURCES}}" \
ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
AUTOPILOT_ACTION="{{.AUTOPILOT_ACTION}}" \
AUTOPILOT_IDE="{{.AUTOPILOT_IDE}}" \
AUTOPILOT_SUBMIT="{{.AUTOPILOT_SUBMIT}}" \
AUTOPILOT_ON_IDLE_ONLY="{{.AUTOPILOT_ON_IDLE_ONLY}}" \
AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL="{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL}}" \
DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
ENABLE_IDLE_DIAGNOSTICS="{{.ENABLE_IDLE_DIAGNOSTICS}}" \
IDLE_DIAGNOSTICS_PROFILE="{{.IDLE_DIAGNOSTICS_PROFILE}}" \
STRICT_DIAGNOSTICS="{{.STRICT_DIAGNOSTICS}}" \
ENABLE_DIAGNOSTIC_TICKETS="{{.ENABLE_DIAGNOSTIC_TICKETS}}" \
DIAGNOSTIC_TICKET_QUEUE="{{.DIAGNOSTIC_TICKET_QUEUE}}" \
DIAGNOSTIC_TICKET_PRIORITY="{{.DIAGNOSTIC_TICKET_PRIORITY}}" \
DIAG_STATE_DIR="{{.DIAG_STATE_DIR}}" \
AUTOPILOT_SKIP_STATUSES="{{.AUTOPILOT_SKIP_STATUSES}}" \
BACKOFF_ON_STAGNATION="{{.BACKOFF_ON_STAGNATION}}" \
MAX_SLEEP_SECONDS="{{.MAX_SLEEP_SECONDS}}" \
SCAN_SKIP_IF_CLEAN="{{.SCAN_SKIP_IF_CLEAN}}" \
SCAN_SKIP_AFTER="{{.SCAN_SKIP_AFTER}}" \
KORU_CMD="{{.KORU_CMD}}" \
KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
bash scripts/koru-autoloop.sh;
}

workflow[name="queue:autoloop:reset-diag-markers"] {
  trigger: manual;
  step-1: run cmd=MARKER_DIR="{{.MARKER_DIR}}" \
CHECK="{{.CHECK}}" \
CLOSE_TICKETS="{{.CLOSE_TICKETS}}" \
CLOSE_STATUS="{{.CLOSE_STATUS}}" \
KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
bash scripts/koru-autoloop-reset-diag-markers.sh;
}

workflow[name="quality:regix"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
  regix gate
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:regix skipped (gate:regix disabled in topology)"
    exit 0
  fi
  regix gate
fi;
}

workflow[name="quality:redup"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
  redup scan . --min-lines 10
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:redup skipped (gate:redup disabled in topology)"
    exit 0
  fi
  redup scan . --min-lines 10
fi;
}

workflow[name="quality:redup:check"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
  bash scripts/redup-check.sh "{{.PATH | default "."}}"
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:redup:check skipped (gate:redup disabled in topology)"
    exit 0
  fi
  bash scripts/redup-check.sh "{{.PATH | default "."}}"
fi;
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
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh --status
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:status skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh --status
fi;
}

workflow[name="quality:sumr:auto"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:auto skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh
fi;
}

workflow[name="quality:sumr:refresh"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh --force
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:refresh skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh --force
fi;
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
  target: docker-compose;
  compose_file: docker-compose.yml;
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
    desc: 'Continuous intake+execution loop (scan + queue --loop + idle diagnostics + autopilot drive). See scripts/koru-autoloop.sh header for all env vars.'
    cmds:
      - |
        PROJECT="{{.PROJECT}}" \
        ACTOR="{{.ACTOR}}" \
        QUEUE_NAME="{{.QUEUE_NAME}}" \
        USE_ALL_QUEUES="{{.USE_ALL_QUEUES}}" \
        MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
        MAX_CYCLES="{{.MAX_CYCLES}}" \
        SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
        INITIAL_DELAY_SECONDS="{{.INITIAL_DELAY_SECONDS}}" \
        ENABLE_SCAN="{{.ENABLE_SCAN}}" \
        TICKET_SOURCES="{{.TICKET_SOURCES}}" \
        ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
        ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
        AUTOPILOT_ACTION="{{.AUTOPILOT_ACTION}}" \
        AUTOPILOT_IDE="{{.AUTOPILOT_IDE}}" \
        AUTOPILOT_SUBMIT="{{.AUTOPILOT_SUBMIT}}" \
        AUTOPILOT_ON_IDLE_ONLY="{{.AUTOPILOT_ON_IDLE_ONLY}}" \
        AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL="{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL}}" \
        DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
        ENABLE_IDLE_DIAGNOSTICS="{{.ENABLE_IDLE_DIAGNOSTICS}}" \
        IDLE_DIAGNOSTICS_PROFILE="{{.IDLE_DIAGNOSTICS_PROFILE}}" \
        STRICT_DIAGNOSTICS="{{.STRICT_DIAGNOSTICS}}" \
        ENABLE_DIAGNOSTIC_TICKETS="{{.ENABLE_DIAGNOSTIC_TICKETS}}" \
        DIAGNOSTIC_TICKET_QUEUE="{{.DIAGNOSTIC_TICKET_QUEUE}}" \
        DIAGNOSTIC_TICKET_PRIORITY="{{.DIAGNOSTIC_TICKET_PRIORITY}}" \
        DIAG_STATE_DIR="{{.DIAG_STATE_DIR}}" \
        AUTOPILOT_SKIP_STATUSES="{{.AUTOPILOT_SKIP_STATUSES}}" \
        BACKOFF_ON_STAGNATION="{{.BACKOFF_ON_STAGNATION}}" \
        MAX_SLEEP_SECONDS="{{.MAX_SLEEP_SECONDS}}" \
        SCAN_SKIP_IF_CLEAN="{{.SCAN_SKIP_IF_CLEAN}}" \
        SCAN_SKIP_AFTER="{{.SCAN_SKIP_AFTER}}" \
        KORU_CMD="{{.KORU_CMD}}" \
        KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
        KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
        bash scripts/koru-autoloop.sh
    vars:
      PROJECT: '{{.PROJECT | default "."}}'
      ACTOR: '{{.ACTOR | default "koru-shell"}}'
      QUEUE_NAME: '{{.QUEUE_NAME | default ""}}'
      USE_ALL_QUEUES: '{{.USE_ALL_QUEUES | default "false"}}'
      MAX_ITERATIONS: '{{.MAX_ITERATIONS | default "50"}}'
      MAX_CYCLES: '{{.MAX_CYCLES | default "0"}}'
      SLEEP_SECONDS: '{{.SLEEP_SECONDS | default "120"}}'
      INITIAL_DELAY_SECONDS: '{{.INITIAL_DELAY_SECONDS | default "0"}}'
      ENABLE_SCAN: '{{.ENABLE_SCAN | default "true"}}'
      TICKET_SOURCES: '{{.TICKET_SOURCES | default "queue"}}'
      ENABLE_INTERACTIVE: '{{.ENABLE_INTERACTIVE | default "false"}}'
      ENABLE_AUTOPILOT_DRIVE: '{{.ENABLE_AUTOPILOT_DRIVE | default "true"}}'
      AUTOPILOT_ACTION: '{{.AUTOPILOT_ACTION | default "drive"}}'
      AUTOPILOT_IDE: '{{.AUTOPILOT_IDE | default "auto"}}'
      AUTOPILOT_SUBMIT: '{{.AUTOPILOT_SUBMIT | default "true"}}'
      AUTOPILOT_ON_IDLE_ONLY: '{{.AUTOPILOT_ON_IDLE_ONLY | default "false"}}'
      AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL: '{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL | default "true"}}'
      DRIVE_PROMPT: '{{.DRIVE_PROMPT | default "continue with the next ticket"}}'
      ENABLE_IDLE_DIAGNOSTICS: '{{.ENABLE_IDLE_DIAGNOSTICS | default "false"}}'
      IDLE_DIAGNOSTICS_PROFILE: '{{.IDLE_DIAGNOSTICS_PROFILE | default "quick"}}'
      STRICT_DIAGNOSTICS: '{{.STRICT_DIAGNOSTICS | default "false"}}'
      ENABLE_DIAGNOSTIC_TICKETS: '{{.ENABLE_DIAGNOSTIC_TICKETS | default "false"}}'
      DIAGNOSTIC_TICKET_QUEUE: '{{.DIAGNOSTIC_TICKET_QUEUE | default "default"}}'
      DIAGNOSTIC_TICKET_PRIORITY: '{{.DIAGNOSTIC_TICKET_PRIORITY | default "high"}}'
      DIAG_STATE_DIR: '{{.DIAG_STATE_DIR | default ".planfile/.koru/autoloop-diag"}}'
      AUTOPILOT_SKIP_STATUSES: '{{.AUTOPILOT_SKIP_STATUSES | default "waiting_input"}}'
      BACKOFF_ON_STAGNATION: '{{.BACKOFF_ON_STAGNATION | default "true"}}'
      MAX_SLEEP_SECONDS: '{{.MAX_SLEEP_SECONDS | default "900"}}'
      SCAN_SKIP_IF_CLEAN: '{{.SCAN_SKIP_IF_CLEAN | default "false"}}'
      SCAN_SKIP_AFTER: '{{.SCAN_SKIP_AFTER | default "1"}}'
      KORU_CMD: '{{.KORU_CMD | default "koru"}}'
      KORU_PLANFILE_CMD: '{{.KORU_PLANFILE_CMD | default "planfile"}}'
      KORU_PYTHONPATH: '{{.KORU_PYTHONPATH | default ""}}'
    interactive: true

  queue:autoloop:reset-diag-markers:
    desc: 'Clear autoloop diagnostic dedup markers; optionally close [AUTO-DIAG] tickets. Usage: task queue:autoloop:reset-diag-markers CLOSE_TICKETS=true CHECK=regix'
    cmds:
      - |
        MARKER_DIR="{{.MARKER_DIR}}" \
        CHECK="{{.CHECK}}" \
        CLOSE_TICKETS="{{.CLOSE_TICKETS}}" \
        CLOSE_STATUS="{{.CLOSE_STATUS}}" \
        KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
        KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
        bash scripts/koru-autoloop-reset-diag-markers.sh
    vars:
      MARKER_DIR: '{{.MARKER_DIR | default ".planfile/.koru/autoloop-diag"}}'
      CHECK: '{{.CHECK | default "all"}}'
      CLOSE_TICKETS: '{{.CLOSE_TICKETS | default "false"}}'
      CLOSE_STATUS: '{{.CLOSE_STATUS | default "done"}}'
      KORU_PLANFILE_CMD: '{{.KORU_PLANFILE_CMD | default "planfile"}}'
      KORU_PYTHONPATH: '{{.KORU_PYTHONPATH | default ""}}'

  # =====================================================================
  # Quality gates (LLM-free, proxies to underlying tools)
  # =====================================================================

  quality:regix:
    desc: Run regix gate locally (LLM-free regression metrics)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
          regix gate
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:regix skipped (gate:regix disabled in topology)"
            exit 0
          fi
          regix gate
        fi
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:redup:
    desc: 'Run redup duplicate detection (default: current dir)'
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
          redup scan . --min-lines 10
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:redup skipped (gate:redup disabled in topology)"
            exit 0
          fi
          redup scan . --min-lines 10
        fi
    preconditions:
      - sh: which redup
        msg: "redup not installed. Run: task install:tools"

  quality:redup:check:
    desc: Run redup with budget check (uses scripts/redup-check.sh)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
          bash scripts/redup-check.sh "{{.PATH | default "."}}"
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:redup:check skipped (gate:redup disabled in topology)"
            exit 0
          fi
          bash scripts/redup-check.sh "{{.PATH | default "."}}"
        fi

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
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh --status
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:status skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh --status
        fi
    preconditions:
      - sh: test -x scripts/sumr-refresh.sh
        msg: "scripts/sumr-refresh.sh missing. Run: task template:install:sumr"

  quality:sumr:auto:
    desc: Refresh SUMR.md only if stale (debounced; safe for hooks/cron)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:auto skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh
        fi

  quality:sumr:refresh:
    desc: Force-refresh SUMR.md (bumps sumd/code2llm/redup/doql + regenerates)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh --force
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:refresh skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh --force
        fi

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
  version: 0.1.81
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

### Docker

- **base image**: `python:3.12-slim as base`
- **entrypoint**: `["koru"]`

### Docker Compose (`docker-compose.yml`)

- **koru** image=`koru:latest`
- **koru-dev** image=`koru:dev`
- **planfile** image=`semcod/planfile:latest`
- **regix** image=`semcod/regix:latest`
- **testql** image=`semcod/testql:latest`
- **healing-webhook** image=`koru/healing-webhook:latest` ports: `8810:8810`

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
- **version files**: `VERSION`, `pyproject.toml:version`, `venv/lib/python3.13/site-packages/cryptography/__init__.py:__version__`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# koru | 139f 30729L | python:100,shell:34,javascript:2,typescript:2,less:1 | 2026-05-14
# stats: 676 func | 135 cls | 139 mod | CC̄=4.6 | critical:69 | cycles:0
# alerts[5]: CC _run_cycle=53; CC _action_up=33; CC run_next_planfile_task=32; CC _queue_run_main=26; CC detect_tools=26
# hotspots[5]: _run_cycle fan=32; _build_handler fan=30; _action_up fan=28; _build_handler fan=24; do_from_todo fan=23
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[139]:
  app.doql.less,565
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
  plugins/koru-autopilot-vscode/out/extension.js,376
  plugins/koru-autopilot-vscode/out/socketPath.js,61
  plugins/koru-autopilot-vscode/src/extension.ts,353
  plugins/koru-autopilot-vscode/src/socketPath.ts,28
  project.sh,54
  scripts/_koru_autodiag_filter_tickets.py,56
  scripts/autopilot-ide-autodetect-smoke.sh,183
  scripts/koru-autoloop-reset-diag-markers.sh,97
  scripts/koru-autoloop.sh,563
  scripts/planfile-export-prompt.sh,82
  scripts/planfile-sync-todo.py,235
  services/healing-webhook/app.py,703
  services/healing-webhook/ticket_builder.py,224
  src/koru/__init__.py,70
  src/koru/__main__.py,9
  src/koru/agents.py,339
  src/koru/autonomous.py,1268
  src/koru/autonomous_wup.py,225
  src/koru/autopilot/__init__.py,68
  src/koru/autopilot/audit.py,158
  src/koru/autopilot/cli_command.py,862
  src/koru/autopilot/client.py,94
  src/koru/autopilot/config.py,120
  src/koru/autopilot/daemon.py,533
  src/koru/autopilot/host_setup.py,208
  src/koru/autopilot/ide.py,262
  src/koru/autopilot/injector.py,290
  src/koru/autopilot/plugin_installer.py,308
  src/koru/autopilot/protocol.py,207
  src/koru/autopilot/utils/__init__.py,6
  src/koru/autopilot/utils/client_helpers.py,58
  src/koru/bootstrap.py,448
  src/koru/cli/__init__.py,56
  src/koru/cli/__main__.py,9
  src/koru/cli/commands.py,1
  src/koru/cli/parsers.py,1
  src/koru/cli.py,1900
  src/koru/context.py,1153
  src/koru/doctor.py,497
  src/koru/dotenv_loader.py,105
  src/koru/events.py,91
  src/koru/gate.py,203
  src/koru/gc.py,372
  src/koru/init.py,501
  src/koru/local_service.py,204
  src/koru/loop.py,132
  src/koru/planfile_queue.py,38
  src/koru/policy.py,235
  src/koru/project_pipeline.py,135
  src/koru/queue/__init__.py,34
  src/koru/queue/human.py,32
  src/koru/queue/locking.py,88
  src/koru/queue/loop.py,110
  src/koru/queue/runner.py,230
  src/koru/queue/runners.py,209
  src/koru/queue/ticket.py,139
  src/koru/queue/types.py,89
  src/koru/queue_clean.py,351
  src/koru/run_log.py,125
  src/koru/runtime.py,106
  src/koru/scan.py,819
  src/koru/semcod_tools.py,130
  src/koru/serve.py,1014
  src/koru/stdio_events.py,50
  src/koru/tasks.py,164
  src/koru/tools.py,251
  src/koru/topology.py,416
  src/koru/utils/__init__.py,6
  src/koru/utils/subprocess_runner.py,41
  src/koru/watch.py,82
  test-data/.planfile/.koru/run-autonomous.sh,7
  test-data/.planfile/.koru/setup-autopilot-host.sh,14
  test-data/.planfile/.koru/shell-env.sh,5
  tests/e2e/bootstrap.sh,94
  tests/e2e/init.sh,29
  tests/e2e/smoke.sh,112
  tests/test_agent_cli.py,101
  tests/test_agents.py,184
  tests/test_autonomous.py,613
  tests/test_autopilot_audit.py,124
  tests/test_autopilot_cli.py,460
  tests/test_autopilot_client_drive_errors.py,16
  tests/test_autopilot_config.py,156
  tests/test_autopilot_daemon.py,481
  tests/test_autopilot_host_setup.py,124
  tests/test_autopilot_ide.py,155
  tests/test_autopilot_injector.py,212
  tests/test_autopilot_plugin_installer.py,117
  tests/test_autopilot_protocol.py,154
  tests/test_autopilot_socket_path.py,29
  tests/test_bootstrap.py,296
  tests/test_cli.py,328
  tests/test_context.py,494
  tests/test_docker_e2e.py,548
  tests/test_doctor.py,434
  tests/test_dotenv_loader.py,117
  tests/test_e2e.py,946
  tests/test_events.py,67
  tests/test_gate.py,167
  tests/test_gc.py,277
  tests/test_init.py,244
  tests/test_local_service.py,97
  tests/test_loop.py,95
  tests/test_planfile_queue.py,1004
  tests/test_policy.py,183
  tests/test_queue_clean.py,309
  tests/test_run_log.py,139
  tests/test_runtime.py,131
  tests/test_scan.py,469
  tests/test_serve.py,276
  tests/test_stdio_autonomous_jsonl.py,99
  tests/test_tasks.py,77
  tests/test_tools.py,110
  tests/test_topology.py,55
  tests/test_watch.py,102
D:
  scripts/_koru_autodiag_filter_tickets.py:
    e: main
    main()
  scripts/planfile-sync-todo.py:
    e: _find_scripts_dir_with_settings,run_planfile,load_tickets,build_auto_section,replace_auto_section,do_from_planfile,do_from_todo,_llm_stub,main
    _find_scripts_dir_with_settings()
    run_planfile()
    load_tickets()
    build_auto_section(tickets)
    replace_auto_section(current;new_section)
    do_from_planfile(check)
    do_from_todo(heading;check)
    _llm_stub(item;heading;source_name)
    main()
  services/healing-webhook/app.py:
    e: _rate_limit_ok,_record_action,_enrich_ticket_with_vallm,_build_planfile_command,_extract_ticket_id_from_stdout,_execute_planfile_create,create_planfile_ticket,_run_docker,heal_redsl_gate,heal_redsl_improve,heal_rebuild_restore,heal_annotate,_run_vallm_check,_run_vallm_validate,_resolve_affected_files,heal_vallm_validate,_parse_redup_summary,_update_redup_metrics,_run_redup_check,heal_redup_check,_resolve_strategy,healthz,metrics,get_history,alertmanager_webhook,probe_failure,get_tickets
    _rate_limit_ok()
    _record_action(action;outcome;component;detail)
    _enrich_ticket_with_vallm(alert;payload)
    _build_planfile_command(payload)
    _extract_ticket_id_from_stdout(stdout)
    _execute_planfile_create(cmd;severity)
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
    _parse_redup_summary(payload)
    _update_redup_metrics(summary;breach)
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
  src/koru/__main__.py:
  src/koru/agents.py:
    e: _which,_marker,detect_agent_options,detect_project_environment,detect_agent_environment,select_agent,save_agent_prompt,normalize_agent_lane_id,agent_lane_environment,format_agent_lane_exports,launch_agent,AgentOption
    AgentOption: to_dict(0)
    _which(command)
    _marker(project)
    detect_agent_options(project)
    detect_project_environment(project)
    detect_agent_environment(project)
    select_agent(agents)
    save_agent_prompt(project;prompt)
    normalize_agent_lane_id(raw)
    agent_lane_environment(agent_id)
    format_agent_lane_exports(env)
    launch_agent(agent;project;prompt)
  src/koru/autonomous.py:
    e: _stdio_info,_resolve_autopilot_ide,_apply_agent_lane_environ,_build_parser,_env_default_bool,_env_apply_autoloop_defaults,_ensure_init,_start_or_reuse_daemon,_effective_flags,_queue_loop_waiting_ticket_label,_is_topology_enabled,_current_head,_compute_backoff_sleep,_status_in_skip_list,_run_command_check,_create_diagnostic_ticket,_clear_diagnostic_marker,_read_wup_health,_run_idle_diagnostics,_run_cycle,_action_up,autonomous_main,DiagnosticResult,AutoloopState
    DiagnosticResult:
    AutoloopState:
    _stdio_info(msg)
    _resolve_autopilot_ide(cli_value)
    _apply_agent_lane_environ(project;agent_lane)
    _build_parser()
    _env_default_bool(name;default)
    _env_apply_autoloop_defaults(args)
    _ensure_init(project)
    _start_or_reuse_daemon()
    _effective_flags(ticket_sources)
    _queue_loop_waiting_ticket_label(queue_result)
    _is_topology_enabled(project;key)
    _current_head(project)
    _compute_backoff_sleep(base;streak;cap;enabled)
    _status_in_skip_list(status;skip_statuses)
    _run_command_check(project;check_id;command)
    _create_diagnostic_ticket()
    _clear_diagnostic_marker(state_dir;check_id)
    _read_wup_health()
    _run_idle_diagnostics()
    _run_cycle()
    _action_up(args)
    autonomous_main(argv)
  src/koru/autonomous_wup.py:
    e: _wup_stdio_info,_wup_topology_gate,_build_wup_watch_config,_wup_watch_command,_wup_autodetect,_start_wup_watch,_stop_process,_read_wup_health,WupWatchConfig,WupHealthResult,_WupEventState
    WupWatchConfig:
    WupHealthResult:
    _WupEventState:
    _wup_stdio_info(msg)
    _wup_topology_gate(project;key)
    _build_wup_watch_config(args;project)
    _wup_watch_command(config)
    _wup_autodetect(config)
    _start_wup_watch(config)
    _stop_process(process;label)
    _read_wup_health()
  src/koru/autopilot/__init__.py:
    e: _autopilot_socket_basename,default_socket_path
    _autopilot_socket_basename()
    default_socket_path()
  src/koru/autopilot/audit.py:
    e: default_log_path,_isoformat_utc,_JSONFormatter,AuditLog
    _JSONFormatter: format(1)  # Emit ``record.msg`` verbatim — we hand it in pre-serialised.
    AuditLog: __init__(0),record(1),close(0)  # Append-only audit log for autopilot events.
    default_log_path()
    _isoformat_utc(ts)
  src/koru/autopilot/cli_command.py:
    e: _build_parser,_client,_action_daemon,_action_drive,_action_status,_action_shutdown,_action_ide_list,_doctor_fix_payload,_render_doctor_text,_render_doctor_json,_action_doctor,_action_setup_host,_plugin_repo_dir,_resolve_plugin_vsix_path,_ide_from_terminal_env,_resolve_plugin_target_ide,_resolve_plugin_editor_bin,_render_install_plugin_dry_run,_render_install_plugin_result,_action_install_plugin,_build_brief,_action_handoff,_format_tail_entry,_render_tail_json,_render_tail_text,_action_tail,_systemd_user_dir,_resolve_koru_bin,_render_unit,_action_install_unit,autopilot_main
    _build_parser()
    _client(args)
    _action_daemon(args)
    _action_drive(args)
    _action_status(args)
    _action_shutdown(args)
    _action_ide_list(_args)
    _doctor_fix_payload()
    _render_doctor_text(injector;statuses;selected;fix_payload)
    _render_doctor_json(injector;statuses;selected;fix_payload)
    _action_doctor(args)
    _action_setup_host(args)
    _plugin_repo_dir()
    _resolve_plugin_vsix_path(vsix)
    _ide_from_terminal_env()
    _resolve_plugin_target_ide(raw_ide)
    _resolve_plugin_editor_bin(ide)
    _render_install_plugin_dry_run(ide;editor_bin;vsix_path;cmd;output_format)
    _render_install_plugin_result(ide;editor_bin;cmd;ok;stdout;stderr;output_format)
    _action_install_plugin(args)
    _build_brief(project)
    _action_handoff(args)
    _format_tail_entry(entry)
    _render_tail_json(tail)
    _render_tail_text(tail)
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
  src/koru/autopilot/host_setup.py:
    e: _package_manager_hint,_human_followups,build_setup_host_report,_try_apt_install,run_host_setup,_print_text_report
    _package_manager_hint()
    _human_followups(injector;selected)
    build_setup_host_report()
    _try_apt_install(packages)
    run_host_setup()
    _print_text_report(report)
  src/koru/autopilot/ide.py:
    e: _iter_proc_pids,_read_comm,_read_cmdline,_matches,detect_running_ides,_active_window_pid_x11,detect_focused_ide_id,focused_ide,pick_target,is_linux,detect_running_ides_cached,clear_detect_cache,RunningIDE
    RunningIDE: to_dict(0)  # A single IDE process discovered on the system.
    _iter_proc_pids()
    _read_comm(pid)
    _read_cmdline(pid)
    _matches(comm;cmdline;patterns)
    detect_running_ides()
    _active_window_pid_x11()
    detect_focused_ide_id()
    focused_ide(detected)
    pick_target(detected)
    is_linux()
    detect_running_ides_cached()
    clear_detect_cache()
  src/koru/autopilot/injector.py:
    e: _submit_key_for,_which,_session_type,_forced_injector_backend,_default_runner,BackendStatus,InjectionResult,InjectorError,Injector
    BackendStatus: to_dict(0)  # Result of probing a single backend.
    InjectionResult: to_dict(0)
    InjectorError:  # No usable backend, or the backend call failed.
    Injector: probe(0),_candidate_backends(0),select_backend(0),_type_with_backend(3),type_text(1),_probe_one(1),_call(1),_press_wtype(1)  # Pick the best available backend and type text through it.
    _submit_key_for(ide)
    _which(name)
    _session_type()
    _forced_injector_backend()
    _default_runner(cmd;stdin)
  src/koru/autopilot/plugin_installer.py:
    e: _valid_ide,_ide_from_terminal_env,resolve_target_ide,resolve_extension_vsix,_resolve_ide_command,_settings_path_for_ide,_configure_socket_path,_run,_extension_is_installed,install_plugin_for_ide,format_plugin_install_result,PluginInstallResult
    PluginInstallResult: to_dict(0)
    _valid_ide(raw)
    _ide_from_terminal_env()
    resolve_target_ide(requested)
    resolve_extension_vsix()
    _resolve_ide_command(ide)
    _settings_path_for_ide(ide)
    _configure_socket_path(ide;socket_path)
    _run(cmd)
    _extension_is_installed(command;runner)
    install_plugin_for_ide()
    format_plugin_install_result(result)
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
  src/koru/autopilot/utils/__init__.py:
  src/koru/autopilot/utils/client_helpers.py:
    e: call_daemon_method,resolve_xdg_path
    call_daemon_method(client;method_name;error_message_prefix;not_running_return_code)
    resolve_xdg_path(relative_path)
  src/koru/bootstrap.py:
    e: load_flat_pipeline,_validate_id,_validate_name,_validate_status,_validate_priority,_validate_executor,_validate_execution_state,_validate_blocked_by,_validate_task,_validate_cross_task_dependencies,validate_flat_pipeline,_detect_cycle,materialize_to_planfile,_normalise_task,_next_id_after,import_flat_pipeline,_infer_prefix,ValidationError,ImportReport
    ValidationError: __str__(0)
    ImportReport: summary(0)
    load_flat_pipeline(path)
    _validate_id(task;seen_ids)
    _validate_name(task)
    _validate_status(task)
    _validate_priority(task)
    _validate_executor(task)
    _validate_execution_state(task)
    _validate_blocked_by(task)
    _validate_task(task;seen_ids)
    _validate_cross_task_dependencies(tasks)
    validate_flat_pipeline(tasks)
    _detect_cycle(tasks)
    materialize_to_planfile(flat_tasks;project_dir)
    _normalise_task(task)
    _next_id_after(tasks;prefix)
    import_flat_pipeline(flat_path;project_dir)
    _infer_prefix(tasks)
  src/koru/cli/__init__.py:
    e: _load_legacy_cli_module,__getattr__
    _load_legacy_cli_module()
    __getattr__(name)
  src/koru/cli/__main__.py:
  src/koru/cli/commands.py:
  src/koru/cli/parsers.py:
  src/koru/cli.py:
    e: _env_truthy,_command_value,_build_parser,_build_tools_parser,_tools_main,_build_task_parser,_build_serve_parser,_build_local_serve_parser,_build_scan_parser,_render_scan_text,_render_scan_markdown,_scan_main,_build_gate_parser,_gate_main,_build_gc_parser,_gc_main,_build_queue_parser,_render_clean_report_text,_queue_main,_build_agent_parser,_task_main,_serve_main,_local_serve_main,_agent_main,_is_bare_invocation,_build_topology_parser,_render_topology_text,_topology_main,_build_runtime_context_parser,_render_runtime_context_text,_runtime_context_main,_doctor_main,_init_main,_init_agent_lane_main,_context_main,_bootstrap_main,_watch_main,_queue_run_main,_command_loop_main,main
    _env_truthy(name)
    _command_value(value)
    _build_parser()
    _build_tools_parser()
    _tools_main(argv)
    _build_task_parser()
    _build_serve_parser()
    _build_local_serve_parser()
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
    _local_serve_main(argv)
    _agent_main(argv)
    _is_bare_invocation(args)
    _build_topology_parser()
    _render_topology_text(topology)
    _topology_main(argv)
    _build_runtime_context_parser()
    _render_runtime_context_text(context)
    _runtime_context_main(argv)
    _doctor_main(args;raw_args)
    _init_main(args)
    _init_agent_lane_main(args)
    _context_main(args)
    _bootstrap_main(args)
    _watch_main(args)
    _queue_run_main(args)
    _command_loop_main(args)
    main()
  src/koru/context.py:
    e: _is_fixture_ticket,_resolve_include_fixtures,_load_project_dotenv,_planfile_command_base,_planfile_env,_fetch_all_tickets,_run_planfile,_safe_json,_git_probe,_build_ticket_args,_try_fallback_ticket_list,_process_list_payload,_process_dict_payload,_extract_error_from_stderr,_fetch_ticket_data,build_context,_load_sprint_data,_find_blocking_tickets,_promote_blocking_to_critical,_promote_bug_priority,_write_sprint_data,_auto_promote_blocking_tickets,_build_instructions,_build_setup_instructions,_build_shared_rules,_build_self_service,_render_header,_render_environment,_render_agent_lanes,_render_autonomous_mode,_render_ai_tool_support_2026,_render_semcod_tools,_render_setup_required,_render_active_ticket,_render_no_active_ticket,_render_gates,_render_project_pipeline,_render_policy,_render_rules,_render_self_service,_render_dashboard,render_markdown_handoff
    _is_fixture_ticket(ticket)
    _resolve_include_fixtures(explicit)
    _load_project_dotenv(project)
    _planfile_command_base()
    _planfile_env()
    _fetch_all_tickets(project)
    _run_planfile(project;args;runner)
    _safe_json(text)
    _git_probe(project)
    _build_ticket_args(ticket_id;queue_name)
    _try_fallback_ticket_list(project;planfile_runner)
    _process_list_payload(ticket_data;include_fixtures)
    _process_dict_payload(ticket_data;ticket_id;include_fixtures)
    _extract_error_from_stderr(stderr)
    _fetch_ticket_data(project;ticket_id;queue_name;planfile_present;planfile_runner;include_fixtures)
    build_context()
    _load_sprint_data(project)
    _find_blocking_tickets(tickets)
    _promote_blocking_to_critical(tickets;blocking_tickets)
    _promote_bug_priority(tickets)
    _write_sprint_data(project;sprint_data)
    _auto_promote_blocking_tickets(project;runner)
    _build_instructions(policy;ticket)
    _build_setup_instructions()
    _build_shared_rules(policy;ticket)
    _build_self_service(policy;ticket)
    _render_header(project)
    _render_environment(env;project)
    _render_agent_lanes(agents)
    _render_autonomous_mode()
    _render_ai_tool_support_2026()
    _render_semcod_tools(semcod_tools)
    _render_setup_required(project)
    _render_active_ticket(ticket)
    _render_no_active_ticket(ticket_error)
    _render_gates(markers)
    _render_project_pipeline(pipeline)
    _render_policy(policy)
    _render_rules(instructions)
    _render_self_service(self_service)
    _render_dashboard()
    render_markdown_handoff(context)
  src/koru/doctor.py:
    e: run_diagnostics,_check_git_repo,_check_planfile_binary,_planfile_version_argv,_check_koru_package_version,_check_planfile_cli_version,_check_planfile_config,_check_planfile_sprints,_check_planfile_sprints_yaml,_check_runtime_dir,_check_koru_project_pipeline,_check_policy_yaml,_check_gitignore,_resolve_pytest_collect_timeout,_check_pytest_collect,_check_ci_command,render_text,Check,DoctorReport
    Check: to_dict(0)  # A single diagnostic outcome.
    DoctorReport: has_failures(0),has_warnings(0),summary(0),to_dict(0)  # Aggregate result of ``run_diagnostics``.
    run_diagnostics(project)
    _check_git_repo(project)
    _check_planfile_binary(_project)
    _planfile_version_argv()
    _check_koru_package_version(_project)
    _check_planfile_cli_version(project)
    _check_planfile_config(project)
    _check_planfile_sprints(project)
    _check_planfile_sprints_yaml(project)
    _check_runtime_dir(project)
    _check_koru_project_pipeline(project)
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
    e: _now_utc,_parse_ts,_planfile_env,_run_planfile,_load_tickets_from_sprint,_archive_tickets,collect_gc_candidates,_apply_keep_last,_archive_tickets_before_delete,_delete_tickets,run_gc,GcCandidate,GcResult
    GcCandidate:  # A ticket eligible for garbage collection.
    GcResult: summary(0)  # Outcome of a gc run.
    _now_utc()
    _parse_ts(raw)
    _planfile_env()
    _run_planfile(args;project;runner)
    _load_tickets_from_sprint(project;sprint)
    _archive_tickets(tickets;project)
    collect_gc_candidates(project)
    _apply_keep_last(candidates;keep_last;kept_ids)
    _archive_tickets_before_delete(to_remove;project;sprint)
    _delete_tickets(to_remove;project;planfile_runner)
    run_gc(project)
  src/koru/init.py:
    e: init_project,refresh_init_agent_lane,_resolve_init_agent_lane,resolve_project_agent_lane,_write_autopilot_host_setup_script,_write_agent_lane_artifacts,_remove_agent_lane_artifacts,_write_policy_stub_if_absent,_ensure_gitignore_entry,InitReport
    InitReport: summary(0)  # Summary of what ``init_project`` actually changed on disk.
    init_project(project)
    refresh_init_agent_lane(project)
    _resolve_init_agent_lane(project;agent_lane)
    resolve_project_agent_lane(project;agent_lane)
    _write_autopilot_host_setup_script(project)
    _write_agent_lane_artifacts(project;lane)
    _remove_agent_lane_artifacts(rt)
    _write_policy_stub_if_absent(project)
    _ensure_gitignore_entry(project)
  src/koru/local_service.py:
    e: _koru_version,_env_int,default_local_service_config,_build_handler,build_local_service_server,run_local_service,start_local_service_background,LocalServiceConfig,_EventBuffer
    LocalServiceConfig:  # Configuration for ``koru local-serve``.
    _EventBuffer: __init__(1),append(1),snapshot(0)  # Thread-safe ring of recent event records (oldest dropped at 
    _koru_version()
    _env_int(name;default)
    default_local_service_config()
    _build_handler(buffer;koru_version)
    build_local_service_server(config)
    run_local_service(config)
    start_local_service_background(config)
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
  src/koru/policy.py:
    e: policy_path,load_policy,policy_violations,Policy
    Policy: to_dict(0)  # Resolved policy for an LLM agent operating on a koru project
    policy_path(project)
    load_policy(project)
    policy_violations(policy;command)
  src/koru/project_pipeline.py:
    e: project_pipeline_path,default_koru_project_pipeline_text,write_koru_project_pipeline_if_absent,load_koru_project_pipeline,build_project_pipeline_brief
    project_pipeline_path(project)
    default_koru_project_pipeline_text()
    write_koru_project_pipeline_if_absent(project)
    load_koru_project_pipeline(project)
    build_project_pipeline_brief(project)
  src/koru/queue/__init__.py:
  src/koru/queue/human.py:
    e: default_human_prompt
    default_human_prompt(prompt;ticket_id)
  src/koru/queue/locking.py:
    e: queue_lock_wanted,queue_runner_lock,claim_lease_seconds_str,ticket_claim_or_error
    queue_lock_wanted()
    queue_runner_lock(project)
    claim_lease_seconds_str()
    ticket_claim_or_error(project;ticket_id;actor)
  src/koru/queue/loop.py:
    e: run_planfile_queue_loop
    run_planfile_queue_loop()
  src/koru/queue/runner.py:
    e: run_next_planfile_task
    run_next_planfile_task()
  src/koru/queue/runners.py:
    e: _planfile_env,run_process,run_shell_command,run_api_request,run_llm_request
    _planfile_env()
    run_process(command;project)
    run_shell_command(command;project)
    run_api_request(request;_project)
    run_llm_request(request;_project)
  src/koru/queue/ticket.py:
    e: parse_next_ticket,ticket_command,ticket_llm_request,ticket_api_request,planfile_command,result_json
    parse_next_ticket(stdout)
    ticket_command(ticket)
    ticket_llm_request(ticket)
    ticket_api_request(ticket)
    planfile_command(project;args;runner)
    result_json(result)
  src/koru/queue/types.py:
    e: CommandResult,QueueRunResult,QueueLoopResult,ApiRunResult,LlmRunResult
    CommandResult:  # Protocol for subprocess-like command results.
    QueueRunResult:  # Result of a single queue tick.
    QueueLoopResult: ticket_id(0),summary(0)  # Aggregate result of draining the planfile queue with run_pla
    ApiRunResult:  # Result of a direct HTTP API executor call.
    LlmRunResult:  # Result of an OpenRouter (or compatible) chat-completion call
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
    e: scan_pytest_collect,_load_koruignore_patterns,_is_koruignored,scan_todo_markers,scan_missing_gates,scan_missing_tools,scan_gitignore_drift,_scan_jscpd_report,_scan_code2llm_analysis,_scan_testql_export,_scan_redup_filtered,scan_semcod_quality_artifacts,collect_suggestions,_existing_scan_titles,_create_ticket,run_scan,Suggestion,ScanResult
    Suggestion: to_dict(0)  # One proposed planfile ticket derived from a repo signal.
    ScanResult: to_dict(0)  # Aggregate output of ``run_scan``.
    scan_pytest_collect(project)
    _load_koruignore_patterns(project)
    _is_koruignored(rel_path;patterns)
    scan_todo_markers(project)
    scan_missing_gates(project)
    scan_missing_tools(project)
    scan_gitignore_drift(project)
    _scan_jscpd_report(project)
    _scan_code2llm_analysis(project)
    _scan_testql_export(project)
    _scan_redup_filtered(project)
    scan_semcod_quality_artifacts(project)
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
    e: serve_endpoint_path,read_serve_endpoint,_build_handler,build_server,write_serve_endpoint_file,bind_serve_server,serve,start_serve_background,ServeConfig
    ServeConfig:
    serve_endpoint_path(project)
    read_serve_endpoint(project)
    _build_handler(config)
    build_server(config)
    write_serve_endpoint_file(config)
    bind_serve_server(config)
    serve(config)
    start_serve_background(config)
  src/koru/stdio_events.py:
    e: iso_ts,write_stdio_event,default_stdio_format_from_env
    iso_ts()
    write_stdio_event(stream)
    default_stdio_format_from_env()
  src/koru/tasks.py:
    e: create_nl_task,_title_from_text,_read_config,_read_sprint,_write_yaml,CreatedTask
    CreatedTask:
    create_nl_task(project;text)
    _title_from_text(text)
    _read_config(path)
    _read_sprint(path)
    _write_yaml(path;data)
  src/koru/tools.py:
    e: default_registry_path,resolve_registry_path,load_tool_registry,_first_token,detect_tools,find_tool_entry,infer_adapter_kind,build_tool_task_scaffold,render_tools_detect_text
    default_registry_path()
    resolve_registry_path(path_override)
    load_tool_registry(path_override)
    _first_token(command)
    detect_tools(project;registry)
    find_tool_entry(registry;tool_id)
    infer_adapter_kind(tool)
    build_tool_task_scaffold(tool)
    render_tools_detect_text(results)
  src/koru/topology.py:
    e: topology_path,_read_yaml,_merge_components,_merge_pipelines,load_topology,_strip_to_persisted,save_topology,_toggle,set_component_enabled,set_pipeline_enabled,is_component_enabled,is_pipeline_enabled,enabled_components_for_pipeline,default_component_ids,default_pipeline_ids,ToggleResult
    ToggleResult:  # Outcome of a single enable/disable mutation.
    topology_path(project)
    _read_yaml(path)
    _merge_components(saved;detected)
    _merge_pipelines(saved)
    load_topology(project)
    _strip_to_persisted(topology)
    save_topology(project;topology)
    _toggle(topology;section;target_id;enabled)
    set_component_enabled(topology;component_id;enabled)
    set_pipeline_enabled(topology;pipeline_id;enabled)
    is_component_enabled(project;component_id)
    is_pipeline_enabled(project;pipeline_id)
    enabled_components_for_pipeline(project;pipeline_id)
    default_component_ids()
    default_pipeline_ids()
  src/koru/utils/__init__.py:
  src/koru/utils/subprocess_runner.py:
    e: default_subprocess_runner,resolve_planfile_subpath,get_python_cmd
    default_subprocess_runner(cmd;cwd)
    resolve_planfile_subpath(project)
    get_python_cmd(project)
  src/koru/watch.py:
    e: format_queue_event,_default_connect,watch_planfile_events
    format_queue_event(event)
    _default_connect(ws_url)
    watch_planfile_events(ws_url)
  tests/test_agent_cli.py:
    e: _run_main,test_agent_list_json_includes_ready_summary,test_agent_env_exports_cursor_lane
    _run_main()
    test_agent_list_json_includes_ready_summary()
    test_agent_env_exports_cursor_lane()
  tests/test_agents.py:
    e: TestAgentDetection,TestAgentLaneEnv
    TestAgentDetection: test_detects_project_hints_without_cli(0),test_detects_openrouter_lane_from_env(0),test_select_agent_prefers_launchable_when_noninteractive(0),test_detects_gemini_cli_when_available(0),test_select_agent_can_pick_gemini_when_only_launchable(0),test_detects_cline_when_available(0),test_select_agent_can_pick_cline_when_only_launchable(0),test_agent_lane_environment_cursor(0),test_normalize_agent_lane_id_strips_garbage(0),test_format_agent_lane_exports_is_shell_safe(0),test_detects_qwen_code_when_available(0),test_select_agent_can_pick_qwen_when_only_launchable(0),test_detects_opencode_when_available(0),test_select_agent_can_pick_opencode_when_only_launchable(0)
    TestAgentLaneEnv: test_qwen_lane_env_defaults(0),test_opencode_lane_env_defaults(0)
  tests/test_autonomous.py:
    e: test_effective_flags_matrix,test_queue_loop_result_summary_includes_waiting_ticket,test_queue_loop_waiting_ticket_label_helper,test_resolve_autopilot_ide_env_overrides_cli,test_resolve_autopilot_ide_ignores_bad_env,test_resolve_autopilot_ide_auto_env_does_not_override_cli,test_apply_agent_lane_environ_auto_cursor,test_apply_agent_lane_environ_none_is_noop,test_autonomous_main_prepends_up_for_flags,test_up_single_cycle_queue_only_no_autopilot,test_up_single_cycle_all_sources_runs_scan,test_up_auto_installs_plugin_before_autopilot_loop,test_run_cycle_skips_autopilot_when_queue_waits_for_input,test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list,test_up_stops_on_waiting_input_by_default,test_up_restarts_autopilot_when_socket_disappears_between_cycles,test_compute_backoff_sleep_caps_stagnation,test_env_apply_autoloop_defaults_enables_full_diagnostics,test_run_idle_diagnostics_profile_off_message,test_run_idle_diagnostics_creates_deduped_ticket,test_wup_watch_command_uses_testql_mode,test_read_wup_health_creates_high_priority_planfile_ticket
    test_effective_flags_matrix()
    test_queue_loop_result_summary_includes_waiting_ticket()
    test_queue_loop_waiting_ticket_label_helper()
    test_resolve_autopilot_ide_env_overrides_cli(monkeypatch)
    test_resolve_autopilot_ide_ignores_bad_env(monkeypatch)
    test_resolve_autopilot_ide_auto_env_does_not_override_cli(monkeypatch)
    test_apply_agent_lane_environ_auto_cursor(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_none_is_noop(tmp_path;monkeypatch)
    test_autonomous_main_prepends_up_for_flags(tmp_path;monkeypatch)
    test_up_single_cycle_queue_only_no_autopilot(tmp_path;monkeypatch)
    test_up_single_cycle_all_sources_runs_scan(tmp_path;monkeypatch)
    test_up_auto_installs_plugin_before_autopilot_loop(tmp_path;monkeypatch)
    test_run_cycle_skips_autopilot_when_queue_waits_for_input(tmp_path;monkeypatch)
    test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list(tmp_path;monkeypatch;capsys)
    test_up_stops_on_waiting_input_by_default(tmp_path;monkeypatch)
    test_up_restarts_autopilot_when_socket_disappears_between_cycles(tmp_path;monkeypatch)
    test_compute_backoff_sleep_caps_stagnation()
    test_env_apply_autoloop_defaults_enables_full_diagnostics(monkeypatch)
    test_run_idle_diagnostics_profile_off_message(tmp_path;capsys)
    test_run_idle_diagnostics_creates_deduped_ticket(tmp_path;monkeypatch)
    test_wup_watch_command_uses_testql_mode(tmp_path)
    test_read_wup_health_creates_high_priority_planfile_ticket(tmp_path)
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
    e: test_autopilot_parser_requires_action,test_drive_without_daemon_errors,test_drive_dry_run_direct,test_ide_list_empty,test_ide_list_marks_focused_ide,test_doctor_json_output,test_doctor_fix_text_output,test_doctor_fix_json_output,test_install_plugin_dry_run_auto_detect_from_term_program,test_install_plugin_auto_detect_ambiguous_running_ides_errors,test_install_plugin_exec_success_json_payload,test_status_when_no_daemon,test_shutdown_when_no_daemon,test_handoff_dry_run_prints_brief_and_skips_daemon,test_handoff_requires_running_daemon,test_handoff_drives_brief_through_client,_write_audit_log,test_tail_text_format_renders_entries,test_tail_json_format_returns_array,test_tail_n_limits_output,test_tail_missing_log_errors_cleanly,test_tail_skips_malformed_lines,test_install_unit_print_renders_execstart,test_install_unit_writes_to_xdg_default_path,test_install_unit_refuses_overwrite_without_force,test_resolve_koru_bin_falls_back_to_sys_executable_sibling
    test_autopilot_parser_requires_action()
    test_drive_without_daemon_errors(capsys;tmp_path)
    test_drive_dry_run_direct(capsys;monkeypatch)
    test_ide_list_empty(capsys;monkeypatch)
    test_ide_list_marks_focused_ide(capsys;monkeypatch)
    test_doctor_json_output(capsys;monkeypatch)
    test_doctor_fix_text_output(capsys;monkeypatch)
    test_doctor_fix_json_output(capsys;monkeypatch)
    test_install_plugin_dry_run_auto_detect_from_term_program(capsys;monkeypatch;tmp_path)
    test_install_plugin_auto_detect_ambiguous_running_ides_errors(capsys;monkeypatch)
    test_install_plugin_exec_success_json_payload(capsys;monkeypatch;tmp_path)
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
  tests/test_autopilot_client_drive_errors.py:
    e: test_drive_missing_socket_returns_ok_false
    test_drive_missing_socket_returns_ok_false(tmp_path)
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
  tests/test_autopilot_host_setup.py:
    e: test_build_setup_host_report_has_expected_keys,test_build_setup_host_report_json_roundtrip,test_run_host_setup_install_dry_run_no_sudo,test_run_host_setup_install_calls_apt_when_missing,test_autopilot_cli_setup_host_invokes_runner
    test_build_setup_host_report_has_expected_keys()
    test_build_setup_host_report_json_roundtrip()
    test_run_host_setup_install_dry_run_no_sudo(monkeypatch)
    test_run_host_setup_install_calls_apt_when_missing(monkeypatch)
    test_autopilot_cli_setup_host_invokes_runner()
  tests/test_autopilot_ide.py:
    e: fake_proc,test_detect_running_ides_finds_windsurf_and_jetbrains,test_detect_running_ides_deduplicates_same_ide,test_detect_running_ides_skips_unknown_processes,test_pick_target_prefers_user_choice,test_pick_target_returns_none_when_pref_not_running,test_pick_target_defaults_to_first,test_pick_target_empty_list_returns_none,test_detect_focused_ide_id_from_active_pid,test_detect_focused_ide_id_returns_none_for_unknown_pid,test_focused_ide_returns_matching_instance,test_pick_target_prefers_focused_when_no_explicit_prefer,test_pick_target_explicit_prefer_beats_focus,test_detect_cached_uses_cache_within_ttl,test_detect_cached_ttl_zero_always_refreshes,test_clear_detect_cache_forces_refresh
    fake_proc(tmp_path;monkeypatch)
    test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc)
    test_detect_running_ides_deduplicates_same_ide(fake_proc)
    test_detect_running_ides_skips_unknown_processes(fake_proc)
    test_pick_target_prefers_user_choice(fake_proc)
    test_pick_target_returns_none_when_pref_not_running(fake_proc)
    test_pick_target_defaults_to_first(fake_proc)
    test_pick_target_empty_list_returns_none()
    test_detect_focused_ide_id_from_active_pid(fake_proc)
    test_detect_focused_ide_id_returns_none_for_unknown_pid(fake_proc)
    test_focused_ide_returns_matching_instance(fake_proc)
    test_pick_target_prefers_focused_when_no_explicit_prefer(fake_proc)
    test_pick_target_explicit_prefer_beats_focus(fake_proc)
    test_detect_cached_uses_cache_within_ttl(monkeypatch)
    test_detect_cached_ttl_zero_always_refreshes(monkeypatch)
    test_clear_detect_cache_forces_refresh(monkeypatch)
  tests/test_autopilot_injector.py:
    e: _fake_runner,_which_factory,test_select_backend_x11_prefers_xdotool,test_select_backend_wayland_prefers_wtype_over_ydotool,test_select_backend_wayland_falls_back_to_ydotool,test_select_backend_no_tools_returns_none,test_type_text_dry_run_does_not_call_runner,test_type_text_xdotool_types_and_submits,test_type_text_wtype_uses_modifiers_for_jetbrains,test_type_text_no_submit_only_types,test_type_text_propagates_runner_error,test_type_text_empty_raises,test_type_text_no_backend_raises,test_probe_marks_unavailable_when_missing_tool,test_probe_marks_unavailable_on_wrong_session,test_wtype_rejects_multi_modifier_submit_key,test_type_text_wayland_falls_back_when_wtype_fails,test_injector_forced_backend,test_wtype_single_modifier_still_works
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
    test_type_text_wayland_falls_back_when_wtype_fails()
    test_injector_forced_backend(monkeypatch)
    test_wtype_single_modifier_still_works()
  tests/test_autopilot_plugin_installer.py:
    e: test_resolve_target_ide_prefers_autopilot_env,test_resolve_target_ide_uses_running_supported_ide,test_resolve_target_ide_uses_integrated_terminal_hint,test_install_plugin_dry_run_builds_editor_command,test_install_plugin_configures_socket_path,test_install_plugin_skips_when_extension_already_installed
    test_resolve_target_ide_prefers_autopilot_env(monkeypatch)
    test_resolve_target_ide_uses_running_supported_ide(monkeypatch)
    test_resolve_target_ide_uses_integrated_terminal_hint(monkeypatch)
    test_install_plugin_dry_run_builds_editor_command(tmp_path;monkeypatch)
    test_install_plugin_configures_socket_path(tmp_path;monkeypatch)
    test_install_plugin_skips_when_extension_already_installed(monkeypatch)
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
  tests/test_autopilot_socket_path.py:
    e: test_explicit_socket_env_overrides_all,test_instance_env_changes_basename,test_default_basename_legacy_when_no_instance
    test_explicit_socket_env_overrides_all(monkeypatch;tmp_path)
    test_instance_env_changes_basename(monkeypatch)
    test_default_basename_legacy_when_no_instance(monkeypatch)
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
    e: _tmp_git_project,_run_main,TestBareInvocation,TestDoctorDispatch,TestInitDispatch,TestInitAgentLaneDispatch,TestContextDispatch,TestBareEmitsMarkdown,TestTopologySubcommand,TestSubcommandDispatch
    TestBareInvocation: _parse(0),test_no_args_is_bare(0),test_project_only_is_bare(0),test_init_is_not_bare(0),test_init_agent_lane_is_not_bare(0),test_doctor_is_not_bare(0),test_context_is_not_bare(0),test_queue_is_not_bare(0),test_watch_is_not_bare(0),test_bootstrap_is_not_bare(0),test_command_is_not_bare(0)  # ``koru`` with no action flag should route to markdown brief.
    TestDoctorDispatch: setUp(0),tearDown(0),test_doctor_default_is_text(0),test_doctor_json(0),test_doctor_exit_0_on_no_failures(0)  # --doctor uses text by default, json when --format json.
    TestInitDispatch: setUp(0),tearDown(0),test_init_creates_planfile(0),test_init_duplicate_rejected(0),test_init_agent_lane_none_skips_helpers(0)  # --init creates project scaffold.
    TestInitAgentLaneDispatch: setUp(0),tearDown(0),test_fails_without_planfile(0),test_ok_when_planfile_exists(0)  # --init-agent-lane refreshes shell helpers without full re-in
    TestContextDispatch: setUp(0),tearDown(0),test_context_json_default(0),test_context_markdown(0)  # --context emits JSON or markdown.
    TestBareEmitsMarkdown: setUp(0),tearDown(0),test_bare_produces_markdown(0)  # Bare ``koru`` should produce a markdown brief.
    TestTopologySubcommand: setUp(0),tearDown(0),test_topology_json_lists_components_and_pipelines(0),test_topology_disable_then_is_enabled_false(0),test_topology_enabled_components_for_pipeline(0)
    TestSubcommandDispatch: test_table_contains_all_documented_subcommands(0),test_table_values_are_callables(0),test_each_subcommand_routes_to_its_handler(0),test_unknown_first_arg_falls_through_to_argparse(0),test_empty_argv_does_not_call_any_handler(0)  # R6: routing through ``_SUBCOMMANDS`` dispatch table.
    _tmp_git_project(prefix)
    _run_main()
  tests/test_context.py:
    e: _ok,_fail,_no_git,_init_planfile,TestBuildContext,TestMarkdownHandoff,TestProjectPipelineInHandoff,TestSetupRequired
    TestBuildContext: test_brief_with_runnable_ticket(0),test_brief_when_queue_idle(0),test_brief_when_planfile_errors(0),test_specific_ticket_uses_show(0),test_instructions_include_no_commit_rule(0),test_instructions_include_ci_command_when_set(0),test_self_service_includes_concrete_ticket_commands(0),test_brief_is_json_serialisable(0),test_files_in_scope_appear_in_instructions(0),test_fixture_tickets_are_skipped_by_default(0),test_real_ticket_picked_over_fixture_in_mixed_queue(0),test_include_fixtures_flag_brings_them_back(0),test_single_object_fixture_is_filtered(0),test_explicit_ticket_id_bypasses_fixture_filter(0),test_all_tickets_are_populated_from_list(0)
    TestMarkdownHandoff: test_renders_ticket_section(0),test_renders_policy_table(0),test_renders_idle_brief_without_crash(0)
    TestProjectPipelineInHandoff: test_context_includes_pipeline_when_koru_yaml_present(0),test_pipeline_absent_without_koru_yaml(0)
    TestSetupRequired: test_instructions_swap_to_setup_guide(0),test_self_service_exposes_init_only(0),test_environment_planfile_initialised_false(0),test_markdown_renders_setup_required_block(0)  # When planfile is not initialised, the brief must steer to ko
    _ok(stdout)
    _fail(stderr)
    _no_git(_project)
    _init_planfile(project)
  tests/test_docker_e2e.py:
    e: TestDockerE2E,TestDockerComposeIntegration
    TestDockerE2E: docker_image(0),test_project(1),test_docker_image_builds_successfully(1),test_koru_help_in_docker(1),test_koru_doctor_in_docker(1),test_koru_init_in_docker(1),test_task_creation_with_priority_in_docker(2),test_autonomous_mode_single_cycle_in_docker(2),test_priority_ordering_in_docker(2),test_external_tool_detection_in_docker(1),test_agent_detection_in_docker(1),test_full_workflow_in_docker(2)  # Test Koru functionality in Docker containers.
    TestDockerComposeIntegration: test_docker_compose_build(0),test_docker_compose_test_profile(0),test_docker_compose_deps_profile(0)  # Test Docker Compose integration.
  tests/test_doctor.py:
    e: _scaffold,_run,_named,TestHappyPath,TestKoruProjectPipelineProbe,TestPlanfileCliVersionProbe,TestGitRepoCheck,TestPlanfileBinary,TestPlanfileConfigCheck,TestSprintsCheck,TestPolicyYamlCheck,TestGitignoreCheck,TestCiCommandCheck,TestPytestCollectProbe,TestReportShape
    TestHappyPath: test_full_scaffold_passes_all_required_checks(0)
    TestKoruProjectPipelineProbe: test_warns_when_planfile_ok_but_koru_yaml_missing(0)
    TestPlanfileCliVersionProbe: test_parses_version_from_stderr(0)
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
    TestE2ETask: setUp(0),tearDown(0),test_task_creates_ticket(0),test_task_increments_id(0),test_task_empty_text_fails(0),test_task_with_priority(0),test_task_with_tool_scaffold(0),test_task_with_plugin_bridge_scaffold(0)  # koru task "..." creates a ticket in the sprint YAML.
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
    e: TestStarterInit,TestForceAndConflicts,TestFromExternalPipeline,TestRuntimeContract,TestAgentLaneArtifacts,TestRefreshInitAgentLane
    TestStarterInit: test_creates_planfile_layout(0),test_writes_policy_stub_and_loads_safe_defaults(0),test_policy_stub_constant_is_valid_yaml(0),test_appends_gitignore_entry(0),test_gitignore_idempotent(0),test_preserves_existing_gitignore_content(0),test_policy_stub_not_overwritten_on_force(0),test_no_starter_yaml_left_behind(0),test_writes_koru_yaml_on_first_init(0),test_force_init_preserves_existing_koru_yaml(0)
    TestForceAndConflicts: test_re_init_without_force_raises(0),test_re_init_with_force_succeeds(0)
    TestFromExternalPipeline: test_imports_user_supplied_pipeline(0)
    TestRuntimeContract: test_init_does_not_leave_files_outside_planfile(0)
    TestAgentLaneArtifacts: test_auto_local_writes_shell_helpers(0),test_auto_cursor_when_dot_cursor(0),test_none_skips_helpers(0)
    TestRefreshInitAgentLane: test_requires_planfile(0),test_writes_after_init_with_agent_lane_none(0)
  tests/test_local_service.py:
    e: _urlopen_json,_urlopen_bytes,local_service_server,test_health_returns_ok_and_version,test_post_event_roundtrip_and_ndjson_events,test_post_enqueue_alias,test_post_empty_body_is_400,test_unknown_path_404
    _urlopen_json(url)
    _urlopen_bytes(url)
    local_service_server()
    test_health_returns_ok_and_version(local_service_server)
    test_post_event_roundtrip_and_ndjson_events(local_service_server)
    test_post_enqueue_alias(local_service_server)
    test_post_empty_body_is_400(local_service_server)
    test_unknown_path_404(local_service_server)
  tests/test_loop.py:
    e: TestKoruLoop
    TestKoruLoop: test_search_root_for_include_uses_literal_prefix(0),test_discover_repositories_with_pattern(0),test_run_closed_loop_retries_failed_repositories(0),test_run_closed_loop_single_round_when_all_succeed(0),test_command_value_rejects_blank_value(0)
  tests/test_planfile_queue.py:
    e: _ok,_ticket_args,TestPlanfileQueue,TestPlanfileQueueLlm,TestPlanfileQueueLoop
    TestPlanfileQueue: test_shell_ticket_runs_lifecycle_commands(0),test_ticket_claim_failure_returns_claim_failed(0),test_human_ticket_returns_waiting_input(0),test_shell_failure_marks_ticket_failed(0),test_api_ticket_runs_lifecycle_commands(0),test_api_failure_marks_ticket_failed(0),test_idle_when_planfile_returns_no_ticket(0),test_planfile_error_propagates(0),test_dry_run_returns_command_without_executing(0),test_unsupported_executor_kind(0),test_shell_ticket_without_command_auto_completes(0),test_api_ticket_without_endpoint_requests_input(0),test_interactive_human_ticket_completes_with_answer(0),test_interactive_human_ticket_cancellation_leaves_ticket(0),test_interactive_with_dry_run_does_not_prompt(0)
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
    e: _ok,TestScanPytestCollect,TestScanTodoMarkers,TestScanMissingGates,TestScanMissingTools,TestScanGitignoreDrift,TestRunScan,TestScanSemcodArtifacts
    TestScanPytestCollect: test_returns_empty_when_no_tests_and_no_pyproject(0),test_empty_on_clean_collect(0),test_parses_per_file_collection_errors(0),test_falls_back_to_umbrella_import_ticket(0),test_collection_timeout_emits_diagnostic_ticket(0),test_timeout_value_is_reflected_in_ticket(0),test_pytest_not_installed_stays_silent(0)
    TestScanTodoMarkers: test_filters_files_below_threshold(0),test_groups_markers_per_file(0),test_respects_koruignore_file_glob(0),test_respects_koruignore_directory_prefix(0)
    TestScanMissingGates: test_no_suggestions_when_tool_missing(0),test_skips_when_config_already_present(0)
    TestScanMissingTools: test_no_pyproject_returns_empty(0),test_skips_tools_not_in_registry(0)
    TestScanGitignoreDrift: test_no_gitignore_returns_empty(0),test_present_entry_skips_suggestion(0),test_missing_entry_suggests(0)
    TestRunScan: test_dry_run_returns_suggestions_no_apply(0),test_apply_creates_tickets_and_skips_duplicates(0),test_apply_create_failure_is_skipped(0),test_apply_deduplicates_planfile_source_tool_payload(0),test_limit_caps_suggestions(0),test_priority_ordering_critical_first(0)
    TestScanSemcodArtifacts: test_jscpd_report_emits_when_duplicates(0),test_code2llm_analysis_emits_when_god_rows(0),test_code2llm_analysis_emits_dup_ticket(0),test_code2llm_analysis_emits_cc_ticket(0),test_code2llm_analysis_emits_refactor_items(0),test_testql_export_emits_when_many_failures(0),test_redup_filtered_emits_when_many_groups(0)
    _ok(stdout;returncode;stderr)
  tests/test_serve.py:
    e: _minimal_planfile_project,_free_port,_start,_get,_post_json,test_start_serve_background_shutdown,TestServe,TestServeAutoPort
    TestServe: setUp(0),tearDown(0),test_health_endpoint(0),test_dashboard_html_served_on_root(0),test_api_context_returns_brief(0),test_api_handoff_returns_markdown(0),test_api_topology_returns_components_and_pipelines(0),test_api_topology_post_persists_toggle(0),test_api_topology_post_rejects_empty_update(0),test_unknown_path_returns_404(0)
    TestServeAutoPort: test_auto_port_skips_busy_port(0),test_without_auto_port_busy_raises(0)
    _minimal_planfile_project()
    _free_port()
    _start(project;port)
    _get(port;path)
    _post_json(port;path;payload)
    test_start_serve_background_shutdown()
  tests/test_stdio_autonomous_jsonl.py:
    e: _parse_jsonl,test_jsonl_session_emits_versioned_envelope,test_default_stdio_format_from_env_jsonl,test_stdio_event_schema_version_constant
    _parse_jsonl(text)
    test_jsonl_session_emits_versioned_envelope(tmp_path;monkeypatch)
    test_default_stdio_format_from_env_jsonl(monkeypatch)
    test_stdio_event_schema_version_constant()
  tests/test_tasks.py:
    e: TestNaturalLanguageTask
    TestNaturalLanguageTask: test_creates_planfile_ticket_from_sentence(0),test_increments_next_id(0),test_rejects_empty_text(0),test_scaffold_overrides_ticket_shape(0)
  tests/test_tools.py:
    e: test_load_registry_from_explicit_path,test_detect_tools_marks_available_via_command,test_detect_tools_marks_available_via_marker,test_infer_adapter_kind_defaults,test_build_tool_task_scaffold_contains_expected_fields,test_build_tool_task_scaffold_plugin_bridge_shape
    test_load_registry_from_explicit_path(tmp_path)
    test_detect_tools_marks_available_via_command(tmp_path)
    test_detect_tools_marks_available_via_marker(tmp_path)
    test_infer_adapter_kind_defaults()
    test_build_tool_task_scaffold_contains_expected_fields()
    test_build_tool_task_scaffold_plugin_bridge_shape()
  tests/test_topology.py:
    e: TestTopology
    TestTopology: setUp(0),tearDown(0),test_load_defaults_without_file(0),test_toggle_and_persist(0),test_enabled_components_for_pipeline_respects_component_flags(0)
  tests/test_watch.py:
    e: FakeWebSocket,TestWatch
    FakeWebSocket: __init__(1),__aenter__(0),__aexit__(0),recv(0)
    TestWatch: test_format_queue_event_for_execution_change(0),test_format_management_event(0),test_watch_planfile_events_prints_compact_lines(0)
```

## Call Graph

*404 nodes · 500 edges · 52 modules · CC̄=4.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.planfile-export-prompt)* | 0 | 225 | 0 | **225** |
| `_run_cycle` *(in src.koru.autonomous)* | 53 ⚠ | 1 | 102 | **103** |
| `_build_handler` *(in src.koru.serve)* | 1 | 1 | 86 | **87** |
| `_build_parser` *(in src.koru.autonomous)* | 1 | 1 | 53 | **54** |
| `detect_agent_options` *(in src.koru.agents)* | 16 ⚠ | 2 | 50 | **52** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 5 | 45 | **50** |
| `_build_parser` *(in src.koru.autopilot.cli_command)* | 1 | 1 | 48 | **49** |
| `run_next_planfile_task` *(in src.koru.queue.runner)* | 32 ⚠ | 2 | 43 | **45** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.18s
# nodes: 404 | edges: 500 | modules: 52
# CC̄=4.7

HUBS[20]:
  scripts.planfile-export-prompt.print
    CC=0  in:225  out:0  total:225
  src.koru.autonomous._run_cycle
    CC=53  in:1  out:102  total:103
  src.koru.serve._build_handler
    CC=1  in:1  out:86  total:87
  src.koru.autonomous._build_parser
    CC=1  in:1  out:53  total:54
  src.koru.agents.detect_agent_options
    CC=16  in:2  out:50  total:52
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:45  total:50
  src.koru.autopilot.cli_command._build_parser
    CC=1  in:1  out:48  total:49
  src.koru.queue.runner.run_next_planfile_task
    CC=32  in:2  out:43  total:45
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.autonomous._action_up
    CC=33  in:1  out:44  total:45
  src.koru.tasks.create_nl_task
    CC=16  in:2  out:39  total:41
  src.koru.scan._scan_code2llm_analysis
    CC=15  in:1  out:39  total:40
  src.koru.local_service._build_handler
    CC=1  in:1  out:39  total:40
  src.koru.autopilot.host_setup._print_text_report
    CC=15  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koru.cli._build_parser
    CC=1  in:3  out:32  total:35
  src.koru.cli._topology_main
    CC=17  in:0  out:33  total:33
  src.koru.events.emit_management_event
    CC=8  in:26  out:7  total:33
  scripts.planfile-sync-todo.do_from_todo
    CC=19  in:1  out:31  total:32
  src.koru.autonomous._run_idle_diagnostics
    CC=17  in:1  out:30  total:31

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [32 funcs]
    activate  CC=3  out:7
    app  CC=1  out:1
    bridge  CC=2  out:3
    clearTimeout  CC=2  out:0
    commands  CC=3  out:1
    connect  CC=3  out:10
    delay  CC=2  out:3
    detectIde  CC=4  out:2
    directPasted  CC=2  out:1
    disconnect  CC=4  out:2
  plugins.koru-autopilot-vscode.src.socketPath  [5 funcs]
    defaultSocketPathFromEnv  CC=9  out:6
    explicit  CC=2  out:1
    inst  CC=2  out:1
    name  CC=2  out:1
    slugInstance  CC=2  out:2
  scripts.planfile-export-prompt  [1 funcs]
    print  CC=0  out:0
  scripts.planfile-sync-todo  [7 funcs]
    build_auto_section  CC=1  out:2
    do_from_planfile  CC=14  out:20
    do_from_todo  CC=19  out:31
    load_tickets  CC=6  out:5
    main  CC=2  out:9
    replace_auto_section  CC=4  out:6
    run_planfile  CC=2  out:4
  services.healing-webhook.app  [22 funcs]
    _build_planfile_command  CC=2  out:1
    _enrich_ticket_with_vallm  CC=8  out:16
    _execute_planfile_create  CC=8  out:12
    _extract_ticket_id_from_stdout  CC=6  out:4
    _parse_redup_summary  CC=9  out:16
    _rate_limit_ok  CC=3  out:3
    _record_action  CC=1  out:7
    _resolve_affected_files  CC=11  out:24
    _resolve_strategy  CC=3  out:1
    _run_docker  CC=1  out:3
  services.healing-webhook.ticket_builder  [5 funcs]
    _default_acceptance  CC=2  out:1
    _format_paths  CC=2  out:1
    _infer_paths  CC=7  out:1
    _reproduction_for  CC=5  out:5
    build_ticket_payload  CC=11  out:25
  src.koru.agents  [11 funcs]
    _marker  CC=1  out:2
    _which  CC=1  out:1
    agent_lane_environment  CC=1  out:2
    detect_agent_environment  CC=6  out:7
    detect_agent_options  CC=16  out:50
    detect_project_environment  CC=4  out:22
    format_agent_lane_exports  CC=2  out:6
    launch_agent  CC=4  out:8
    normalize_agent_lane_id  CC=6  out:8
    save_agent_prompt  CC=1  out:3
  src.koru.autonomous  [17 funcs]
    _action_up  CC=33  out:44
    _apply_agent_lane_environ  CC=3  out:3
    _build_parser  CC=1  out:53
    _create_diagnostic_ticket  CC=2  out:6
    _effective_flags  CC=3  out:0
    _ensure_init  CC=4  out:3
    _env_apply_autoloop_defaults  CC=6  out:26
    _env_default_bool  CC=2  out:3
    _is_topology_enabled  CC=4  out:2
    _queue_loop_waiting_ticket_label  CC=3  out:1
  src.koru.autonomous_wup  [4 funcs]
    _start_wup_watch  CC=9  out:12
    _wup_stdio_info  CC=2  out:1
    _wup_topology_gate  CC=4  out:2
    _wup_watch_command  CC=3  out:8
  src.koru.autopilot  [2 funcs]
    _autopilot_socket_basename  CC=6  out:7
    default_socket_path  CC=5  out:14
  src.koru.autopilot.audit  [1 funcs]
    default_log_path  CC=2  out:3
  src.koru.autopilot.cli_command  [31 funcs]
    _action_daemon  CC=9  out:15
    _action_doctor  CC=4  out:6
    _action_drive  CC=8  out:17
    _action_handoff  CC=9  out:18
    _action_ide_list  CC=5  out:4
    _action_install_plugin  CC=6  out:12
    _action_install_unit  CC=6  out:18
    _action_setup_host  CC=1  out:1
    _action_shutdown  CC=1  out:2
    _action_status  CC=1  out:2
  src.koru.autopilot.client  [2 funcs]
    __init__  CC=2  out:1
    request  CC=5  out:11
  src.koru.autopilot.config  [4 funcs]
    _merge_submit_keys  CC=7  out:5
    cached_config  CC=1  out:2
    default_config_path  CC=1  out:1
    load_config  CC=4  out:10
  src.koru.autopilot.daemon  [13 funcs]
    __init__  CC=7  out:8
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=5  out:19
    _drive_via_plugin  CC=2  out:9
    _handle_ack  CC=7  out:7
    _handle_hello  CC=5  out:12
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=6  out:11
  src.koru.autopilot.host_setup  [6 funcs]
    _human_followups  CC=14  out:10
    _package_manager_hint  CC=5  out:4
    _print_text_report  CC=15  out:38
    _try_apt_install  CC=5  out:11
    build_setup_host_report  CC=7  out:11
    run_host_setup  CC=6  out:8
  src.koru.autopilot.ide  [10 funcs]
    _active_window_pid_x11  CC=7  out:6
    _iter_proc_pids  CC=4  out:6
    _matches  CC=7  out:5
    _read_cmdline  CC=2  out:5
    _read_comm  CC=2  out:3
    detect_focused_ide_id  CC=7  out:5
    detect_running_ides  CC=11  out:7
    detect_running_ides_cached  CC=4  out:2
    focused_ide  CC=6  out:1
    pick_target  CC=6  out:1
  src.koru.autopilot.injector  [4 funcs]
    _candidate_backends  CC=5  out:10
    type_text  CC=8  out:11
    _forced_injector_backend  CC=2  out:3
    _submit_key_for  CC=1  out:2
  src.koru.autopilot.plugin_installer  [9 funcs]
    _configure_socket_path  CC=8  out:12
    _extension_is_installed  CC=4  out:5
    _ide_from_terminal_env  CC=4  out:4
    _resolve_ide_command  CC=3  out:2
    _settings_path_for_ide  CC=2  out:5
    _valid_ide  CC=3  out:2
    install_plugin_for_ide  CC=19  out:27
    resolve_extension_vsix  CC=6  out:15
    resolve_target_ide  CC=10  out:6
  src.koru.autopilot.protocol  [5 funcs]
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    chat_send  CC=1  out:1
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koru.autopilot.utils.client_helpers  [2 funcs]
    call_daemon_method  CC=4  out:7
    resolve_xdg_path  CC=2  out:3
  src.koru.bootstrap  [8 funcs]
    _detect_cycle  CC=10  out:13
    _validate_cross_task_dependencies  CC=10  out:13
    _validate_id  CC=4  out:6
    _validate_task  CC=4  out:17
    import_flat_pipeline  CC=9  out:12
    load_flat_pipeline  CC=9  out:12
    materialize_to_planfile  CC=6  out:16
    validate_flat_pipeline  CC=3  out:9
  src.koru.cli  [33 funcs]
    _agent_main  CC=19  out:27
    _bootstrap_main  CC=5  out:18
    _build_gate_parser  CC=1  out:11
    _build_gc_parser  CC=1  out:14
    _build_local_serve_parser  CC=1  out:4
    _build_parser  CC=1  out:32
    _build_queue_parser  CC=1  out:11
    _build_runtime_context_parser  CC=1  out:4
    _build_scan_parser  CC=1  out:9
    _build_serve_parser  CC=1  out:10
  src.koru.context  [26 funcs]
    _auto_promote_blocking_tickets  CC=4  out:5
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _build_ticket_args  CC=3  out:1
    _extract_error_from_stderr  CC=7  out:4
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=15  out:14
    _find_blocking_tickets  CC=6  out:8
  src.koru.doctor  [12 funcs]
    _check_ci_command  CC=5  out:6
    _check_koru_project_pipeline  CC=7  out:9
    _check_planfile_cli_version  CC=9  out:9
    _check_planfile_config  CC=4  out:7
    _check_planfile_sprints  CC=10  out:17
    _check_planfile_sprints_yaml  CC=6  out:8
    _check_policy_yaml  CC=11  out:13
    _check_pytest_collect  CC=8  out:6
    _check_runtime_dir  CC=6  out:6
    _planfile_version_argv  CC=3  out:4
  src.koru.dotenv_loader  [3 funcs]
    _parse_value  CC=5  out:7
    load_dotenv  CC=7  out:5
    parse_dotenv  CC=5  out:7
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.gate  [2 funcs]
    _resolve_actor  CC=4  out:1
    authorize_gate  CC=9  out:16
  src.koru.gc  [11 funcs]
    _apply_keep_last  CC=7  out:8
    _archive_tickets  CC=2  out:6
    _archive_tickets_before_delete  CC=5  out:3
    _delete_tickets  CC=6  out:6
    _load_tickets_from_sprint  CC=7  out:7
    _now_utc  CC=1  out:1
    _parse_ts  CC=3  out:2
    _planfile_env  CC=1  out:0
    _run_planfile  CC=6  out:9
    collect_gc_candidates  CC=9  out:21
  src.koru.init  [9 funcs]
    _ensure_gitignore_entry  CC=8  out:12
    _remove_agent_lane_artifacts  CC=5  out:3
    _resolve_init_agent_lane  CC=6  out:5
    _write_agent_lane_artifacts  CC=2  out:10
    _write_autopilot_host_setup_script  CC=1  out:5
    _write_policy_stub_if_absent  CC=3  out:6
    init_project  CC=7  out:21
    refresh_init_agent_lane  CC=3  out:10
    resolve_project_agent_lane  CC=1  out:2
  src.koru.local_service  [7 funcs]
    _build_handler  CC=1  out:39
    _env_int  CC=3  out:3
    _koru_version  CC=2  out:1
    build_local_service_server  CC=1  out:4
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:11
    start_local_service_background  CC=1  out:4
  src.koru.loop  [3 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
    run_closed_loop  CC=12  out:18
  src.koru.policy  [2 funcs]
    load_policy  CC=9  out:43
    policy_path  CC=1  out:1
  src.koru.project_pipeline  [5 funcs]
    build_project_pipeline_brief  CC=9  out:14
    default_koru_project_pipeline_text  CC=1  out:0
    load_koru_project_pipeline  CC=4  out:5
    project_pipeline_path  CC=1  out:1
    write_koru_project_pipeline_if_absent  CC=2  out:5
  src.koru.queue.human  [1 funcs]
    default_human_prompt  CC=5  out:12
  src.koru.queue.locking  [4 funcs]
    claim_lease_seconds_str  CC=2  out:6
    queue_lock_wanted  CC=1  out:3
    queue_runner_lock  CC=3  out:6
    ticket_claim_or_error  CC=4  out:4
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=12  out:8
  src.koru.queue.runner  [1 funcs]
    run_next_planfile_task  CC=32  out:43
  src.koru.queue.runners  [2 funcs]
    _planfile_env  CC=1  out:0
    run_process  CC=1  out:2
  src.koru.queue.ticket  [2 funcs]
    parse_next_ticket  CC=10  out:11
    planfile_command  CC=3  out:4
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
    planfile_dir  CC=1  out:1
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [16 funcs]
    _create_ticket  CC=5  out:3
    _existing_scan_titles  CC=3  out:18
    _is_koruignored  CC=10  out:6
    _load_koruignore_patterns  CC=8  out:9
    _scan_code2llm_analysis  CC=15  out:39
    _scan_jscpd_report  CC=11  out:14
    _scan_redup_filtered  CC=7  out:12
    _scan_testql_export  CC=5  out:7
    collect_suggestions  CC=3  out:13
    run_scan  CC=8  out:14
  src.koru.semcod_tools  [3 funcs]
    _config_present  CC=3  out:2
    _read_pyproject  CC=3  out:3
    detect_semcod_tools  CC=7  out:9
  src.koru.serve  [8 funcs]
    _build_handler  CC=1  out:86
    bind_serve_server  CC=8  out:7
    build_server  CC=1  out:2
    read_serve_endpoint  CC=4  out:5
    serve  CC=7  out:18
    serve_endpoint_path  CC=1  out:1
    start_serve_background  CC=4  out:13
    write_serve_endpoint_file  CC=1  out:5
  src.koru.stdio_events  [2 funcs]
    iso_ts  CC=1  out:4
    write_stdio_event  CC=2  out:4
  src.koru.tasks  [4 funcs]
    _read_config  CC=4  out:7
    _read_sprint  CC=4  out:11
    _write_yaml  CC=1  out:3
    create_nl_task  CC=16  out:39
  src.koru.tools  [8 funcs]
    _first_token  CC=2  out:1
    build_tool_task_scaffold  CC=16  out:21
    default_registry_path  CC=1  out:2
    detect_tools  CC=26  out:25
    find_tool_entry  CC=4  out:6
    infer_adapter_kind  CC=5  out:4
    load_tool_registry  CC=11  out:13
    resolve_registry_path  CC=4  out:7
  src.koru.topology  [13 funcs]
    _merge_components  CC=12  out:21
    _merge_pipelines  CC=9  out:10
    _read_yaml  CC=5  out:4
    _strip_to_persisted  CC=8  out:16
    _toggle  CC=2  out:11
    enabled_components_for_pipeline  CC=9  out:11
    is_component_enabled  CC=3  out:6
    is_pipeline_enabled  CC=3  out:6
    load_topology  CC=1  out:9
    save_topology  CC=1  out:6
  src.koru.utils.subprocess_runner  [2 funcs]
    get_python_cmd  CC=3  out:3
    resolve_planfile_subpath  CC=1  out:3
  src.koru.watch  [2 funcs]
    format_queue_event  CC=19  out:35
    watch_planfile_events  CC=7  out:7

EDGES:
  services.healing-webhook.app._enrich_ticket_with_vallm → services.healing-webhook.app._resolve_affected_files
  services.healing-webhook.app._enrich_ticket_with_vallm → services.healing-webhook.app._run_vallm_check
  services.healing-webhook.app._execute_planfile_create → services.healing-webhook.app._extract_ticket_id_from_stdout
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.app._enrich_ticket_with_vallm
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.app._build_planfile_command
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.app._execute_planfile_create
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.ticket_builder.build_ticket_payload
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
  services.healing-webhook.app._run_redup_check → services.healing-webhook.app._update_redup_metrics
  services.healing-webhook.app._run_redup_check → services.healing-webhook.app._parse_redup_summary
  services.healing-webhook.app.heal_redup_check → services.healing-webhook.app._run_redup_check
  services.healing-webhook.app.heal_redup_check → services.healing-webhook.app._record_action
  services.healing-webhook.app.alertmanager_webhook → services.healing-webhook.app._resolve_strategy
  services.healing-webhook.app.probe_failure → services.healing-webhook.app.create_planfile_ticket
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._format_paths
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._default_acceptance
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._reproduction_for
  src.koru.loop.discover_repositories → src.koru.loop._search_root_for_include
  src.koru.project_pipeline.write_koru_project_pipeline_if_absent → src.koru.project_pipeline.project_pipeline_path
  src.koru.project_pipeline.write_koru_project_pipeline_if_absent → src.koru.project_pipeline.default_koru_project_pipeline_text
  src.koru.project_pipeline.load_koru_project_pipeline → src.koru.project_pipeline.project_pipeline_path
  src.koru.project_pipeline.build_project_pipeline_brief → src.koru.project_pipeline.load_koru_project_pipeline
  src.koru.semcod_tools.detect_semcod_tools → src.koru.semcod_tools._read_pyproject
  src.koru.semcod_tools.detect_semcod_tools → src.koru.semcod_tools._config_present
  src.koru.run_log.RunLogWriter._emit → scripts.planfile-export-prompt.print
  src.koru.run_log.RunLogWriter.write_header → src.koru.run_log._iso
  src.koru.run_log.RunLogWriter.write_iteration → src.koru.run_log._iso
  src.koru.run_log.RunLogWriter.write_footer → src.koru.run_log._iso
  src.koru.run_log.open_run_log → src.koru.runtime.new_run_id
  src.koru.run_log.open_run_log → src.koru.runtime.runs_dir
  src.koru.run_log.open_run_log_eagerly → src.koru.runtime.ensure_runs_dir
  src.koru.run_log.open_run_log_eagerly → src.koru.run_log.open_run_log
  src.koru.dotenv_loader.parse_dotenv → src.koru.dotenv_loader._parse_value
  src.koru.dotenv_loader.load_dotenv → src.koru.dotenv_loader.parse_dotenv
  src.koru.queue.locking.queue_runner_lock → src.koru.queue.locking.queue_lock_wanted
  src.koru.queue.locking.ticket_claim_or_error → src.koru.queue.ticket.planfile_command
  src.koru.queue.locking.ticket_claim_or_error → src.koru.queue.locking.claim_lease_seconds_str
  src.koru.queue.human.default_human_prompt → scripts.planfile-export-prompt.print
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

Closed-loop automation across semcod/* repositories.
