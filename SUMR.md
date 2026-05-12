# koru

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `koru`
- **version**: `0.1.56`
- **python_requires**: `>=3.12`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.56;
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

## Call Graph

*348 nodes · 425 edges · 48 modules · CC̄=4.9*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.planfile-export-prompt)* | 0 | 223 | 0 | **223** |
| `_build_handler` *(in src.koru.serve)* | 1 | 1 | 86 | **87** |
| `detect_agent_options` *(in src.koru.agents)* | 16 ⚠ | 2 | 50 | **52** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 5 | 45 | **50** |
| `_build_parser` *(in src.koru.autopilot.cli_command)* | 1 | 1 | 48 | **49** |
| `load_policy` *(in src.koru.policy)* | 9 | 2 | 43 | **45** |
| `run_next_planfile_task` *(in src.koru.queue.runner)* | 26 ⚠ | 2 | 43 | **45** |
| `_validate_task` *(in src.koru.bootstrap)* | 18 ⚠ | 1 | 43 | **44** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.15s
# nodes: 348 | edges: 425 | modules: 48
# CC̄=4.9

HUBS[20]:
  scripts.planfile-export-prompt.print
    CC=0  in:223  out:0  total:223
  src.koru.serve._build_handler
    CC=1  in:1  out:86  total:87
  src.koru.agents.detect_agent_options
    CC=16  in:2  out:50  total:52
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:45  total:50
  src.koru.autopilot.cli_command._build_parser
    CC=1  in:1  out:48  total:49
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.queue.runner.run_next_planfile_task
    CC=26  in:2  out:43  total:45
  src.koru.bootstrap._validate_task
    CC=18  in:1  out:43  total:44
  services.healing-webhook.app.create_planfile_ticket
    CC=24  in:2  out:39  total:41
  src.koru.tasks.create_nl_task
    CC=16  in:1  out:39  total:40
  src.koru.autopilot.host_setup._print_text_report
    CC=15  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koru.cli._build_parser
    CC=1  in:3  out:32  total:35
  src.koru.events.emit_management_event
    CC=8  in:26  out:7  total:33
  src.koru.cli._topology_main
    CC=17  in:0  out:33  total:33
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.autopilot.cli_command._action_doctor
    CC=21  in:0  out:29  total:29
  src.koru.autonomous._action_up
    CC=28  in:1  out:28  total:29
  src.koru.cli._queue_run_main
    CC=26  in:1  out:28  total:29
  src.koru.autopilot.plugin_installer.install_plugin_for_ide
    CC=19  in:1  out:27  total:28

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [28 funcs]
    activate  CC=3  out:7
    app  CC=1  out:1
    bridge  CC=2  out:3
    clearTimeout  CC=2  out:0
    commands  CC=3  out:1
    connect  CC=1  out:9
    delay  CC=2  out:3
    detectIde  CC=4  out:2
    disconnect  CC=4  out:2
    dispatch  CC=6  out:2
  plugins.koru-autopilot-vscode.src.socketPath  [5 funcs]
    defaultSocketPathFromEnv  CC=9  out:6
    explicit  CC=2  out:1
    inst  CC=2  out:1
    name  CC=2  out:1
    slugInstance  CC=2  out:2
  scripts.planfile-export-prompt  [1 funcs]
    print  CC=0  out:0
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
  src.koru.autonomous  [9 funcs]
    _action_up  CC=28  out:28
    _apply_agent_lane_environ  CC=3  out:3
    _build_parser  CC=1  out:21
    _effective_flags  CC=3  out:0
    _ensure_init  CC=4  out:3
    _resolve_autopilot_ide  CC=3  out:3
    _run_cycle  CC=8  out:19
    _start_or_reuse_daemon  CC=2  out:12
    autonomous_main  CC=5  out:3
  src.koru.autopilot  [2 funcs]
    _autopilot_socket_basename  CC=6  out:7
    default_socket_path  CC=5  out:14
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.autopilot.cli_command  [25 funcs]
    _action_daemon  CC=9  out:15
    _action_doctor  CC=21  out:29
    _action_drive  CC=8  out:17
    _action_handoff  CC=9  out:18
    _action_ide_list  CC=5  out:4
    _action_install_plugin  CC=11  out:23
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
  src.koru.bootstrap  [7 funcs]
    _detect_cycle  CC=10  out:13
    _validate_cross_task_dependencies  CC=10  out:13
    _validate_task  CC=18  out:43
    import_flat_pipeline  CC=9  out:12
    load_flat_pipeline  CC=9  out:12
    materialize_to_planfile  CC=6  out:16
    validate_flat_pipeline  CC=3  out:9
  src.koru.cli  [31 funcs]
    _agent_main  CC=19  out:27
    _bootstrap_main  CC=5  out:18
    _build_gate_parser  CC=1  out:11
    _build_gc_parser  CC=1  out:14
    _build_parser  CC=1  out:32
    _build_queue_parser  CC=1  out:11
    _build_runtime_context_parser  CC=1  out:4
    _build_scan_parser  CC=1  out:9
    _build_serve_parser  CC=1  out:10
    _build_tools_parser  CC=1  out:7
  src.koru.context  [16 funcs]
    _auto_promote_blocking_tickets  CC=25  out:24
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=36  out:23
    _is_fixture_ticket  CC=4  out:6
    _load_project_dotenv  CC=3  out:2
    _planfile_command_base  CC=3  out:3
  src.koru.doctor  [10 funcs]
    _check_ci_command  CC=5  out:6
    _check_koru_project_pipeline  CC=7  out:9
    _check_planfile_config  CC=4  out:7
    _check_planfile_sprints  CC=10  out:17
    _check_planfile_sprints_yaml  CC=6  out:8
    _check_policy_yaml  CC=11  out:13
    _check_pytest_collect  CC=8  out:6
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
    run_next_planfile_task  CC=26  out:43
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
    _existing_scan_titles  CC=11  out:13
    _is_koruignored  CC=10  out:6
    _load_koruignore_patterns  CC=8  out:9
    _scan_code2llm_analysis  CC=12  out:9
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
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._format_paths
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._default_acceptance
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._reproduction_for
  src.koru.runtime.planfile_dir → src.koru.utils.subprocess_runner.resolve_planfile_subpath
  src.koru.runtime.runtime_dir → src.koru.runtime.planfile_dir
  src.koru.runtime.runs_dir → src.koru.runtime.runtime_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runs_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runtime_dir
  src.koru.watch.watch_planfile_events → plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect
  src.koru.watch.watch_planfile_events → src.koru.watch.format_queue_event
  src.koru.gate.authorize_gate → src.koru.gate._resolve_actor
  src.koru.bootstrap._validate_cross_task_dependencies → src.koru.bootstrap._detect_cycle
  src.koru.bootstrap.validate_flat_pipeline → src.koru.bootstrap._validate_task
  src.koru.bootstrap.validate_flat_pipeline → src.koru.bootstrap._validate_cross_task_dependencies
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.load_flat_pipeline
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.validate_flat_pipeline
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.materialize_to_planfile
  src.koru.cli._tools_main → src.koru.tools.load_tool_registry
  src.koru.cli._tools_main → src.koru.tools.detect_tools
  src.koru.cli._tools_main → src.koru.events.emit_management_event
  src.koru.cli._tools_main → scripts.planfile-export-prompt.print
  src.koru.cli._tools_main → src.koru.cli._build_tools_parser
  src.koru.cli._scan_main → src.koru.scan.run_scan
  src.koru.cli._scan_main → src.koru.events.emit_management_event
  src.koru.cli._scan_main → scripts.planfile-export-prompt.print
  src.koru.cli._scan_main → src.koru.cli._build_scan_parser
  src.koru.cli._gate_main → scripts.planfile-export-prompt.print
  src.koru.cli._gate_main → src.koru.events.emit_management_event
  src.koru.cli._gate_main → src.koru.gate.authorize_gate
  src.koru.cli._gate_main → src.koru.cli._build_gate_parser
  src.koru.cli._gc_main → src.koru.gc.run_gc
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.15s
# nodes: 348 | edges: 425 | modules: 48
# CC̄=4.9

HUBS[20]:
  scripts.planfile-export-prompt.print
    CC=0  in:223  out:0  total:223
  src.koru.serve._build_handler
    CC=1  in:1  out:86  total:87
  src.koru.agents.detect_agent_options
    CC=16  in:2  out:50  total:52
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:45  total:50
  src.koru.autopilot.cli_command._build_parser
    CC=1  in:1  out:48  total:49
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.queue.runner.run_next_planfile_task
    CC=26  in:2  out:43  total:45
  src.koru.bootstrap._validate_task
    CC=18  in:1  out:43  total:44
  services.healing-webhook.app.create_planfile_ticket
    CC=24  in:2  out:39  total:41
  src.koru.tasks.create_nl_task
    CC=16  in:1  out:39  total:40
  src.koru.autopilot.host_setup._print_text_report
    CC=15  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koru.cli._build_parser
    CC=1  in:3  out:32  total:35
  src.koru.events.emit_management_event
    CC=8  in:26  out:7  total:33
  src.koru.cli._topology_main
    CC=17  in:0  out:33  total:33
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.autopilot.cli_command._action_doctor
    CC=21  in:0  out:29  total:29
  src.koru.autonomous._action_up
    CC=28  in:1  out:28  total:29
  src.koru.cli._queue_run_main
    CC=26  in:1  out:28  total:29
  src.koru.autopilot.plugin_installer.install_plugin_for_ide
    CC=19  in:1  out:27  total:28

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [28 funcs]
    activate  CC=3  out:7
    app  CC=1  out:1
    bridge  CC=2  out:3
    clearTimeout  CC=2  out:0
    commands  CC=3  out:1
    connect  CC=1  out:9
    delay  CC=2  out:3
    detectIde  CC=4  out:2
    disconnect  CC=4  out:2
    dispatch  CC=6  out:2
  plugins.koru-autopilot-vscode.src.socketPath  [5 funcs]
    defaultSocketPathFromEnv  CC=9  out:6
    explicit  CC=2  out:1
    inst  CC=2  out:1
    name  CC=2  out:1
    slugInstance  CC=2  out:2
  scripts.planfile-export-prompt  [1 funcs]
    print  CC=0  out:0
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
  src.koru.autonomous  [9 funcs]
    _action_up  CC=28  out:28
    _apply_agent_lane_environ  CC=3  out:3
    _build_parser  CC=1  out:21
    _effective_flags  CC=3  out:0
    _ensure_init  CC=4  out:3
    _resolve_autopilot_ide  CC=3  out:3
    _run_cycle  CC=8  out:19
    _start_or_reuse_daemon  CC=2  out:12
    autonomous_main  CC=5  out:3
  src.koru.autopilot  [2 funcs]
    _autopilot_socket_basename  CC=6  out:7
    default_socket_path  CC=5  out:14
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.autopilot.cli_command  [25 funcs]
    _action_daemon  CC=9  out:15
    _action_doctor  CC=21  out:29
    _action_drive  CC=8  out:17
    _action_handoff  CC=9  out:18
    _action_ide_list  CC=5  out:4
    _action_install_plugin  CC=11  out:23
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
  src.koru.bootstrap  [7 funcs]
    _detect_cycle  CC=10  out:13
    _validate_cross_task_dependencies  CC=10  out:13
    _validate_task  CC=18  out:43
    import_flat_pipeline  CC=9  out:12
    load_flat_pipeline  CC=9  out:12
    materialize_to_planfile  CC=6  out:16
    validate_flat_pipeline  CC=3  out:9
  src.koru.cli  [31 funcs]
    _agent_main  CC=19  out:27
    _bootstrap_main  CC=5  out:18
    _build_gate_parser  CC=1  out:11
    _build_gc_parser  CC=1  out:14
    _build_parser  CC=1  out:32
    _build_queue_parser  CC=1  out:11
    _build_runtime_context_parser  CC=1  out:4
    _build_scan_parser  CC=1  out:9
    _build_serve_parser  CC=1  out:10
    _build_tools_parser  CC=1  out:7
  src.koru.context  [16 funcs]
    _auto_promote_blocking_tickets  CC=25  out:24
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=36  out:23
    _is_fixture_ticket  CC=4  out:6
    _load_project_dotenv  CC=3  out:2
    _planfile_command_base  CC=3  out:3
  src.koru.doctor  [10 funcs]
    _check_ci_command  CC=5  out:6
    _check_koru_project_pipeline  CC=7  out:9
    _check_planfile_config  CC=4  out:7
    _check_planfile_sprints  CC=10  out:17
    _check_planfile_sprints_yaml  CC=6  out:8
    _check_policy_yaml  CC=11  out:13
    _check_pytest_collect  CC=8  out:6
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
    run_next_planfile_task  CC=26  out:43
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
    _existing_scan_titles  CC=11  out:13
    _is_koruignored  CC=10  out:6
    _load_koruignore_patterns  CC=8  out:9
    _scan_code2llm_analysis  CC=12  out:9
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
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._format_paths
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._default_acceptance
  services.healing-webhook.ticket_builder.build_ticket_payload → services.healing-webhook.ticket_builder._reproduction_for
  src.koru.runtime.planfile_dir → src.koru.utils.subprocess_runner.resolve_planfile_subpath
  src.koru.runtime.runtime_dir → src.koru.runtime.planfile_dir
  src.koru.runtime.runs_dir → src.koru.runtime.runtime_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runs_dir
  src.koru.runtime.ensure_runs_dir → src.koru.runtime.runtime_dir
  src.koru.watch.watch_planfile_events → plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.connect
  src.koru.watch.watch_planfile_events → src.koru.watch.format_queue_event
  src.koru.gate.authorize_gate → src.koru.gate._resolve_actor
  src.koru.bootstrap._validate_cross_task_dependencies → src.koru.bootstrap._detect_cycle
  src.koru.bootstrap.validate_flat_pipeline → src.koru.bootstrap._validate_task
  src.koru.bootstrap.validate_flat_pipeline → src.koru.bootstrap._validate_cross_task_dependencies
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.load_flat_pipeline
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.validate_flat_pipeline
  src.koru.bootstrap.import_flat_pipeline → src.koru.bootstrap.materialize_to_planfile
  src.koru.cli._tools_main → src.koru.tools.load_tool_registry
  src.koru.cli._tools_main → src.koru.tools.detect_tools
  src.koru.cli._tools_main → src.koru.events.emit_management_event
  src.koru.cli._tools_main → scripts.planfile-export-prompt.print
  src.koru.cli._tools_main → src.koru.cli._build_tools_parser
  src.koru.cli._scan_main → src.koru.scan.run_scan
  src.koru.cli._scan_main → src.koru.events.emit_management_event
  src.koru.cli._scan_main → scripts.planfile-export-prompt.print
  src.koru.cli._scan_main → src.koru.cli._build_scan_parser
  src.koru.cli._gate_main → scripts.planfile-export-prompt.print
  src.koru.cli._gate_main → src.koru.events.emit_management_event
  src.koru.cli._gate_main → src.koru.gate.authorize_gate
  src.koru.cli._gate_main → src.koru.cli._build_gate_parser
  src.koru.cli._gc_main → src.koru.gc.run_gc
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 103f 19469L | python:55,shell:28,yaml:9,yml:2,json:2,typescript:2,toml:1,txt:1 | 2026-05-12
# generated in 0.02s
# CC̄=4.9 | critical:24/493 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    create_planfile_ticket CC=24 (limit:15)
  🟡 CC    _run_redup_check CC=15 (limit:15)
  🟡 CC    format_queue_event CC=19 (limit:15)
  🟡 CC    _validate_task CC=18 (limit:15)
  🟡 CC    _gc_main CC=18 (limit:15)
  🟡 CC    _agent_main CC=19 (limit:15)
  🟡 CC    _render_topology_text CC=15 (limit:15)
  🟡 CC    _topology_main CC=17 (limit:15)
  🟡 CC    _queue_run_main CC=26 (limit:15)
  🟡 CC    find_candidates CC=15 (limit:15)
  🟡 CC    detect_tools CC=26 (limit:15)
  🟡 CC    build_tool_task_scaffold CC=16 (limit:15)
  🟡 CC    _fetch_ticket_data CC=36 (limit:15)
  🟡 CC    _auto_promote_blocking_tickets CC=25 (limit:15)
  🟡 CC    _build_shared_rules CC=15 (limit:15)
  🟡 CC    policy_violations CC=22 (limit:15)
  🟡 CC    detect_agent_options CC=16 (limit:15)
  🟡 CC    create_nl_task CC=16 (limit:15)
  🟡 CC    run_llm_request CC=23 (limit:15)
  🟡 CC    run_next_planfile_task CC=26 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[160]:
  [1] Src [heal_rebuild_restore]: heal_rebuild_restore → _run_docker
      PURITY: 100% pure
  [2] Src [heal_annotate]: heal_annotate → _record_action
      PURITY: 100% pure
  [3] Src [_run_vallm_validate]: _run_vallm_validate
      PURITY: 100% pure
  [4] Src [heal_vallm_validate]: heal_vallm_validate → _resolve_affected_files → _infer_paths
      PURITY: 100% pure
  [5] Src [heal_redup_check]: heal_redup_check → _run_redup_check
      PURITY: 100% pure

LAYERS:
  services/                       CC̄=5.6    ←in:0  →out:0
  │ !! app                        673L  0C   21m  CC=24     ←0
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │
  src/                            CC̄=5.3    ←in:0  →out:0
  │ !! context                   1081L  0C   32m  CC=36     ←4
  │ !! serve                     1008L  1C    8m  CC=8      ←1
  │ !! cli_command                781L  0C   25m  CC=21     ←0
  │ !! scan                       708L  2C   18m  CC=13     ←2
  │ !! daemon                     517L  2C   24m  CC=14     ←0
  │ !! init                       500L  1C   10m  CC=13     ←2
  │ doctor                     454L  2C   17m  CC=11     ←1
  │ !! bootstrap                  413L  2C   12m  CC=18     ←2
  │ topology                   407L  1C   15m  CC=12     ←2
  │ !! autonomous                 383L  0C    9m  CC=28     ←0
  │ gc                         374L  2C   12m  CC=11     ←1
  │ !! queue_clean                355L  2C   10m  CC=15     ←1
  │ !! agents                     347L  1C   12m  CC=16     ←3
  │ !! plugin_installer           309L  1C   12m  CC=19     ←1
  │ injector                   293L  4C   15m  CC=8      ←0
  │ ide                        262L  1C   13m  CC=11     ←4
  │ !! tools                      248L  0C    9m  CC=26     ←1
  │ !! policy                     241L  1C    4m  CC=22     ←2
  │ !! runner                     225L  0C    1m  CC=26     ←2
  │ !! runners                    210L  0C    5m  CC=23     ←0
  │ !! host_setup                 210L  0C    6m  CC=15     ←1
  │ gate                       204L  1C    5m  CC=12     ←1
  │ protocol                   200L  2C   11m  CC=12     ←2
  │ !! tasks                      165L  1C    5m  CC=16     ←1
  │ audit                      155L  2C    6m  CC=7      ←1
  │ ticket                     139L  0C    6m  CC=10     ←2
  │ loop                       131L  3C    4m  CC=12     ←1
  │ semcod_tools               129L  1C    4m  CC=7      ←3
  │ project_pipeline           126L  0C    5m  CC=9      ←3
  │ run_log                    124L  1C    7m  CC=4      ←1
  │ config                     122L  1C    6m  CC=7      ←1
  │ loop                       107L  0C    1m  CC=12     ←2
  │ runtime                    104L  0C    5m  CC=2      ←5
  │ dotenv_loader              104L  0C    3m  CC=7      ←0
  │ client                      92L  1C    7m  CC=5      ←0
  │ events                      90L  0C    2m  CC=8      ←2
  │ locking                     87L  0C    4m  CC=4      ←1
  │ !! watch                       83L  0C    3m  CC=19     ←1
  │ types                       80L  5C    1m  CC=1      ←0
  │ __init__                    69L  0C    0m  CC=0.0    ←0
  │ __init__                    67L  0C    2m  CC=6      ←4
  │ __init__                    55L  0C    2m  CC=4      ←0
  │ client_helpers              53L  0C    2m  CC=4      ←2
  │ subprocess_runner           38L  0C    3m  CC=3      ←4
  │ planfile_queue              37L  0C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    0m  CC=0.0    ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ !! cli                          0L  0C   38m  CC=26     ←0
  │ commands                     0L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=2.7    ←in:0  →out:0
  │ extension.ts               248L  2C   32m  CC=12     ←1
  │ package.json                71L  0C    0m  CC=0.0    ←0
  │ socketPath.ts               27L  0C    9m  CC=9      ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=0.5    ←in:222  →out:0
  │ !! koru-autoloop.sh           562L  0C   14m  CC=0.0    ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←13
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1319L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               758L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  511L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                91L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              90L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  70L  0C    0m  CC=0.0    ←0
  │ project.sh                  54L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │
  docs/                           CC̄=0.0    ←in:0  →out:0
  │ ai-tool-registry-2026.yaml   290L  0C    0m  CC=0.0    ←0
  │ install.sh                  88L  0C    0m  CC=0.0    ←0
  │ install.sh                  87L  0C    0m  CC=0.0    ←0
  │ install.sh                  80L  0C    0m  CC=0.0    ←0
  │ install.sh                  60L  0C    0m  CC=0.0    ←0
  │ install.sh                  55L  0C    0m  CC=0.0    ←0
  │ install.sh                  55L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  41L  0C    0m  CC=0.0    ←0
  │ install.sh                  41L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │
  redeploy/                       CC̄=0.0    ←in:0  →out:0
  │ manifest.yaml              125L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=0.0    ←in:0  →out:0
  │ bootstrap.planfile.yaml    425L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    20L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     src/koru/cli.py                           0L
     src/koru/cli/commands.py                  0L

COUPLING:
                                                      src.koru                        scripts  plugins.koru-autopilot-vscode
                       src.koru                             ──                            222                              1  !! fan-out
                        scripts                           ←222                             ──                                 hub
  plugins.koru-autopilot-vscode                             ←1                                                            ──
  CYCLES: none
  HUB: scripts/ (fan-in=222)
  SMELL: src.koru/ fan-out=223 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 4 groups | 58f 14998L | 2026-05-12

SUMMARY:
  files_scanned: 58
  total_lines:   14998
  dup_groups:    4
  dup_fragments: 8
  saved_lines:   26
  scan_ms:       4558

HOTSPOTS[4] (files with most duplication):
  src/koru/serve.py  dup=20L  groups=2  frags=3  (0.1%)
  src/koru/topology.py  dup=12L  groups=1  frags=2  (0.1%)
  src/koru/project_pipeline.py  dup=10L  groups=1  frags=1  (0.1%)
  src/koru/autopilot/cli_command.py  dup=10L  groups=1  frags=2  (0.1%)

DUPLICATES[4] (ranked by impact):
  [db3e3e3ad621b70e]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:87-96  (load_koru_project_pipeline)
      src/koru/serve.py:59-68  (read_serve_endpoint)
  [c7374d52504d8e71]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:346-351  (set_component_enabled)
      src/koru/topology.py:354-359  (set_pipeline_enabled)
  [a0375ffb77746a3f]   EXAC  _open_later  L=5 N=2 saved=5 sim=1.00
      src/koru/serve.py:943-947  (_open_later)
      src/koru/serve.py:993-997  (_open_later)
  [be027ff698a2786c]   STRU  _action_status  L=5 N=2 saved=5 sim=1.00
      src/koru/autopilot/cli_command.py:345-349  (_action_status)
      src/koru/autopilot/cli_command.py:352-356  (_action_shutdown)

REFACTOR[4] (ranked by priority):
  [1] ○ extract_function   → src/koru/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koru/serve.py
  [2] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [3] ○ extract_function   → src/koru/utils/_open_later.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/serve.py
  [4] ○ extract_function   → src/koru/autopilot/utils/_action_status.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/autopilot/cli_command.py

QUICK_WINS[2] (low risk, high savings — do first):
  [1] extract_function   saved=10L  → src/koru/utils/load_koru_project_pipeline.py
      FILES: project_pipeline.py, serve.py
  [2] extract_function   saved=6L  → src/koru/utils/set_component_enabled.py
      FILES: topology.py

EFFORT_ESTIMATE (total ≈ 0.9h):
  easy   load_koru_project_pipeline          saved=10L  ~20min
  easy   set_component_enabled               saved=6L  ~12min
  easy   _open_later                         saved=5L  ~10min
  easy   _action_status                      saved=5L  ~10min

METRICS-TARGET:
  dup_groups:  4 → 0
  saved_lines: 26 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 471 func | 49f | 2026-05-12
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           src/koru/autopilot/cli_command.py
      WHY: 781L, 0 classes, max CC=21
      EFFORT: ~4h  IMPACT: 16401

  [2] !! SPLIT           src/koru/serve.py
      WHY: 1008L, 1 classes, max CC=8
      EFFORT: ~4h  IMPACT: 8064

  [3] !  SPLIT-FUNC      create_planfile_ticket  CC=24  fan=27
      WHY: CC=24 exceeds 15
      EFFORT: ~1h  IMPACT: 648

  [4] !! SPLIT-FUNC      run_next_planfile_task  CC=26  fan=21
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 546

  [5] !! SPLIT-FUNC      _action_up  CC=28  fan=18
      WHY: CC=28 exceeds 15
      EFFORT: ~1h  IMPACT: 504

  [6] !  SPLIT-FUNC      run_llm_request  CC=23  fan=19
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 437

  [7] !! SPLIT-FUNC      _fetch_ticket_data  CC=36  fan=12
      WHY: CC=36 exceeds 15
      EFFORT: ~1h  IMPACT: 432

  [8] !  SPLIT-FUNC      _agent_main  CC=19  fan=18
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 342

  [9] !! SPLIT-FUNC      _queue_run_main  CC=26  fan=13
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 338

  [10] !  SPLIT-FUNC      create_nl_task  CC=16  fan=21
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 336


RISKS[3]:
  ⚠ Splitting planfile.yaml may break 0 import paths
  ⚠ Splitting src/koru/serve.py may break 8 import paths
  ⚠ Splitting src/koru/autopilot/cli_command.py may break 25 import paths

METRICS-TARGET:
  CC̄:          5.1 → ≤3.6
  max-CC:      36 → ≤18
  god-modules: 9 → 0
  high-CC(≥15): 24 → ≤12
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=5.1 → now CC̄=5.1
```

## Intent

Closed-loop automation across semcod/* repositories.
