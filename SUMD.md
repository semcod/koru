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
- **version**: `0.1.132`
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
  version: 0.1.132;
}

dependencies {
  runtime: pyyaml>=6.0;
  dev: "pytest>=8.0, pytest-xdist>=3.0, ruff>=0.11, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60";
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
  step-1: run cmd=pip install planfile wup testql regix redup vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun;
  step-2: run cmd=echo "✓ semcod toolchain installed. Optional interactive agent: pip install aider-chat";
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -v {{.CLI_ARGS}};
}

workflow[name="test:all"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -v -m "" {{.CLI_ARGS}};
}

workflow[name="test:docker"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}};
}

workflow[name="test:fast"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -q;
}

workflow[name="test:quick"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -q --maxfail=1 --no-header;
}

workflow[name="test:parallel"] {
  trigger: manual;
  step-1: run cmd=python3 -m pytest tests/ -q -n auto --maxfail=1;
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

workflow[name="koru:server"] {
  trigger: manual;
  step-1: run cmd=python3 -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open;
}

workflow[name="koru:mcp:bootstrap"] {
  trigger: manual;
  step-1: run cmd=python3 -m koru.cli init-ide --project . --ide all;
}

workflow[name="koru:operator:plugin-probe"] {
  trigger: manual;
  step-1: run cmd=python3 -m koru.cli autopilot status;
}

workflow[name="koru:operator:setup-host"] {
  trigger: manual;
  step-1: run cmd=python3 -m koru.cli autopilot setup-host;
}

workflow[name="koru:ide-os:calibrate"] {
  trigger: manual;
  step-1: run cmd=python3 -m koru.cli autopilot calibrate --ide "{{.IDE}}";
}

workflow[name="quality:regix"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
  regix gates
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:regix skipped (gate:regix disabled in topology)"
    exit 0
  fi
  regix gates
fi;
}

workflow[name="quality:regix:local"] {
  trigger: manual;
  step-1: run cmd=regix compare HEAD --local;
}

workflow[name="quality:wup"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:wup >/dev/null 2>&1; then
  wup status
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:wup skipped (gate:wup disabled in topology)"
    exit 0
  fi
  wup status
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

workflow[name="quality:redup:changed"] {
  trigger: manual;
  step-1: run cmd=bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-HEAD}"; OUT="${OUT:-.redup/wup-changed.json}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi';
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

workflow[name="quality:semcod:planfile"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-semcod-gates.sh;
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

workflow[name="scripts:soak:start"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-start.sh;
}

workflow[name="scripts:soak:status"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-status.sh;
}

workflow[name="scripts:soak:monitor"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .planfile/.koru
if ! pgrep -f "autonomous up.*--max-cycles 0" >/dev/null 2>&1; then
  echo "! no running soak process found; start with: task scripts:soak:start"
  exit 1
fi
pkill -f koru-soak-monitor.sh || true
nohup env PROJECT="$PWD" TICKET_ID="{{.TID | default "STARTER-009"}}" \
  POLL_SECONDS="{{.POLL_SECONDS | default "60"}}" \
  bash scripts/koru-soak-monitor.sh > .planfile/.koru/soak-monitor.log 2>&1 &
echo "✓ soak monitor started for {{.TID | default "STARTER-009"}}";
}

workflow[name="scripts:soak:report"] {
  trigger: manual;
  step-1: run cmd=test -f .planfile/.koru/soak-interim-report.md && cat .planfile/.koru/soak-interim-report.md || true
test -f .planfile/.koru/soak-final-report.md && cat .planfile/.koru/soak-final-report.md || true
test -f .planfile/.koru/soak-stop-report.md && cat .planfile/.koru/soak-stop-report.md || true;
}

workflow[name="scripts:soak:stop"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-stop.sh;
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
- `koru-wup-testql`
- `koru-dsl`
- `koru-api`

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
    desc: Install semcod toolchain used by koru (planfile, wup, testql, regix, redup, sumr/sumd, doql, redeploy, ...)
    cmds:
      - pip install planfile wup testql regix redup vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun
      - 'echo "✓ semcod toolchain installed. Optional interactive agent: pip install aider-chat"'

  # =====================================================================
  # Tests
  # =====================================================================

  test:
    desc: Run default koru tests (slow Docker/integration tests are deselected by pytest addopts)
    cmds:
      - python3 -m pytest tests/ -v {{.CLI_ARGS}}

  test:all:
    desc: Run every koru test, including slow Docker/integration tests
    cmds:
      - python3 -m pytest tests/ -v -m "" {{.CLI_ARGS}}

  test:docker:
    desc: Run Docker E2E tests only (slow; deselected by default addopts)
    cmds:
      - python3 -m pytest tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}}

  test:fast:
    desc: Run tests without verbose output
    cmds:
      - python3 -m pytest tests/ -q

  test:quick:
    desc: Fastest possible test run (fail fast, no header)
    cmds:
      - python3 -m pytest tests/ -q --maxfail=1 --no-header

  test:parallel:
    desc: Run tests in parallel (safe only for isolated subsets)
    cmds:
      - python3 -m pytest tests/ -q -n auto --maxfail=1

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
  # Koru operator helpers
  # =====================================================================

  koru:server:
    desc: Start the local koru dashboard/API for operator checks
    cmds:
      - python3 -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open
    vars:
      HOST: '{{.HOST | default "127.0.0.1"}}'
      PORT: '{{.PORT | default "8765"}}'
    interactive: true

  koru:mcp:bootstrap:
    desc: Provision koru MCP config for Cursor, VS Code, and Windsurf
    cmds:
      - python3 -m koru.cli init-ide --project . --ide all

  koru:operator:plugin-probe:
    desc: Check autopilot daemon/plugin status
    cmds:
      - python3 -m koru.cli autopilot status

  koru:operator:setup-host:
    desc: Probe host injector dependencies for autopilot
    cmds:
      - python3 -m koru.cli autopilot setup-host

  koru:ide-os:calibrate:
    desc: Calibrate OS injector chat coordinates for an IDE (IDE=vscode|cursor|windsurf|jetbrains|zed)
    cmds:
      - python3 -m koru.cli autopilot calibrate --ide "{{.IDE}}"
    vars:
      IDE: '{{.IDE | default "auto"}}'
    interactive: true

  # =====================================================================
  # Quality gates (LLM-free, proxies to underlying tools)
  # =====================================================================

  quality:regix:
    desc: Run regix gates locally (LLM-free regression metrics)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
          regix gates
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:regix skipped (gate:regix disabled in topology)"
            exit 0
          fi
          regix gates
        fi
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:regix:local:
    desc: Compare working tree against HEAD with regix
    cmds:
      - regix compare HEAD --local
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:wup:
    desc: Check WUP on-change watcher configuration
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:wup >/dev/null 2>&1; then
          wup status
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:wup skipped (gate:wup disabled in topology)"
            exit 0
          fi
          wup status
        fi
    preconditions:
      - sh: which wup
        msg: "wup not installed. Run: task install:tools"
      - sh: test -f wup.yaml
        msg: "wup.yaml missing. Run: task template:install:wup"

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

  quality:redup:changed:
    desc: 'Run incremental redup scan over files changed since BASE_REF (default: HEAD)'
    cmds:
      - bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-HEAD}"; OUT="${OUT:-.redup/wup-changed.json}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi'
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

  quality:semcod:planfile:
    desc: Run configured semcod/* gates and create/update deduplicated planfile tickets on failures
    cmds:
      - bash scripts/koru-semcod-gates.sh

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

  scripts:soak:start:
    desc: Start background koru autonomous soak (--max-cycles 0, logs to .planfile/.koru/soak.log)
    cmds:
      - bash scripts/koru-soak-start.sh

  scripts:soak:status:
    desc: Show current long-run autonomy soak status (PID, uptime, cycle, ticket, report)
    cmds:
      - bash scripts/koru-soak-status.sh

  scripts:soak:monitor:
    desc: Start or restart the background soak completion monitor for STARTER-009
    cmds:
      - |
        mkdir -p .planfile/.koru
        if ! pgrep -f "autonomous up.*--max-cycles 0" >/dev/null 2>&1; then
          echo "! no running soak process found; start with: task scripts:soak:start"
          exit 1
        fi
        pkill -f koru-soak-monitor.sh || true
        nohup env PROJECT="$PWD" TICKET_ID="{{.TID | default "STARTER-009"}}" \
          POLL_SECONDS="{{.POLL_SECONDS | default "60"}}" \
          bash scripts/koru-soak-monitor.sh > .planfile/.koru/soak-monitor.log 2>&1 &
        echo "✓ soak monitor started for {{.TID | default "STARTER-009"}}"

  scripts:soak:report:
    desc: Show interim/final soak reports when present
    cmds:
      - |
        test -f .planfile/.koru/soak-interim-report.md && cat .planfile/.koru/soak-interim-report.md || true
        test -f .planfile/.koru/soak-final-report.md && cat .planfile/.koru/soak-final-report.md || true
        test -f .planfile/.koru/soak-stop-report.md && cat .planfile/.koru/soak-stop-report.md || true

  scripts:soak:stop:
    desc: Stop the background soak run and monitor, write a stop report, optionally mark ticket done
    cmds:
      - |
        bash scripts/koru-soak-stop.sh
    vars:
      TID: '{{.TID | default "STARTER-009"}}'
      MARK_DONE: '{{.MARK_DONE | default "false"}}'
    env:
      TICKET_ID: '{{.TID | default "STARTER-009"}}'
      MARK_DONE: '{{.MARK_DONE | default "false"}}'

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
  version: 0.1.132
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
pytest-xdist>=3.0
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
# koru | 284f 52179L | python:209,shell:62,javascript:6,typescript:6,less:1 | 2026-05-19
# stats: 1453 func | 176 cls | 284 mod | CC̄=4.2 | critical:119 | cycles:0
# alerts[5]: CC run_next_planfile_task=43; CC _handle_autopilot_phase=29; CC run_llm_request=23; CC policy_violations=22; CC do_from_todo=19
# hotspots[5]: _action_up fan=31; _build_handler fan=29; run_next_planfile_task fan=25; do_from_todo fan=23; run_cycle fan=23
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[284]:
  .planfile/.koru/run-autonomous.sh,7
  .planfile/.koru/setup-autopilot-host.sh,14
  .planfile/.koru/shell-env.sh,6
  app.doql.less,676
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
  examples/ci/headless-autonomous-jsonl/e2e.sh,27
  examples/ci/headless-autonomous-jsonl/run-docker.sh,8
  examples/env/autopilot-ide-auto/e2e.sh,28
  examples/env/autopilot-ide-auto/run-docker.sh,8
  examples/env/autopilot-ide-cursor/e2e.sh,29
  examples/env/autopilot-ide-cursor/run-docker.sh,8
  examples/planfile/http-api-curl/e2e.sh,20
  examples/planfile/http-api-curl/run-docker.sh,8
  examples/planfile/queue-cli-dryrun/e2e.sh,16
  examples/planfile/queue-cli-dryrun/run-docker.sh,8
  examples/protocol/autopilot-socket-smoke/e2e.sh,27
  examples/protocol/autopilot-socket-smoke/run-docker.sh,8
  examples/run-e2e.sh,44
  examples/runtime/koru-serve-health/e2e.sh,22
  examples/runtime/koru-serve-health/run-docker.sh,8
  plugins/koru-autopilot-vscode/.planfile/.koru/run-autonomous.sh,7
  plugins/koru-autopilot-vscode/.planfile/.koru/setup-autopilot-host.sh,14
  plugins/koru-autopilot-vscode/.planfile/.koru/shell-env.sh,6
  plugins/koru-autopilot-vscode/out/dispatch-plan.js,19
  plugins/koru-autopilot-vscode/out/dispatch-plan.test.js,89
  plugins/koru-autopilot-vscode/out/extension.js,582
  plugins/koru-autopilot-vscode/out/probe-ladder.js,211
  plugins/koru-autopilot-vscode/out/probe-ladder.test.js,43
  plugins/koru-autopilot-vscode/out/socketPath.js,100
  plugins/koru-autopilot-vscode/src/dispatch-plan.test.ts,95
  plugins/koru-autopilot-vscode/src/dispatch-plan.ts,27
  plugins/koru-autopilot-vscode/src/extension.ts,591
  plugins/koru-autopilot-vscode/src/probe-ladder.test.ts,69
  plugins/koru-autopilot-vscode/src/probe-ladder.ts,252
  plugins/koru-autopilot-vscode/src/socketPath.ts,67
  project.sh,54
  scripts/_koru_autodiag_filter_tickets.py,56
  scripts/autopilot-ide-autodetect-smoke.sh,183
  scripts/koru-autoloop-reset-diag-markers.sh,97
  scripts/koru-autoloop.sh,577
  scripts/koru-gate-capture.py,315
  scripts/koru-queue-diagnose.sh,125
  scripts/koru-semcod-gates.sh,100
  scripts/koru-soak-monitor.sh,129
  scripts/koru-soak-start.sh,40
  scripts/koru-soak-status.sh,100
  scripts/koru-soak-stop.sh,124
  scripts/planfile-export-prompt.sh,82
  scripts/planfile-sync-todo.py,235
  services/healing-webhook/app.py,703
  services/healing-webhook/ticket_builder.py,224
  src/koru/__init__.py,70
  src/koru/__main__.py,9
  src/koru/activity_log.py,69
  src/koru/agent_backend_runtime.py,181
  src/koru/agent_backends.py,215
  src/koru/agent_cli_helpers.py,89
  src/koru/agents.py,371
  src/koru/api/__init__.py,10
  src/koru/autonomous.py,1667
  src/koru/autonomous_cycle.py,1047
  src/koru/autonomous_diagnostics.py,251
  src/koru/autonomous_env.py,27
  src/koru/autonomous_parser.py,399
  src/koru/autonomous_process_guard.py,220
  src/koru/autonomous_startup.py,257
  src/koru/autonomous_wup.py,287
  src/koru/autonomy/__init__.py,26
  src/koru/autonomy/config.py,122
  src/koru/autonomy/env.py,251
  src/koru/autonomy/environment.py,225
  src/koru/autonomy/heal.py,113
  src/koru/autonomy/ide_work.py,297
  src/koru/autonomy/operator_pipeline.py,532
  src/koru/autonomy/post_run_verify.py,355
  src/koru/autonomy/prompts.py,102
  src/koru/autonomy/telemetry_snapshot.py,80
  src/koru/autopilot/__init__.py,19
  src/koru/autopilot/audit.py,10
  src/koru/autopilot/cli_command.py,1283
  src/koru/autopilot/client.py,12
  src/koru/autopilot/config.py,10
  src/koru/autopilot/daemon.py,17
  src/koru/autopilot/host_setup.py,10
  src/koru/autopilot/ide.py,10
  src/koru/autopilot/injector.py,10
  src/koru/autopilot/os_injector.py,10
  src/koru/autopilot/plugin_installer.py,10
  src/koru/autopilot/protocol.py,50
  src/koru/autopilot/utils/__init__.py,6
  src/koru/autopilot/utils/client_helpers.py,58
  src/koru/bootstrap.py,447
  src/koru/cli/__init__.py,56
  src/koru/cli/__main__.py,9
  src/koru/cli/commands.py,1
  src/koru/cli/parsers.py,1
  src/koru/cli.py,1869
  src/koru/context.py,1200
  src/koru/doctor.py,514
  src/koru/dotenv_loader.py,105
  src/koru/dsl/__init__.py,10
  src/koru/events.py,91
  src/koru/gate.py,203
  src/koru/gc.py,372
  src/koru/gc_cli_helpers.py,84
  src/koru/ide_client.py,146
  src/koru/ide_router.py,99
  src/koru/ide_runtime.py,45
  src/koru/init.py,611
  src/koru/init_host_environment.py,261
  src/koru/local_service.py,212
  src/koru/loop.py,132
  src/koru/mcp_provision.py,398
  src/koru/mcp_server.py,10
  src/koru/planfile_queue.py,38
  src/koru/policy.py,235
  src/koru/project_pipeline.py,151
  src/koru/queue/__init__.py,39
  src/koru/queue/human.py,32
  src/koru/queue/koru_queue_argv.py,45
  src/koru/queue/locking.py,88
  src/koru/queue/loop.py,110
  src/koru/queue/planfile_ticket_note.py,57
  src/koru/queue/runner.py,301
  src/koru/queue/runners.py,209
  src/koru/queue/shell_evidence.py,73
  src/koru/queue/ticket.py,139
  src/koru/queue/types.py,89
  src/koru/queue_clean.py,393
  src/koru/queue_cli_helpers.py,219
  src/koru/redup_integration.py,140
  src/koru/refactor_planfile_handoff.py,43
  src/koru/run_log.py,125
  src/koru/runtime.py,106
  src/koru/scan.py,893
  src/koru/semcod_tools.py,144
  src/koru/serve.py,10
  src/koru/stdio_events.py,50
  src/koru/tasks.py,218
  src/koru/tools.py,283
  src/koru/topology.py,416
  src/koru/topology_cli.py,74
  src/koru/utils/__init__.py,6
  src/koru/utils/subprocess_runner.py,41
  src/koru/watch.py,94
  src/koru/wup_testql_compat.py,66
  src/koruapi/__init__.py,26
  src/koruapi/cli.py,129
  src/koruapi/dashboard.py,92
  src/koruapi/dashboard_serve.py,1297
  src/koruapi/integrations.py,199
  src/koruapi/invoke.py,32
  src/koruapi/invoke_handlers.py,189
  src/koruapi/local.py,38
  src/koruapi/mcp.py,16
  src/koruapi/mcp_server.py,1029
  src/koruapi/openapi.py,156
  src/koruapi/server.py,172
  src/korudsl/__init__.py,26
  src/korudsl/cli.py,82
  src/korudsl/library.py,208
  src/korudsl/transform.py,71
  src/koruide/__init__.py,68
  src/koruide/audit.py,158
  src/koruide/client.py,129
  src/koruide/config.py,121
  src/koruide/daemon.py,716
  src/koruide/host_setup.py,227
  src/koruide/ide.py,544
  src/koruide/injector.py,404
  src/koruide/os_injector.py,393
  src/koruide/plugin_installer.py,412
  src/koruide/protocol.py,232
  src/koruide/socket.py,46
  src/koruide/utils.py,22
  test-data/.planfile/.koru/run-autonomous.sh,7
  test-data/.planfile/.koru/setup-autopilot-host.sh,14
  test-data/.planfile/.koru/shell-env.sh,5
  tests/e2e/bootstrap.sh,94
  tests/e2e/init.sh,29
  tests/e2e/smoke.sh,112
  tests/test_activity_log.py,26
  tests/test_agent_backend_runtime.py,156
  tests/test_agent_backends.py,88
  tests/test_agent_backends_cli.py,34
  tests/test_agent_cli.py,101
  tests/test_agents.py,196
  tests/test_autonomous.py,1685
  tests/test_autonomous_diagnostics.py,64
  tests/test_autonomous_parser_detection.py,16
  tests/test_autonomous_process_detection.py,37
  tests/test_autonomous_scenarios.py,305
  tests/test_autonomous_startup.py,91
  tests/test_autonomy_config.py,141
  tests/test_autonomy_env.py,79
  tests/test_autonomy_environment.py,220
  tests/test_autonomy_prompts.py,162
  tests/test_autopilot_audit.py,124
  tests/test_autopilot_cli.py,922
  tests/test_autopilot_client_drive_errors.py,16
  tests/test_autopilot_config.py,156
  tests/test_autopilot_daemon.py,736
  tests/test_autopilot_host_setup.py,124
  tests/test_autopilot_ide.py,335
  tests/test_autopilot_injector.py,275
  tests/test_autopilot_jetbrains_scaffold.py,46
  tests/test_autopilot_os_injector.py,308
  tests/test_autopilot_plugin_installer.py,167
  tests/test_autopilot_protocol.py,154
  tests/test_autopilot_socket_path.py,30
  tests/test_bootstrap.py,296
  tests/test_cli.py,432
  tests/test_context.py,548
  tests/test_dashboard_topology_post.py,36
  tests/test_docker_e2e.py,550
  tests/test_docs_ide_control_surfaces.py,55
  tests/test_doctor.py,455
  tests/test_dotenv_loader.py,117
  tests/test_e2e.py,955
  tests/test_events.py,67
  tests/test_gate.py,167
  tests/test_gc.py,277
  tests/test_gc_cli_helpers.py,31
  tests/test_ide_client.py,115
  tests/test_ide_client_contract.py,106
  tests/test_ide_router.py,257
  tests/test_ide_runtime.py,39
  tests/test_ide_work.py,135
  tests/test_init.py,332
  tests/test_koru_gate_capture.py,35
  tests/test_koru_queue_argv.py,24
  tests/test_koruapi.py,73
  tests/test_koruapi_transports.py,21
  tests/test_korudsl.py,31
  tests/test_koruide_bridges.py,66
  tests/test_koruide_client.py,83
  tests/test_local_service.py,97
  tests/test_loop.py,95
  tests/test_mcp_provision.py,166
  tests/test_mcp_server.py,235
  tests/test_operator_pipeline.py,191
  tests/test_planfile_queue.py,1119
  tests/test_policy.py,183
  tests/test_post_run_verify.py,153
  tests/test_queue_clean.py,309
  tests/test_queue_cli_helpers.py,38
  tests/test_refactor_planfile_handoff.py,21
  tests/test_regix_taskfile.py,23
  tests/test_run_log.py,139
  tests/test_runtime.py,131
  tests/test_scan.py,588
  tests/test_semcod_tools.py,51
  tests/test_serve.py,364
  tests/test_shell_evidence.py,51
  tests/test_stdio_autonomous_jsonl.py,99
  tests/test_tasks.py,77
  tests/test_tools.py,110
  tests/test_topology.py,55
  tests/test_topology_cli.py,26
  tests/test_watch.py,102
  tests/test_wup_taskfile.py,38
  tree.sh,2
D:
  scripts/_koru_autodiag_filter_tickets.py:
    e: main
    main()
  scripts/koru-gate-capture.py:
    e: _normalize_line,_first_nonempty_line,_is_noise_line,_first_meaningful_line,_run_planfile,_parse_args,_run_gate_command,_matched_failure_line,_extract_finding_keys_from_item,_existing_finding_tickets,_append_existing_note,_create_ticket,_handle_existing_finding,main
    _normalize_line(text)
    _first_nonempty_line(text)
    _is_noise_line(line)
    _first_meaningful_line(text)
    _run_planfile(project;args)
    _parse_args(argv)
    _run_gate_command(project;command)
    _matched_failure_line(combined;fail_regex)
    _extract_finding_keys_from_item(item;marker_re)
    _existing_finding_tickets(project)
    _append_existing_note()
    _create_ticket()
    _handle_existing_finding()
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
  src/koru/activity_log.py:
    e: activity_enabled,preview_text,_out_stream,activity,activity_info
    activity_enabled()
    preview_text(text)
    _out_stream(fmt)
    activity(category;message)
    activity_info(msg)
  src/koru/agent_backend_runtime.py:
    e: build_agent_backend,AgentBackend,PluginSocketBackend,McpToolBackend,NoopBackend,OsInjectorBackend
    AgentBackend: send_chat(2)  # Push a prompt toward the agent UI (chat / drive session) for
    PluginSocketBackend: send_chat(2)  # Plugin + unix socket — maps ``send_chat`` to autopilot ``dri
    McpToolBackend: send_chat(2)  # MCP-only backend (e.g. Cursor with koru_run_ticket).
    NoopBackend: send_chat(2)  # Explicit no-op backend for headless / smoke / CI runs.
    OsInjectorBackend: send_chat(2)  # Coordinate-based fallback backend (X11 + xdotool).
    build_agent_backend()
  src/koru/agent_backends.py:
    e: normalize_agent_backend_id,list_agent_backend_ids,iter_agent_backend_profiles,get_agent_backend_profile,_parse_lane,load_agent_integration_config,validate_agent_integration_config,AgentBackendProfile,LaneConfig,AgentIntegrationConfig
    AgentBackendProfile:  # Static description of one way koru can reach an IDE-side age
    LaneConfig:  # One lane entry under ``koru.yaml`` ``ide_integration.lanes``
    AgentIntegrationConfig:  # Parsed ``ide_integration`` block from a project ``koru.yaml`
    normalize_agent_backend_id(raw)
    list_agent_backend_ids()
    iter_agent_backend_profiles()
    get_agent_backend_profile(backend_id)
    _parse_lane(raw)
    load_agent_integration_config(project)
    validate_agent_integration_config(config)
  src/koru/agent_cli_helpers.py:
    e: try_agent_env_exports,print_agent_list,run_agent_handoff
    try_agent_env_exports(args)
    print_agent_list(args;agents)
    run_agent_handoff(project;args)
  src/koru/agents.py:
    e: normalize_agent_lane_id,autopilot_backend_for_agent_id,_which,_marker,detect_agent_options,detect_project_environment,detect_agent_environment,select_agent,save_agent_prompt,agent_lane_environment,format_agent_lane_exports,launch_agent,AgentOption
    AgentOption: to_dict(0)
    normalize_agent_lane_id(raw)
    autopilot_backend_for_agent_id(agent_id)
    _which(command)
    _marker(project)
    detect_agent_options(project)
    detect_project_environment(project)
    detect_agent_environment(project)
    select_agent(agents)
    save_agent_prompt(project;prompt)
    agent_lane_environment(agent_id)
    format_agent_lane_exports(env)
    launch_agent(agent;project;prompt)
  src/koru/api/__init__.py:
  src/koru/autonomous.py:
    e: _try_os_injector_fallback,_stdio_info,_daemon_activity_log,_allow_keyboard_autopilot_fallback,_resolve_autopilot_ide,_apply_agent_lane_environ,_command_project,_process_cwd,_ancestor_pids,_looks_like_autonomous_up_command,_find_existing_autonomous_processes,stop_prior_autonomous_for_auto_start,_find_existing_wup_processes,_as_managed,_terminate_existing_processes,_confirm_replace_existing,_guard_existing_autonomous_processes,_build_parser,_ensure_init,_start_or_reuse_daemon,_status_has_autopilot_plugin,_wait_for_autopilot_plugin,_queue_loop_waiting_ticket_label,_is_topology_enabled,_current_head,_compute_backoff_sleep,_load_loop_checkpoint,_save_loop_checkpoint,_status_in_skip_list,_run_command_check,_create_diagnostic_ticket,_clear_diagnostic_marker,_read_wup_health,_run_idle_diagnostics,_run_cycle,_setup_autonomous_session,_setup_autopilot_daemon,_configure_loop_state,_run_mcp_provision,_setup_autopilot_plugin,_run_operator_pipeline,_unblock_queue_if_needed,_restart_daemon_if_needed,_handle_cycle_exit_conditions,_cleanup_autonomous_session,_action_up,autonomous_main,ExistingAutonomousProcess,ExistingManagedProcess
    ExistingAutonomousProcess:
    ExistingManagedProcess:
    _try_os_injector_fallback(prompt)
    _stdio_info(msg)
    _daemon_activity_log(msg)
    _allow_keyboard_autopilot_fallback()
    _resolve_autopilot_ide(cli_value)
    _apply_agent_lane_environ(project;agent_lane)
    _command_project(command)
    _process_cwd(pid)
    _ancestor_pids(pid)
    _looks_like_autonomous_up_command(command)
    _find_existing_autonomous_processes(project)
    stop_prior_autonomous_for_auto_start(project)
    _find_existing_wup_processes(project)
    _as_managed(proc)
    _terminate_existing_processes(processes)
    _confirm_replace_existing(processes)
    _guard_existing_autonomous_processes(args;project)
    _build_parser()
    _ensure_init(project)
    _start_or_reuse_daemon()
    _status_has_autopilot_plugin(status;ide)
    _wait_for_autopilot_plugin(client;ide)
    _queue_loop_waiting_ticket_label(queue_result)
    _is_topology_enabled(project;key)
    _current_head(project)
    _compute_backoff_sleep(base;streak;cap;enabled)
    _load_loop_checkpoint(path)
    _save_loop_checkpoint(path)
    _status_in_skip_list(status;skip_statuses)
    _run_command_check(project;check_id;command)
    _create_diagnostic_ticket()
    _clear_diagnostic_marker(state_dir;check_id)
    _read_wup_health()
    _run_idle_diagnostics()
    _run_cycle()
    _setup_autonomous_session(args)
    _setup_autopilot_daemon(args;project)
    _configure_loop_state(args;project)
    _run_mcp_provision(project;stdio_format)
    _setup_autopilot_plugin(args;autopilot_ide;socket_path;client)
    _run_operator_pipeline(args;project;startup_probe;plugin_connected;mcp_provision_ran;correlation_id)
    _unblock_queue_if_needed(project;stdio_format)
    _restart_daemon_if_needed(args;client;socket_path;daemon;thread;autopilot_socket_observed_at_boot;project)
    _handle_cycle_exit_conditions(args;queue_result;cycle;correlation_id)
    _cleanup_autonomous_session(previous_stdio_format_env;previous_sigterm;daemon;thread;wup_process;stdio_format)
    _action_up(args)
    autonomous_main(argv)
  src/koru/autonomous_cycle.py:
    e: _stdio_info,_queue_loop_waiting_ticket_label,_is_topology_enabled,_current_head,_status_in_skip_list,_allow_keyboard_autopilot_fallback,_prefer_keyboard_autopilot,_try_os_injector_fallback,_run_command_check,_create_diagnostic_ticket,_clear_diagnostic_marker,_read_wup_health,_run_idle_diagnostics,_autopilot_event_path,_drain_autopilot_events,_initialize_cycle_telemetry,_heal_stale_socket,_handle_autopilot_events,_handle_queue_hygiene,_handle_post_run_verify_ide,_handle_scan_phase,_handle_queue_loop_phase,_handle_scan_after_idle,_update_stagnation_state,_handle_diagnostics,_handle_autopilot_phase,_emit_cycle_completion_events,run_cycle,DiagnosticResult,AutoloopState
    DiagnosticResult:
    AutoloopState:
    _stdio_info(msg)
    _queue_loop_waiting_ticket_label(queue_result)
    _is_topology_enabled(project;key)
    _current_head(project)
    _status_in_skip_list(status;skip_statuses)
    _allow_keyboard_autopilot_fallback()
    _prefer_keyboard_autopilot()
    _try_os_injector_fallback(prompt)
    _run_command_check(project;check_id;command)
    _create_diagnostic_ticket()
    _clear_diagnostic_marker(state_dir;check_id)
    _read_wup_health()
    _run_idle_diagnostics()
    _autopilot_event_path()
    _drain_autopilot_events(state)
    _initialize_cycle_telemetry()
    _heal_stale_socket()
    _handle_autopilot_events(state;_hp)
    _handle_queue_hygiene(project;cycle;_hp;_emit)
    _handle_post_run_verify_ide(project;state;cycle;_hp;_emit)
    _handle_scan_phase(project;state;cycle;enable_scan;include_semcod_artifacts;scan_skip_if_clean;scan_skip_after;topology_integration;_hp;_emit)
    _handle_queue_loop_phase(project;state;cycle;actor;queue_name;max_iterations;topology_integration;verify_config;_hp;_emit)
    _handle_scan_after_idle(project;state;cycle;queue_result;scan_after_idle_queue;include_semcod_artifacts;scan_after_idle_min_interval_seconds;topology_integration;cycle_telemetry;_hp;_emit)
    _update_stagnation_state(state;queue_result)
    _handle_diagnostics(project;state;cycle;queue_result;idle_diagnostics;diagnostic_tickets;diagnostic_ticket_queue;diagnostic_ticket_priority;diagnostic_state_dir;wup_watch_enabled;wup_diagnostic_tickets;wup_ticket_queue;topology_integration;_hp;_emit)
    _handle_autopilot_phase(project;state;cycle;queue_result;enable_autopilot;client;autopilot_ide;drive_prompt;submit;autopilot_action;autopilot_on_idle_only;autopilot_skip_on_diagnostics_fail;autopilot_skip_drive_idle_streak;autopilot_skip_statuses;diag_result;topology_integration;cycle_telemetry;_hp;_emit)
    _emit_cycle_completion_events(project;state;cycle;queue_result;diag_result;wup_health;autopilot_status;autopilot_ide;autopilot_backend;autopilot_drive_kind;cycle_telemetry;scan_after_idle_queue;scan_after_idle_min_interval_seconds;autopilot_skip_drive_idle_streak;_hp;_emit)
    run_cycle()
  src/koru/autonomous_diagnostics.py:
    e: build_idle_checks,run_idle_check_loop,create_diagnostic_ticket,clear_diagnostic_marker,run_command_check,read_wup_health,run_idle_diagnostics
    build_idle_checks(project;profile)
    run_idle_check_loop()
    create_diagnostic_ticket()
    clear_diagnostic_marker(state_dir;check_id)
    run_command_check()
    read_wup_health()
    run_idle_diagnostics()
  src/koru/autonomous_env.py:
    e: apply_autonomous_env_overrides
    apply_autonomous_env_overrides(args)
  src/koru/autonomous_parser.py:
    e: build_parser,looks_like_autonomous_up_command
    build_parser()
    looks_like_autonomous_up_command(command)
  src/koru/autonomous_process_guard.py:
    e: command_project,process_cwd,ancestor_pids,looks_like_autonomous_up_command,find_existing_autonomous_processes,find_existing_wup_processes,as_managed,terminate_existing_processes,confirm_replace_existing,ExistingAutonomousProcess,ExistingManagedProcess
    ExistingAutonomousProcess:
    ExistingManagedProcess:
    command_project(command)
    process_cwd(pid)
    ancestor_pids(pid)
    looks_like_autonomous_up_command(command)
    find_existing_autonomous_processes(project)
    find_existing_wup_processes(project)
    as_managed(proc)
    terminate_existing_processes(processes)
    confirm_replace_existing(processes)
  src/koru/autonomous_startup.py:
    e: koru_distribution_version,_session_label,_terminal_agent_lane_from_env,resolve_agent_lane_id,resolve_autopilot_ide_for_autonomous,build_startup_probe,format_startup_banner,format_post_startup_operator_hints,AutonomousStartupProbe
    AutonomousStartupProbe:
    koru_distribution_version()
    _session_label()
    _terminal_agent_lane_from_env()
    resolve_agent_lane_id(project;agent_lane_cli)
    resolve_autopilot_ide_for_autonomous(autopilot_ide_cli;lane)
    build_startup_probe(project)
    format_startup_banner(probe)
    format_post_startup_operator_hints(probe)
  src/koru/autonomous_wup.py:
    e: _wup_stdio_info,_wup_topology_gate,_build_wup_watch_config,_resolve_wup_testql_bin,_wup_cpu_throttle_arg,_wup_watch_command,_wup_autodetect,_start_wup_watch,_stop_process,_load_wup_health,_identify_failing_services,_create_wup_diagnostic_tickets,_count_wup_events,_read_wup_health,WupWatchConfig,WupHealthResult,_WupEventState
    WupWatchConfig:
    WupHealthResult:
    _WupEventState:
    _wup_stdio_info(msg)
    _wup_topology_gate(project;key)
    _build_wup_watch_config(args;project)
    _resolve_wup_testql_bin(config)
    _wup_cpu_throttle_arg(value)
    _wup_watch_command(config)
    _wup_autodetect(config)
    _start_wup_watch(config)
    _stop_process(process;label)
    _load_wup_health(health_path)
    _identify_failing_services(health)
    _create_wup_diagnostic_tickets(health;failing;project;ticket_queue;state_dir;create_diagnostic_ticket)
    _count_wup_events(events_path;previous_count)
    _read_wup_health()
  src/koru/autonomy/__init__.py:
  src/koru/autonomy/config.py:
    e: AutonomyConfig
    AutonomyConfig: from_env(1)  # Configuration for autonomous loop (unified shell + Python).
  src/koru/autonomy/env.py:
    e: env_truthy,effective_ticket_source_flags,_env_ticket_sources,_env_get,_apply_ticket_and_diagnostics_env,_apply_autopilot_env,_apply_scan_env,_apply_wup_env,_apply_operator_env,apply_autoloop_env_to_args,autonomous_environ_doctor_probe
    env_truthy(name;default)
    effective_ticket_source_flags(ticket_sources)
    _env_ticket_sources(cli_value;environ)
    _env_get(name;default;environ)
    _apply_ticket_and_diagnostics_env(args;environ)
    _apply_autopilot_env(args;environ)
    _apply_scan_env(args;environ)
    _apply_wup_env(args;environ)
    _apply_operator_env(args;environ)
    apply_autoloop_env_to_args(args)
    autonomous_environ_doctor_probe(project)
  src/koru/autonomy/environment.py:
    e: probe_ide_presence,probe_socket_health,probe_environment,IDEPresence,SocketHealth,EnvironmentReport
    IDEPresence: installed(0)  # Per-IDE detection result.
    SocketHealth: healthy(0)  # State of a Unix-socket file (typically autopilot).
    EnvironmentReport: installed_ides(0),mcp_enabled_ides(0)  # Snapshot of the autonomy-relevant environment.
    probe_ide_presence(project)
    probe_socket_health(path)
    probe_environment(project)
  src/koru/autonomy/heal.py:
    e: remove_stale_socket,heal_environment,summarise,RepairResult
    RepairResult:  # Outcome of one self-heal action.
    remove_stale_socket(socket)
    heal_environment(report)
    summarise(results)
  src/koru/autonomy/ide_work.py:
    e: extract_ticket_id_from_text,_parse_open_tickets,fetch_next_open_ticket,build_ide_work_prompt,resolve_idle_drive_prompt,_parse_iso_datetime,_ticket_in_progress_started_at,_list_in_progress_tickets,release_stale_in_progress_tickets,resolve_in_progress_stale_minutes,release_in_progress_tickets
    extract_ticket_id_from_text(text)
    _parse_open_tickets(stdout)
    fetch_next_open_ticket(project)
    build_ide_work_prompt(ticket)
    resolve_idle_drive_prompt(project)
    _parse_iso_datetime(value)
    _ticket_in_progress_started_at(ticket)
    _list_in_progress_tickets(project)
    release_stale_in_progress_tickets(project)
    resolve_in_progress_stale_minutes(project)
    release_in_progress_tickets(project)
  src/koru/autonomy/operator_pipeline.py:
    e: _operator_state_dir,_marker_path,_read_marker,_write_marker,_clear_marker,_close_resolved_step_ticket,_mcp_koru_configured,_candidate_planfile_health_urls,_planfile_api_ok,_operator_autostart_server_enabled,_try_start_planfile_api,_os_profile_ok,_host_injectors_ok,build_operator_steps,_emit_step,_create_step_ticket,run_startup_operator_pipeline,sys_stdout_for_format,OperatorStep,OperatorPipelineResult
    OperatorStep:
    OperatorPipelineResult:
    _operator_state_dir(project)
    _marker_path(state_dir;step_id)
    _read_marker(state_dir;step_id)
    _write_marker(state_dir;step_id;ticket_id)
    _clear_marker(state_dir;step_id)
    _close_resolved_step_ticket(project)
    _mcp_koru_configured(project)
    _candidate_planfile_health_urls(project)
    _planfile_api_ok(project)
    _operator_autostart_server_enabled()
    _try_start_planfile_api(project)
    _os_profile_ok(ide;project)
    _host_injectors_ok()
    build_operator_steps()
    _emit_step(stream)
    _create_step_ticket(project;step)
    run_startup_operator_pipeline()
    sys_stdout_for_format(fmt)
  src/koru/autonomy/post_run_verify.py:
    e: _truthy_env,load_post_run_verify_config,_parse_iso_datetime,fetch_ticket_status,fetch_recently_done_ticket_ids,_record_verify_outcomes,verify_after_ide_work,run_verify_commands,_truncate,apply_verify_failure,verify_completed_tickets,_HasIdeVerifyState,PostRunVerifyConfig
    _HasIdeVerifyState:
    PostRunVerifyConfig:
    _truthy_env(name)
    load_post_run_verify_config(project)
    _parse_iso_datetime(value)
    fetch_ticket_status(project;ticket_id)
    fetch_recently_done_ticket_ids(project)
    _record_verify_outcomes(state;outcomes)
    verify_after_ide_work(project;state)
    run_verify_commands(project;commands)
    _truncate(text;limit)
    apply_verify_failure(project;ticket_id)
    verify_completed_tickets(project;ticket_ids)
  src/koru/autonomy/prompts.py:
    e: build_prompt,PromptDecision
    PromptDecision:  # Result of building a prompt for autopilot.send_chat.
    build_prompt()
  src/koru/autonomy/telemetry_snapshot.py:
    e: autonomy_telemetry_path,write_autonomy_cycle_telemetry,build_autonomy_loop_brief
    autonomy_telemetry_path(project)
    write_autonomy_cycle_telemetry(project)
    build_autonomy_loop_brief(project)
  src/koru/autopilot/__init__.py:
  src/koru/autopilot/audit.py:
  src/koru/autopilot/cli_command.py:
    e: _resolve_session_ides,_action_calibrate,_action_session_start,_build_parser,_client,_action_daemon,_auto_direct_fallback_enabled,_should_fallback_to_direct,_run_direct_drive,_action_drive,_action_status,_action_shutdown,_action_ide_list,_doctor_fix_payload,_render_doctor_text,_render_doctor_json,_action_doctor,_action_setup_host,_plugin_repo_dir,_resolve_plugin_vsix_path,_ide_from_terminal_env,_resolve_plugin_target_ide,_resolve_plugin_editor_bin,_render_install_plugin_dry_run,_render_install_plugin_result,_action_install_plugin,_build_brief,_action_handoff,_format_tail_entry,_render_tail_json,_render_tail_text,_action_tail,_systemd_user_dir,_resolve_koru_bin,_render_unit,_action_install_unit,autopilot_main
    _resolve_session_ides(raw)
    _action_calibrate(args)
    _action_session_start(args)
    _build_parser()
    _client(args)
    _action_daemon(args)
    _auto_direct_fallback_enabled()
    _should_fallback_to_direct(args;reply)
    _run_direct_drive(args;text)
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
  src/koru/autopilot/config.py:
  src/koru/autopilot/daemon.py:
  src/koru/autopilot/host_setup.py:
  src/koru/autopilot/ide.py:
  src/koru/autopilot/injector.py:
  src/koru/autopilot/os_injector.py:
  src/koru/autopilot/plugin_installer.py:
  src/koru/autopilot/protocol.py:
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
    e: _env_truthy,_command_value,_build_parser,_build_tools_parser,_tools_main,_build_task_parser,_build_serve_parser,_build_local_serve_parser,_build_scan_parser,_render_scan_text,_render_scan_markdown,_scan_main,_build_gate_parser,_gate_main,_build_gc_parser,_gc_main,_build_queue_parser,_render_clean_report_text,_queue_main,_build_agent_parser,_task_main,_serve_main,_local_serve_main,_agent_main,_is_bare_invocation,_build_topology_parser,_render_topology_text,_topology_main,_build_runtime_context_parser,_render_runtime_context_text,_runtime_context_main,_init_ci_main,_mcp_serve_main,_agent_backends_main,_init_ide_main,_refactor_planfile_handoff_main,ide_router_main,_dsl_main,_api_main,_peek_project_from_argv,_auto_main,_doctor_main,_doctor_fix_payload,_render_doctor_with_fix,_init_main,_init_agent_lane_main,_context_main,_bootstrap_main,_watch_main,_queue_run_main,_command_loop_main,main
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
    _init_ci_main(_argv)
    _mcp_serve_main(argv)
    _agent_backends_main(argv)
    _init_ide_main(argv)
    _refactor_planfile_handoff_main(argv)
    ide_router_main(argv)
    _dsl_main(argv)
    _api_main(argv)
    _peek_project_from_argv(argv)
    _auto_main(argv)
    _doctor_main(args;raw_args)
    _doctor_fix_payload(report)
    _render_doctor_with_fix(report;fix_payload)
    _init_main(args)
    _init_agent_lane_main(args)
    _context_main(args)
    _bootstrap_main(args)
    _watch_main(args)
    _queue_run_main(args)
    _command_loop_main(args)
    main()
  src/koru/context.py:
    e: _is_fixture_ticket,_resolve_include_fixtures,_load_project_dotenv,_planfile_command_base,_planfile_env,_fetch_all_tickets,_run_planfile,_safe_json,_git_probe,_build_ticket_args,_try_fallback_ticket_list,_process_list_payload,_process_dict_payload,_extract_error_from_stderr,_fetch_ticket_data,build_context,_load_sprint_data,_find_blocking_tickets,_promote_blocking_to_critical,_promote_bug_priority,_write_sprint_data,_auto_promote_blocking_tickets,_build_instructions,_build_setup_instructions,_build_shared_rules,_build_self_service,_render_header,_render_environment,_render_agent_lanes,_render_autonomous_mode,_render_ai_tool_support_2026,_render_semcod_tools,_render_setup_required,_render_active_ticket,_render_no_active_ticket,_render_gates,_render_project_pipeline,_render_policy,_render_rules,_render_self_service,_render_dashboard,_render_autonomy_loop_brief,render_markdown_handoff
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
    _render_autonomy_loop_brief(ctx)
    render_markdown_handoff(context)
  src/koru/doctor.py:
    e: run_diagnostics,_check_agent_backends_registry,_check_git_repo,_check_planfile_binary,_planfile_version_argv,_check_koru_package_version,_check_planfile_cli_version,_check_planfile_config,_check_planfile_sprints,_check_planfile_sprints_yaml,_check_runtime_dir,_check_koru_project_pipeline,_check_policy_yaml,_check_gitignore,_resolve_pytest_collect_timeout,_check_pytest_collect,_check_ci_command,render_text,Check,DoctorReport
    Check: to_dict(0)  # A single diagnostic outcome.
    DoctorReport: has_failures(0),has_warnings(0),summary(0),to_dict(0)  # Aggregate result of ``run_diagnostics``.
    run_diagnostics(project)
    _check_agent_backends_registry(_project)
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
  src/koru/dsl/__init__.py:
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
  src/koru/gc_cli_helpers.py:
    e: gc_statuses_from_args,gc_result_to_json,print_gc_text_report,emit_gc_management_event,print_gc_report
    gc_statuses_from_args(status_csv)
    gc_result_to_json(result)
    print_gc_text_report(result)
    emit_gc_management_event(args;result)
    print_gc_report(args;result)
  src/koru/ide_client.py:
    e: adapt_legacy_autopilot_client,build_legacy_ide_client,build_koruide_client,build_ide_client,IDEControlClient,LegacyAutopilotClientAdapter
    IDEControlClient: is_running(0),drive(1),status(0),shutdown(0)  # Minimal interface `koru` runtime code expects from an IDE cl
    LegacyAutopilotClientAdapter: is_running(0),drive(1),status(0),shutdown(0)  # Expose legacy :class:`AutopilotClient` through :class:`IDECo
    adapt_legacy_autopilot_client(client)
    build_legacy_ide_client()
    build_koruide_client()
    build_ide_client()
  src/koru/ide_router.py:
    e: is_headless_environment,resolve_ide_route,IDERoute
    IDERoute:  # Resolved routing decision for one Koru process.
    is_headless_environment(environ)
    resolve_ide_route()
  src/koru/ide_runtime.py:
    e: build_host_setup_report,detect_running_ides
    build_host_setup_report()
    detect_running_ides()
  src/koru/init.py:
    e: init_project,refresh_init_agent_lane,_init_auto_agent_lane,_read_persisted_agent_lane,_resolve_init_agent_lane,resolve_project_agent_lane,_write_autopilot_host_setup_script,_write_agent_lane_artifacts,_remove_agent_lane_artifacts,_write_policy_stub_if_absent,_ensure_gitignore_entry,InitReport
    InitReport: summary(0)  # Summary of what ``init_project`` actually changed on disk.
    init_project(project)
    refresh_init_agent_lane(project)
    _init_auto_agent_lane(project)
    _read_persisted_agent_lane(project)
    _resolve_init_agent_lane(project;agent_lane)
    resolve_project_agent_lane(project;agent_lane)
    _write_autopilot_host_setup_script(project)
    _write_agent_lane_artifacts(project;lane)
    _remove_agent_lane_artifacts(rt)
    _write_policy_stub_if_absent(project)
    _ensure_gitignore_entry(project)
  src/koru/init_host_environment.py:
    e: _read_os_release,_id_group_names,_uinput_snapshot,build_host_environment_report,_recommended_next_steps,_render_host_environment_md,write_host_environment_bundle
    _read_os_release()
    _id_group_names()
    _uinput_snapshot()
    build_host_environment_report()
    _recommended_next_steps(base;groups)
    _render_host_environment_md(report)
    write_host_environment_bundle(project)
  src/koru/local_service.py:
    e: _koru_version,_env_int,_read_bounded_json_object,default_local_service_config,_build_handler,build_local_service_server,run_local_service,start_local_service_background,LocalServiceConfig,_EventBuffer
    LocalServiceConfig:  # Configuration for ``koru local-serve``.
    _EventBuffer: __init__(1),append(1),snapshot(0)  # Thread-safe ring of recent event records (oldest dropped at 
    _koru_version()
    _env_int(name;default)
    _read_bounded_json_object(handler)
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
  src/koru/mcp_provision.py:
    e: _windsurf_global_config,_cursor_project_config,_vscode_project_config,_windsurf_project_config,_resolved_koru_command,_koru_mcp_entry,_koru_mcp_entry_cursor,_maybe_upgrade_koru_command,detect_ides,_read_json,_write_json,provision_windsurf,provision_cursor,provision_vscode,remove_from_config,ensure_koru_mcp_not_disabled,_resolve_targets,_removal_paths_for_ide,_apply_target,_render_results,init_ide_main
    _windsurf_global_config()
    _cursor_project_config(project)
    _vscode_project_config(project)
    _windsurf_project_config(project)
    _resolved_koru_command()
    _koru_mcp_entry()
    _koru_mcp_entry_cursor()
    _maybe_upgrade_koru_command(servers)
    detect_ides()
    _read_json(path)
    _write_json(path;data)
    provision_windsurf(project)
    provision_cursor(project)
    provision_vscode(project)
    remove_from_config(config_path)
    ensure_koru_mcp_not_disabled(project)
    _resolve_targets(ide)
    _removal_paths_for_ide(ide;project)
    _apply_target(ide;project)
    _render_results(results;output_format)
    init_ide_main(argv)
  src/koru/mcp_server.py:
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
  src/koru/queue/koru_queue_argv.py:
    e: build_koru_queue_argv
    build_koru_queue_argv(project)
  src/koru/queue/locking.py:
    e: queue_lock_wanted,queue_runner_lock,claim_lease_seconds_str,ticket_claim_or_error
    queue_lock_wanted()
    queue_runner_lock(project)
    claim_lease_seconds_str()
    ticket_claim_or_error(project;ticket_id;actor)
  src/koru/queue/loop.py:
    e: run_planfile_queue_loop
    run_planfile_queue_loop()
  src/koru/queue/planfile_ticket_note.py:
    e: _stderr_unknown_option,append_shell_evidence_note
    _stderr_unknown_option(stderr;flag)
    append_shell_evidence_note(project;ticket_id;note)
  src/koru/queue/runner.py:
    e: _source_tool,run_next_planfile_task
    _source_tool(ticket)
    run_next_planfile_task()
  src/koru/queue/runners.py:
    e: _planfile_env,run_process,run_shell_command,run_api_request,run_llm_request
    _planfile_env()
    run_process(command;project)
    run_shell_command(command;project)
    run_api_request(request;_project)
    run_llm_request(request;_project)
  src/koru/queue/shell_evidence.py:
    e: _tail_stream,format_shell_run_note
    _tail_stream(text;limit)
    format_shell_run_note()
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
    e: _planfile_base,_parse_age_days,_matched_rules,_cleanable_statuses,_maybe_skip_active_ticket,_candidate_from_ticket,find_candidates,_build_close_note,_list_tickets,_close_ticket,clean_queue,CleanupCandidate,CleanupReport
    CleanupCandidate: explanation(0)  # A planfile ticket selected for cleanup, with the reasons why
    CleanupReport: to_dict(0)  # Outcome of a (dry-run or applied) sweep.
    _planfile_base()
    _parse_age_days(ticket)
    _matched_rules(ticket)
    _cleanable_statuses()
    _maybe_skip_active_ticket(ticket;ticket_id;status)
    _candidate_from_ticket(ticket;ticket_id;status)
    find_candidates(tickets)
    _build_close_note(candidate;reason)
    _list_tickets(project;runner)
    _close_ticket(project;candidate;reason;runner)
    clean_queue(project)
  src/koru/queue_cli_helpers.py:
    e: queue_status_marker,queue_loop_exit_code,single_task_ticket_lists,emit_queue_run_started,open_queue_run_log,_queue_progress_callback,_emit_queue_completed,run_queue_loop_mode,_single_task_summary,run_queue_single_mode
    queue_status_marker(status)
    queue_loop_exit_code(last_status)
    single_task_ticket_lists(result)
    emit_queue_run_started(args)
    open_queue_run_log(args)
    _queue_progress_callback(args;run_log)
    _emit_queue_completed(args)
    run_queue_loop_mode(args;run_log)
    _single_task_summary(result)
    run_queue_single_mode(args;run_log)
  src/koru/redup_integration.py:
    e: redup_scan_command,redup_check_command,redup_changed_scan_command,redup_changed_scan_runner_command,_redup_scan_supports,_redup_json_scan_command,run_changed_scan,main
    redup_scan_command(path)
    redup_check_command(path)
    redup_changed_scan_command(path)
    redup_changed_scan_runner_command()
    _redup_scan_supports(option)
    _redup_json_scan_command(path)
    run_changed_scan()
    main(argv)
  src/koru/refactor_planfile_handoff.py:
    e: render_planfile_refactor_handoff
    render_planfile_refactor_handoff(project)
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
    e: scan_pytest_collect,_load_koruignore_patterns,_is_koruignored,scan_todo_markers,scan_missing_gates,scan_missing_tools,scan_gitignore_drift,_scan_jscpd_report,_scan_code2llm_analysis,_scan_testql_export,_scan_redup_filtered,_scan_redup_changed,scan_semcod_quality_artifacts,collect_suggestions,_existing_scan_titles,_create_ticket,run_scan,Suggestion,ScanResult
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
    _scan_redup_changed(project)
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
  src/koru/stdio_events.py:
    e: iso_ts,write_stdio_event,default_stdio_format_from_env
    iso_ts()
    write_stdio_event(stream)
    default_stdio_format_from_env()
  src/koru/tasks.py:
    e: _generate_ticket_id,_build_ticket_labels,_build_ticket_source,_build_ticket_inputs,_build_ticket_dict,create_nl_task,_title_from_text,_read_config,_read_sprint,_write_yaml,CreatedTask
    CreatedTask:
    _generate_ticket_id(config_path;project_name)
    _build_ticket_labels(scaffold)
    _build_ticket_source(scaffold;text;now)
    _build_ticket_inputs(scaffold;text)
    _build_ticket_dict(ticket_id;name;text;priority;sprint;queue_name;labels;source;inputs;executor_kind;executor_mode;files;now)
    create_nl_task(project;text)
    _title_from_text(text)
    _read_config(path)
    _read_sprint(path)
    _write_yaml(path;data)
  src/koru/tools.py:
    e: default_registry_path,resolve_registry_path,load_tool_registry,_first_token,_extract_detect_config,_check_commands_exist,_check_markers_exist,_check_env_vars_exist,_build_detection_result,detect_tools,find_tool_entry,infer_adapter_kind,build_tool_task_scaffold,render_tools_detect_text
    default_registry_path()
    resolve_registry_path(path_override)
    load_tool_registry(path_override)
    _first_token(command)
    _extract_detect_config(item)
    _check_commands_exist(commands)
    _check_markers_exist(project;markers)
    _check_env_vars_exist(env_vars)
    _build_detection_result(item;available;found_commands;found_markers;found_env)
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
  src/koru/topology_cli.py:
    e: render_topology_text,_render_component_rows,_render_pipeline_rows,apply_topology_mutations,TopologyMutation
    TopologyMutation:
    render_topology_text(topology)
    _render_component_rows(topology)
    _render_pipeline_rows(topology)
    apply_topology_mutations(topo;mutations)
  src/koru/utils/__init__.py:
  src/koru/utils/subprocess_runner.py:
    e: default_subprocess_runner,resolve_planfile_subpath,get_python_cmd
    default_subprocess_runner(cmd;cwd)
    resolve_planfile_subpath(project)
    get_python_cmd(project)
  src/koru/watch.py:
    e: _format_connected_event,_format_management_event,_format_ticket_event,format_queue_event,_default_connect,watch_planfile_events
    _format_connected_event(event)
    _format_management_event(event)
    _format_ticket_event(event;event_type)
    format_queue_event(event)
    _default_connect(ws_url)
    watch_planfile_events(ws_url)
  src/koru/wup_testql_compat.py:
    e: _normalize_timeout,_normalize_args,_real_testql,main
    _normalize_timeout(value)
    _normalize_args(args)
    _real_testql()
    main(argv)
  src/koruapi/__init__.py:
  src/koruapi/cli.py:
    e: _build_parser,_parse_body,main
    _build_parser()
    _parse_body(raw)
    main(argv)
  src/koruapi/dashboard.py:
    e: _env_truthy,build_serve_parser,dashboard_main
    _env_truthy(name)
    build_serve_parser()
    dashboard_main(argv)
  src/koruapi/dashboard_serve.py:
    e: _list_tickets,apply_topology_post_update,_bulk_waiting_input_action,_address_in_use,_listener_pids_for_tcp_port,_cmdline_suggests_koru_serve_from_bytes,_cmdline_suggests_koru_serve,_try_stop_prior_koru_serve_listener,serve_endpoint_path,read_serve_endpoint,_build_handler,build_server,write_serve_endpoint_file,bind_serve_server,serve,start_serve_background,ServeConfig
    ServeConfig:
    _list_tickets(project)
    apply_topology_post_update(project;body)
    _bulk_waiting_input_action(project)
    _address_in_use(exc)
    _listener_pids_for_tcp_port(port)
    _cmdline_suggests_koru_serve_from_bytes(raw)
    _cmdline_suggests_koru_serve(pid)
    _try_stop_prior_koru_serve_listener(host;port)
    serve_endpoint_path(project)
    read_serve_endpoint(project)
    _build_handler(config)
    build_server(config)
    write_serve_endpoint_file(config)
    bind_serve_server(config)
    serve(config)
    start_serve_background(config)
  src/koruapi/integrations.py:
    e: list_integrations,get_integration,IntegrationSpec
    IntegrationSpec:  # One invokable integration exposed via :mod:`koruapi`.
    list_integrations()
    get_integration(integration_id)
  src/koruapi/invoke.py:
    e: invoke_integration
    invoke_integration(integration_id)
  src/koruapi/invoke_handlers.py:
    e: _handle_context_build,_handle_doctor_run,_handle_scan_apply,_handle_queue_loop,_handle_autopilot_status,_handle_autopilot_drive,_handle_dsl_to_library,_handle_dsl_to_dsl,_handle_dsl_roundtrip,_handle_topology_read,_handle_gate_regix,_handle_planfile_tickets,_handle_mcp_list_tickets,_handle_mcp_run_ticket,_handle_mcp_quality_gates,InvokeError
    InvokeError:
    _handle_context_build(project;_method;payload)
    _handle_doctor_run(project;_method;_payload)
    _handle_scan_apply(project;method;payload)
    _handle_queue_loop(project;method;payload)
    _handle_autopilot_status(_project;_method;_payload)
    _handle_autopilot_drive(_project;_method;payload)
    _handle_dsl_to_library(_project;_method;payload)
    _handle_dsl_to_dsl(_project;_method;payload)
    _handle_dsl_roundtrip(_project;_method;payload)
    _handle_topology_read(project;_method;_payload)
    _handle_gate_regix(project;_method;payload)
    _handle_planfile_tickets(project;_method;payload)
    _handle_mcp_list_tickets(project;_method;payload)
    _handle_mcp_run_ticket(project;_method;payload)
    _handle_mcp_quality_gates(project;_method;payload)
  src/koruapi/local.py:
    e: build_local_parser,local_main
    build_local_parser()
    local_main(argv)
  src/koruapi/mcp.py:
    e: mcp_main
    mcp_main(argv)
  src/koruapi/mcp_server.py:
    e: _get_job_store_path,_load_jobs,_save_jobs,_get_process_memory_mb,_monitor_subprocess_oom,_get_python_cmd,_run_planfile_cli,_parse_tickets_json,_tickets_for_status_filter,_serialize_mcp_ticket,tool_list_tickets,_create_job,_update_job,_collect_process_logs,tool_run_ticket,tool_job_status,_gate_commands,_detect_enabled_gates,_resolve_gates,_run_single_gate,tool_run_quality_gates,_find_ticket,_build_edit_context,tool_propose_edits,_jsonrpc_response,_jsonrpc_error,_handle_initialize,_handle_tools_list,_handle_tools_call,handle_message,run_stdio,_write,_log,mcp_serve_main
    _get_job_store_path(project)
    _load_jobs(project)
    _save_jobs(jobs;project)
    _get_process_memory_mb(pid)
    _monitor_subprocess_oom(proc;threshold_mb;interval_seconds;action)
    _get_python_cmd()
    _run_planfile_cli(project)
    _parse_tickets_json(stdout)
    _tickets_for_status_filter(ctx;status_filter)
    _serialize_mcp_ticket(ticket)
    tool_list_tickets(arguments)
    _create_job(ticket_id;mode;project)
    _update_job(job_id;project)
    _collect_process_logs(result)
    tool_run_ticket(arguments)
    tool_job_status(arguments)
    _gate_commands(project)
    _detect_enabled_gates(project;known_gates)
    _resolve_gates(project;requested;commands)
    _run_single_gate(project;gate_name;cmd;oom_threshold_mb;oom_interval_seconds;oom_action)
    tool_run_quality_gates(arguments)
    _find_ticket(all_tickets;ticket_id)
    _build_edit_context(project;file_path)
    tool_propose_edits(arguments)
    _jsonrpc_response(req_id;result)
    _jsonrpc_error(req_id;code;message;data)
    _handle_initialize(params)
    _handle_tools_list(params)
    _handle_tools_call(params)
    handle_message(msg)
    run_stdio()
    _write(payload)
    _log(msg)
    mcp_serve_main(argv)
  src/koruapi/openapi.py:
    e: build_openapi_document
    build_openapi_document()
  src/koruapi/server.py:
    e: _json_response,_read_json_body,_parse_invoke_request,_handle_invoke_post,serve,KoruAPIHandler
    KoruAPIHandler: log_message(1),do_GET(0),do_POST(0)
    _json_response(handler;status;payload)
    _read_json_body(handler)
    _parse_invoke_request(body;default_project)
    _handle_invoke_post(handler)
    serve()
  src/korudsl/__init__.py:
  src/korudsl/cli.py:
    e: _build_parser,_read_input,main
    _build_parser()
    _read_input(path)
    main(argv)
  src/korudsl/library.py:
    e: ensure_library_structure,_start_goal,_handle_func,_handle_set,_handle_wait,_handle_get,_handle_save,_handle_if,_handle_error,_handle_correct,_apply_prefixed_line,normalize_dsl_to_library,convert_goals_json_to_library,_emit_step,_emit_objective,_emit_functions,_emit_goal,_emit_goals,library_to_dsl
    ensure_library_structure(library)
    _start_goal(library;line)
    _handle_func(line;goal;library)
    _handle_set(line;goal)
    _handle_wait(line;goal)
    _handle_get(line;goal)
    _handle_save(line;goal)
    _handle_if(line;goal)
    _handle_error(line;goal)
    _handle_correct(line;goal)
    _apply_prefixed_line(line;goal;library)
    normalize_dsl_to_library(dsl_text;existing_library)
    convert_goals_json_to_library(goals_json;existing_library)
    _emit_step(step)
    _emit_objective(obj)
    _emit_functions(lib)
    _emit_goal(goal)
    _emit_goals(lib)
    library_to_dsl(library)
  src/korudsl/transform.py:
    e: library_from_any,library_to_any,dsl_roundtrip_report,load_path
    library_from_any(payload)
    library_to_any(library)
    dsl_roundtrip_report(dsl_text)
    load_path(path)
  src/koruide/__init__.py:
  src/koruide/audit.py:
    e: default_log_path,_isoformat_utc,_JSONFormatter,AuditLog
    _JSONFormatter: format(1)  # Emit ``record.msg`` verbatim — we hand it in pre-serialised.
    AuditLog: __init__(0),record(1),close(0)  # Append-only audit log for autopilot events.
    default_log_path()
    _isoformat_utc(ts)
  src/koruide/client.py:
    e: build_client,KoruIDEClient
    KoruIDEClient: __init__(0),_connect(0),request(1),is_running(0),drive(1),status(0),shutdown(0)  # Connect, send one message, read one reply, disconnect.
    build_client()
  src/koruide/config.py:
    e: default_config_path,_merge_submit_keys,load_config,cached_config,clear_config_cache,AutopilotConfig
    AutopilotConfig: submit_key_for(1)  # In-memory view of ``autopilot.toml`` (or defaults).
    default_config_path()
    _merge_submit_keys(raw)
    load_config(path)
    cached_config()
    clear_config_cache()
  src/koruide/daemon.py:
    e: _env_truthy,_prefer_keyboard_drive,_load_context_module,_default_handoff,_peer_uid,_Client,AutopilotDaemon
    _Client:  # In-memory state for one connected socket.
    AutopilotDaemon: __init__(0),start(0),serve_forever(0),stop(0),_shutdown(0),_accept(0),_on_readable(1),_dispatch(2),_send(2),_drop(1),_plugin_for(1),_handle_drive(2),_drive_via_plugin(5),_try_os_injector_drive(3),_drive_via_keyboard(5),_handle_hello(2),_handle_status(2),_plugin_ack_needs_os_fallback(0),_relay_os_fallback_ack(6),_handle_ack(2),_event_path(0),_append_event(2),_handle_plugin_event(2),_handle_shutdown(2),_handle_ping(2),_build_handler_table(0)  # Selector-based unix-socket broker.
    _env_truthy(name)
    _prefer_keyboard_drive()
    _load_context_module()
    _default_handoff(project)
    _peer_uid(sock)
  src/koruide/host_setup.py:
    e: _package_manager_hint,_human_followups,build_setup_host_report,_try_apt_install,run_host_setup,_print_setup_host_header,_print_setup_host_backends,_print_setup_host_ides,_print_setup_host_apt_section,_print_setup_host_human_followups,_print_setup_host_install_details,_print_text_report
    _package_manager_hint()
    _human_followups(injector;selected)
    build_setup_host_report()
    _try_apt_install(packages)
    run_host_setup()
    _print_setup_host_header(report)
    _print_setup_host_backends(report)
    _print_setup_host_ides(report)
    _print_setup_host_apt_section(report)
    _print_setup_host_human_followups(report)
    _print_setup_host_install_details(report)
    _print_text_report(report)
  src/koruide/ide.py:
    e: _iter_proc_pids,_read_comm,_read_cmdline,_read_exe,_matches,_score_comm_name,_score_exe_path,_score_cmdline_flags,_candidate_score,detect_running_ides,_active_window_pid_x11,_ide_id_from_process,detect_focused_ide_id,_vscode_family_env_present,_vscode_family_flavor_from_env,_terminal_ide_from_env,_terminal_ide_from_parent_chain,detect_terminal_host_ide_id,focused_ide,pick_target,is_linux,detect_running_ides_cached,clear_detect_cache,_has_os_injector_profile,_auto_profile_candidate_ids,_resolve_explicit_drive_target,_resolve_auto_drive_target,resolve_drive_target,RunningIDE
    RunningIDE: to_dict(0)  # A single IDE process discovered on the system.
    _iter_proc_pids()
    _read_comm(pid)
    _read_cmdline(pid)
    _read_exe(pid)
    _matches(comm;cmdline;patterns)
    _score_comm_name(ide_id;comm)
    _score_exe_path(ide_id;exe)
    _score_cmdline_flags(cmdline)
    _candidate_score(ide_id;pid;comm;cmdline;exe)
    detect_running_ides()
    _active_window_pid_x11()
    _ide_id_from_process(pid)
    detect_focused_ide_id()
    _vscode_family_env_present()
    _vscode_family_flavor_from_env()
    _terminal_ide_from_env()
    _terminal_ide_from_parent_chain(start_pid)
    detect_terminal_host_ide_id()
    focused_ide(detected)
    pick_target(detected)
    is_linux()
    detect_running_ides_cached()
    clear_detect_cache()
    _has_os_injector_profile(tool_id;project)
    _auto_profile_candidate_ids(detected)
    _resolve_explicit_drive_target(prefer;target)
    _resolve_auto_drive_target(detected;target)
    resolve_drive_target(ide_arg;os_profile)
  src/koruide/injector.py:
    e: _submit_key_for,_which,_session_type,_forced_injector_backend,_ydotool_enter_keycode,_ydotool_submit_mode,_ydotool_ctrl_keycode,_extra_enter_count,_default_runner,BackendStatus,InjectionResult,InjectorError,Injector
    BackendStatus: to_dict(0)  # Result of probing a single backend.
    InjectionResult: to_dict(0)
    InjectorError:  # No usable backend, or the backend call failed.
    Injector: probe(0),_candidate_backends(0),select_backend(0),_type_with_backend(3),type_text(1),submit_only(0),_probe_one(1),_call(1),_press_wtype(1)  # Pick the best available backend and type text through it.
    _submit_key_for(ide)
    _which(name)
    _session_type()
    _forced_injector_backend()
    _ydotool_enter_keycode()
    _ydotool_submit_mode()
    _ydotool_ctrl_keycode()
    _extra_enter_count()
    _default_runner(cmd;stdin)
  src/koruide/os_injector.py:
    e: default_config_path,iter_config_paths,os_injector_env_disabled,os_injector_env_forced,dry_run_from_env,focus_mode_from_env,input_mode_from_env,_is_wayland_session,_cmd_timeout_seconds,_post_focus_delay_seconds,try_load_profile,_read_json,load_profile,save_profile,profile_from_mouse,capture_mouse_xy,capture_from_xdotool,_run_cmd,_xdotool,_tool_pid,_clipboard_backend,_set_clipboard,inject_with_profile,try_drive_with_profile,OsInjectorError,OsInjectorProfile
    OsInjectorError:  # Raised when profile config or xdotool operations fail.
    OsInjectorProfile:  # Chat anchor: pixel position under the cursor at calibration 
    default_config_path()
    iter_config_paths()
    os_injector_env_disabled()
    os_injector_env_forced()
    dry_run_from_env()
    focus_mode_from_env()
    input_mode_from_env()
    _is_wayland_session()
    _cmd_timeout_seconds()
    _post_focus_delay_seconds()
    try_load_profile(tool_id)
    _read_json(path)
    load_profile(tool_id)
    save_profile(profile)
    profile_from_mouse(tool_id)
    capture_mouse_xy()
    capture_from_xdotool()
    _run_cmd(cmd)
    _xdotool(argv_tail)
    _tool_pid(tool_id)
    _clipboard_backend()
    _set_clipboard(text)
    inject_with_profile()
    try_drive_with_profile()
  src/koruide/plugin_installer.py:
    e: _valid_ide,_ide_from_terminal_env,_terminal_vscode_flavor,resolve_target_ide,resolve_extension_vsix,_resolve_ide_command,_settings_path_for_ide,_configure_socket_path,_run,_env_reassert_extension_install,_extension_is_installed,_reassert_extension_extra,_result_already_installed,_install_extension_vsix,install_plugin_for_ide,format_plugin_install_result,PluginInstallResult
    PluginInstallResult: to_dict(0)
    _valid_ide(raw)
    _ide_from_terminal_env()
    _terminal_vscode_flavor()
    resolve_target_ide(requested)
    resolve_extension_vsix()
    _resolve_ide_command(ide)
    _settings_path_for_ide(ide)
    _configure_socket_path(ide;socket_path)
    _run(cmd)
    _env_reassert_extension_install()
    _extension_is_installed(command;runner)
    _reassert_extension_extra(command)
    _result_already_installed(target;command)
    _install_extension_vsix(target;command;vsix)
    install_plugin_for_ide()
    format_plugin_install_result(result)
  src/koruide/protocol.py:
    e: _filter_extras,decode,hello,chat_send,drive,ack,error,session_started,session_ended,message_sent,message_received,status_error,ProtocolError,Message
    ProtocolError:  # Raised when a line cannot be decoded into a valid message.
    Message: to_dict(0),encode(0)
    _filter_extras(msg_type;obj)
    decode(line)
    hello()
    chat_send(text)
    drive(text)
    ack(reply_to)
    error(reply_to;message)
    session_started()
    session_ended()
    message_sent()
    message_received()
    status_error()
  src/koruide/socket.py:
    e: _autopilot_socket_basename,default_socket_path
    _autopilot_socket_basename()
    default_socket_path()
  src/koruide/utils.py:
    e: resolve_xdg_path
    resolve_xdg_path(relative_path)
  tests/test_activity_log.py:
    e: test_activity_flushes_with_timestamp,test_activity_disabled
    test_activity_flushes_with_timestamp(capsys)
    test_activity_disabled(monkeypatch;capsys)
  tests/test_agent_backend_runtime.py:
    e: test_plugin_socket_backend_forwards_send_chat_to_drive,test_mcp_tool_backend_returns_ok_marker,test_mcp_tool_backend_no_server_field,test_noop_backend_returns_ok_with_reason,test_factory_resolves_plugin_socket_with_client,test_factory_plugin_socket_requires_client,test_factory_resolves_mcp_tool,test_factory_resolves_mcp_tool_without_server,test_factory_resolves_none_to_noop,test_factory_resolves_os_injector_from_env,test_factory_os_injector_requires_profile_env,test_factory_normalizes_case_and_whitespace,test_factory_rejects_unknown_backend_id,test_all_backends_implement_send_chat
    test_plugin_socket_backend_forwards_send_chat_to_drive()
    test_mcp_tool_backend_returns_ok_marker()
    test_mcp_tool_backend_no_server_field()
    test_noop_backend_returns_ok_with_reason()
    test_factory_resolves_plugin_socket_with_client()
    test_factory_plugin_socket_requires_client()
    test_factory_resolves_mcp_tool()
    test_factory_resolves_mcp_tool_without_server()
    test_factory_resolves_none_to_noop()
    test_factory_resolves_os_injector_from_env(monkeypatch)
    test_factory_os_injector_requires_profile_env(monkeypatch)
    test_factory_normalizes_case_and_whitespace()
    test_factory_rejects_unknown_backend_id()
    test_all_backends_implement_send_chat(backend_id;kwargs)
  tests/test_agent_backends.py:
    e: test_list_contains_core_backends,test_iter_matches_list_count,test_get_profile_returns_none_for_unknown,test_mcp_profile_is_tools_only,test_backend_aliases_normalize_to_profiles,test_load_agent_integration_config_from_koru_yaml,test_validate_agent_integration_config_reports_unknown_backend
    test_list_contains_core_backends()
    test_iter_matches_list_count()
    test_get_profile_returns_none_for_unknown()
    test_mcp_profile_is_tools_only()
    test_backend_aliases_normalize_to_profiles()
    test_load_agent_integration_config_from_koru_yaml(tmp_path)
    test_validate_agent_integration_config_reports_unknown_backend(tmp_path)
  tests/test_agent_backends_cli.py:
    e: test_list_text_prints_ids,test_list_json_is_array,test_show_one_json,test_unknown_id_errors
    test_list_text_prints_ids(capsys)
    test_list_json_is_array(capsys)
    test_show_one_json(capsys)
    test_unknown_id_errors(capsys)
  tests/test_agent_cli.py:
    e: _run_main,test_agent_list_json_includes_ready_summary,test_agent_env_exports_cursor_lane
    _run_main()
    test_agent_list_json_includes_ready_summary()
    test_agent_env_exports_cursor_lane()
  tests/test_agents.py:
    e: TestAgentDetection,TestAgentLaneEnv,TestAutopilotBackendForLane
    TestAgentDetection: test_detects_project_hints_without_cli(0),test_detects_openrouter_lane_from_env(0),test_select_agent_prefers_launchable_when_noninteractive(0),test_detects_gemini_cli_when_available(0),test_select_agent_can_pick_gemini_when_only_launchable(0),test_detects_cline_when_available(0),test_select_agent_can_pick_cline_when_only_launchable(0),test_agent_lane_environment_cursor(0),test_normalize_agent_lane_id_strips_garbage(0),test_format_agent_lane_exports_is_shell_safe(0),test_detects_qwen_code_when_available(0),test_select_agent_can_pick_qwen_when_only_launchable(0),test_detects_opencode_when_available(0),test_select_agent_can_pick_opencode_when_only_launchable(0)
    TestAgentLaneEnv: test_qwen_lane_env_defaults(0),test_opencode_lane_env_defaults(0)
    TestAutopilotBackendForLane: test_backend_matrix(0)
  tests/test_autonomous.py:
    e: test_effective_flags_matrix,test_scan_after_idle_queue_runs_scan_when_queue_idle,test_scan_after_idle_min_interval_skips_second_scan,test_idle_streak_skip_increments_telemetry,test_ticket_sources_env_overrides_cli_queue_to_scan,test_ticket_sources_env_invalid_keeps_cli_queue,test_autonomous_environ_doctor_probe_invalid_ticket_sources,test_autonomous_environ_doctor_probe_pass_summary,test_looks_like_autonomous_matches_koru_cli_auto,test_looks_like_autonomous_matches_koru_autonomous_regex,test_auto_main_argv_injects_replace_existing,test_stop_prior_autonomous_for_auto_start_terminates,test_guard_existing_autonomous_noninteractive_blocks_duplicate,test_guard_existing_autonomous_replace_existing_terminates,test_guard_existing_autonomous_replace_existing_terminates_stale_wup,test_guard_existing_autonomous_interactive_decline_blocks_duplicate,test_autonomous_jsonl_keyboard_interrupt_emits_reason,test_queue_loop_result_summary_includes_waiting_ticket,test_queue_loop_waiting_ticket_label_helper,test_resolve_autopilot_ide_env_overrides_cli,test_resolve_autopilot_ide_ignores_bad_env,test_resolve_autopilot_ide_auto_env_does_not_override_cli,test_resolve_autopilot_ide_headless_forces_auto,test_resolve_autopilot_ide_headless_allow_autopilot_honors_env,test_resolve_autopilot_ide_koru_ide_mode_headless,test_resolve_autopilot_ide_ssh_without_display_headless,test_resolve_autopilot_ide_ssh_with_display_uses_cli,test_resolve_autopilot_ide_os_environ_autopilot_ide,test_resolve_autopilot_ide_headless_allow_yes,_isolate_integrated_terminal_env,test_apply_agent_lane_environ_auto_cursor,test_apply_agent_lane_environ_auto_prefers_vscode_terminal,test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env,test_apply_agent_lane_environ_none_is_noop,test_autonomous_main_prepends_up_for_flags,test_up_single_cycle_queue_only_no_autopilot,test_safe_up_uses_queue_diagnostics_without_autopilot,test_up_single_cycle_all_sources_runs_scan,test_up_auto_installs_plugin_before_autopilot_loop,test_status_has_autopilot_plugin_matches_specific_ide,test_wait_for_autopilot_plugin_polls_until_connected,test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message,test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list,test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping,test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure,test_run_cycle_visible_typing_does_not_require_plugin,_fast_autonomous_up,test_up_keeps_running_on_waiting_input_by_default,test_up_stops_on_waiting_input_when_flag_set,test_up_restarts_autopilot_when_socket_disappears_between_cycles,test_compute_backoff_sleep_caps_stagnation,test_env_apply_autoloop_defaults_enables_full_diagnostics,test_run_idle_diagnostics_profile_off_message,test_run_idle_diagnostics_creates_deduped_ticket,test_wup_watch_command_uses_testql_mode,test_wup_watch_command_keeps_explicit_testql_bin,test_wup_watch_command_normalizes_percent_cpu_throttle,test_wup_topology_gate_uses_pipeline_for_gate_wup,test_read_wup_health_creates_high_priority_planfile_ticket,test_read_wup_health_ignores_degraded_fleet_and_clears_marker
    test_effective_flags_matrix()
    test_scan_after_idle_queue_runs_scan_when_queue_idle(tmp_path;monkeypatch)
    test_scan_after_idle_min_interval_skips_second_scan(tmp_path;monkeypatch)
    test_idle_streak_skip_increments_telemetry(tmp_path;monkeypatch)
    test_ticket_sources_env_overrides_cli_queue_to_scan(tmp_path;monkeypatch)
    test_ticket_sources_env_invalid_keeps_cli_queue(tmp_path;monkeypatch;capsys)
    test_autonomous_environ_doctor_probe_invalid_ticket_sources(tmp_path;monkeypatch)
    test_autonomous_environ_doctor_probe_pass_summary(tmp_path;monkeypatch)
    test_looks_like_autonomous_matches_koru_cli_auto()
    test_looks_like_autonomous_matches_koru_autonomous_regex()
    test_auto_main_argv_injects_replace_existing(tmp_path)
    test_stop_prior_autonomous_for_auto_start_terminates(tmp_path;monkeypatch)
    test_guard_existing_autonomous_noninteractive_blocks_duplicate(tmp_path;monkeypatch)
    test_guard_existing_autonomous_replace_existing_terminates(tmp_path;monkeypatch)
    test_guard_existing_autonomous_replace_existing_terminates_stale_wup(tmp_path;monkeypatch)
    test_guard_existing_autonomous_interactive_decline_blocks_duplicate(tmp_path;monkeypatch)
    test_autonomous_jsonl_keyboard_interrupt_emits_reason(tmp_path;monkeypatch)
    test_queue_loop_result_summary_includes_waiting_ticket()
    test_queue_loop_waiting_ticket_label_helper()
    test_resolve_autopilot_ide_env_overrides_cli(monkeypatch)
    test_resolve_autopilot_ide_ignores_bad_env(monkeypatch)
    test_resolve_autopilot_ide_auto_env_does_not_override_cli(monkeypatch)
    test_resolve_autopilot_ide_headless_forces_auto(monkeypatch)
    test_resolve_autopilot_ide_headless_allow_autopilot_honors_env(monkeypatch)
    test_resolve_autopilot_ide_koru_ide_mode_headless(monkeypatch)
    test_resolve_autopilot_ide_ssh_without_display_headless(monkeypatch)
    test_resolve_autopilot_ide_ssh_with_display_uses_cli(monkeypatch)
    test_resolve_autopilot_ide_os_environ_autopilot_ide(monkeypatch)
    test_resolve_autopilot_ide_headless_allow_yes(monkeypatch)
    _isolate_integrated_terminal_env(monkeypatch)
    test_apply_agent_lane_environ_auto_cursor(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_auto_prefers_vscode_terminal(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_none_is_noop(tmp_path;monkeypatch)
    test_autonomous_main_prepends_up_for_flags(tmp_path;monkeypatch)
    test_up_single_cycle_queue_only_no_autopilot(tmp_path;monkeypatch)
    test_safe_up_uses_queue_diagnostics_without_autopilot(tmp_path;monkeypatch)
    test_up_single_cycle_all_sources_runs_scan(tmp_path;monkeypatch)
    test_up_auto_installs_plugin_before_autopilot_loop(tmp_path;monkeypatch)
    test_status_has_autopilot_plugin_matches_specific_ide()
    test_wait_for_autopilot_plugin_polls_until_connected(monkeypatch)
    test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message(tmp_path;monkeypatch)
    test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list(tmp_path;monkeypatch;capsys)
    test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping(tmp_path;monkeypatch)
    test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure(tmp_path;monkeypatch)
    test_run_cycle_visible_typing_does_not_require_plugin(tmp_path;monkeypatch)
    _fast_autonomous_up(monkeypatch)
    test_up_keeps_running_on_waiting_input_by_default(tmp_path;monkeypatch)
    test_up_stops_on_waiting_input_when_flag_set(tmp_path;monkeypatch)
    test_up_restarts_autopilot_when_socket_disappears_between_cycles(tmp_path;monkeypatch)
    test_compute_backoff_sleep_caps_stagnation()
    test_env_apply_autoloop_defaults_enables_full_diagnostics(monkeypatch)
    test_run_idle_diagnostics_profile_off_message(tmp_path;capsys)
    test_run_idle_diagnostics_creates_deduped_ticket(tmp_path;monkeypatch)
    test_wup_watch_command_uses_testql_mode(tmp_path)
    test_wup_watch_command_keeps_explicit_testql_bin(tmp_path)
    test_wup_watch_command_normalizes_percent_cpu_throttle(tmp_path)
    test_wup_topology_gate_uses_pipeline_for_gate_wup(tmp_path;monkeypatch)
    test_read_wup_health_creates_high_priority_planfile_ticket(tmp_path)
    test_read_wup_health_ignores_degraded_fleet_and_clears_marker(tmp_path)
  tests/test_autonomous_diagnostics.py:
    e: test_build_idle_checks_quick_profile_skips_deep_tools,test_build_idle_checks_full_includes_redup_when_available,test_build_idle_checks_full_uses_changed_redup_when_wup_configured,test_run_idle_diagnostics_profile_off
    test_build_idle_checks_quick_profile_skips_deep_tools(tmp_path;monkeypatch)
    test_build_idle_checks_full_includes_redup_when_available(tmp_path;monkeypatch)
    test_build_idle_checks_full_uses_changed_redup_when_wup_configured(tmp_path;monkeypatch)
    test_run_idle_diagnostics_profile_off()
  tests/test_autonomous_parser_detection.py:
    e: test_looks_like_koru_auto_command,test_looks_like_koru_autonomous_up_command,test_looks_like_unrelated_command
    test_looks_like_koru_auto_command()
    test_looks_like_koru_autonomous_up_command()
    test_looks_like_unrelated_command()
  tests/test_autonomous_process_detection.py:
    e: test_find_existing_autonomous_does_not_skip_sibling_from_same_shell
    test_find_existing_autonomous_does_not_skip_sibling_from_same_shell(tmp_path;monkeypatch)
  tests/test_autonomous_scenarios.py:
    e: test_autonomous_main_safe_up_expands_args,test_autonomous_cycle_smoke_scenario,test_autonomous_cycle_autopilot_skipped_when_no_client,test_run_cycle_auto_heals_stale_socket,test_autonomous_cycle_skips_autopilot_after_repeated_idle_when_threshold_set
    test_autonomous_main_safe_up_expands_args()
    test_autonomous_cycle_smoke_scenario()
    test_autonomous_cycle_autopilot_skipped_when_no_client()
    test_run_cycle_auto_heals_stale_socket()
    test_autonomous_cycle_skips_autopilot_after_repeated_idle_when_threshold_set()
  tests/test_autonomous_startup.py:
    e: test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker,test_resolve_autopilot_ide_for_autonomous_returns_string_lane,test_format_post_startup_operator_hints_mentions_socket,test_format_startup_banner_includes_version,test_apply_agent_lane_environ_uses_running_ide
    test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker(tmp_path)
    test_resolve_autopilot_ide_for_autonomous_returns_string_lane()
    test_format_post_startup_operator_hints_mentions_socket(tmp_path)
    test_format_startup_banner_includes_version(tmp_path)
    test_apply_agent_lane_environ_uses_running_ide(tmp_path;monkeypatch)
  tests/test_autonomy_config.py:
    e: test_autonomy_config_defaults,test_autonomy_config_from_env,test_autonomy_config_from_env_defaults,test_autonomy_config_from_env_actor_name_fallback,test_autonomy_config_ticket_sources_valid,test_autonomy_config_autopilot_action_valid,test_autonomy_config_idle_diagnostics_profile_valid,test_autonomy_config_stagnation_control_fields,test_autonomy_config_from_env_idle_streak,test_autonomy_config_diag_state_dir_default
    test_autonomy_config_defaults()
    test_autonomy_config_from_env()
    test_autonomy_config_from_env_defaults()
    test_autonomy_config_from_env_actor_name_fallback()
    test_autonomy_config_ticket_sources_valid()
    test_autonomy_config_autopilot_action_valid()
    test_autonomy_config_idle_diagnostics_profile_valid()
    test_autonomy_config_stagnation_control_fields()
    test_autonomy_config_from_env_idle_streak()
    test_autonomy_config_diag_state_dir_default()
  tests/test_autonomy_env.py:
    e: test_auto_loop_env_defaults_cover_core_autoloop_flags,test_env_truthy_matrix,test_apply_autoloop_env_to_args_custom_environ
    test_auto_loop_env_defaults_cover_core_autoloop_flags()
    test_env_truthy_matrix(monkeypatch)
    test_apply_autoloop_env_to_args_custom_environ()
  tests/test_autonomy_environment.py:
    e: test_probe_socket_health_missing_file,test_probe_socket_health_stale_socket,test_probe_socket_health_listening_socket,test_probe_ide_presence_returns_entry_per_known_ide,test_probe_ide_presence_detects_installed_binary,test_probe_ide_presence_detects_koru_in_cursor_mcp,test_probe_ide_presence_ignores_disabled_koru,test_probe_environment_headless_via_env,test_probe_environment_flags_stale_socket,test_probe_environment_flags_missing_mcp_when_ide_installed,test_remove_stale_socket_skips_when_not_stale,test_remove_stale_socket_dry_run_does_not_mutate,test_remove_stale_socket_fixes_real_stale_socket,test_remove_stale_socket_idempotent_after_fix,test_heal_environment_repairs_stale_socket,test_heal_environment_no_op_on_clean_env,test_summarise_no_repairs,test_summarise_counts_statuses
    test_probe_socket_health_missing_file(tmp_path)
    test_probe_socket_health_stale_socket(tmp_path)
    test_probe_socket_health_listening_socket(tmp_path)
    test_probe_ide_presence_returns_entry_per_known_ide(tmp_path)
    test_probe_ide_presence_detects_installed_binary(tmp_path)
    test_probe_ide_presence_detects_koru_in_cursor_mcp(tmp_path)
    test_probe_ide_presence_ignores_disabled_koru(tmp_path)
    test_probe_environment_headless_via_env(tmp_path)
    test_probe_environment_flags_stale_socket(tmp_path)
    test_probe_environment_flags_missing_mcp_when_ide_installed(tmp_path)
    test_remove_stale_socket_skips_when_not_stale(tmp_path)
    test_remove_stale_socket_dry_run_does_not_mutate(tmp_path)
    test_remove_stale_socket_fixes_real_stale_socket(tmp_path)
    test_remove_stale_socket_idempotent_after_fix(tmp_path)
    test_heal_environment_repairs_stale_socket(tmp_path)
    test_heal_environment_no_op_on_clean_env(tmp_path)
    test_summarise_no_repairs()
    test_summarise_counts_statuses(tmp_path)
  tests/test_autonomy_prompts.py:
    e: _call,test_idle_status_uses_drive_prompt,test_handoff_action_returns_drive_prompt,test_waiting_input_with_message_uses_ticket_prompt,test_waiting_input_empty_message_uses_fallback_prompt,test_waiting_input_empty_message_no_ticket_id,test_waiting_input_strips_whitespace_message,test_stagnation_below_threshold_no_escalation,test_stagnation_at_threshold_triggers_escalation,test_escalation_includes_status_and_streak,test_escalation_skipped_without_ticket_id,test_custom_escalation_threshold,test_drive_action_with_running_status,test_decision_is_frozen
    _call()
    test_idle_status_uses_drive_prompt()
    test_handoff_action_returns_drive_prompt()
    test_waiting_input_with_message_uses_ticket_prompt()
    test_waiting_input_empty_message_uses_fallback_prompt()
    test_waiting_input_empty_message_no_ticket_id()
    test_waiting_input_strips_whitespace_message()
    test_stagnation_below_threshold_no_escalation()
    test_stagnation_at_threshold_triggers_escalation()
    test_escalation_includes_status_and_streak()
    test_escalation_skipped_without_ticket_id()
    test_custom_escalation_threshold()
    test_drive_action_with_running_status()
    test_decision_is_frozen()
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
    e: test_autopilot_parser_requires_action,test_drive_without_daemon_errors,test_drive_missing_text_errors,test_drive_prompt_flag,test_drive_auto_fallbacks_to_direct_when_daemon_cannot_focus,test_drive_auto_fallback_can_be_disabled_by_env,test_drive_dry_run_direct,test_drive_direct_prefers_os_injector_profile,test_drive_direct_honors_os_profile_override,test_drive_direct_os_profile_requires_os_injector_when_not_available,test_drive_direct_os_profile_os_injector_error_no_fallback,test_drive_direct_falls_back_when_os_injector_fails,test_calibrate_auto_ide_resolves_from_running_processes,test_calibrate_writes_profile_from_mouse,test_session_start_explicit_ides,test_session_start_keeps_profile_when_smoke_fails,test_session_start_warns_on_duplicate_coordinates,test_ide_list_empty,test_ide_list_marks_focused_ide,test_doctor_json_output,test_doctor_fix_text_output,test_doctor_fix_json_output,test_install_plugin_dry_run_auto_detect_from_term_program,test_install_plugin_auto_detect_ambiguous_running_ides_errors,test_install_plugin_exec_success_json_payload,test_status_when_no_daemon,test_shutdown_when_no_daemon,test_handoff_dry_run_prints_brief_and_skips_daemon,test_handoff_requires_running_daemon,test_handoff_drives_brief_through_client,_write_audit_log,test_tail_text_format_renders_entries,test_tail_json_format_returns_array,test_tail_n_limits_output,test_tail_missing_log_errors_cleanly,test_tail_skips_malformed_lines,test_install_unit_print_renders_execstart,test_install_unit_writes_to_xdg_default_path,test_install_unit_refuses_overwrite_without_force,test_resolve_koru_bin_falls_back_to_sys_executable_sibling
    test_autopilot_parser_requires_action()
    test_drive_without_daemon_errors(capsys;tmp_path)
    test_drive_missing_text_errors(capsys)
    test_drive_prompt_flag(monkeypatch;capsys)
    test_drive_auto_fallbacks_to_direct_when_daemon_cannot_focus(monkeypatch;capsys)
    test_drive_auto_fallback_can_be_disabled_by_env(monkeypatch;capsys)
    test_drive_dry_run_direct(capsys;monkeypatch)
    test_drive_direct_prefers_os_injector_profile(capsys;monkeypatch)
    test_drive_direct_honors_os_profile_override(capsys;monkeypatch)
    test_drive_direct_os_profile_requires_os_injector_when_not_available(capsys;monkeypatch)
    test_drive_direct_os_profile_os_injector_error_no_fallback(capsys;monkeypatch)
    test_drive_direct_falls_back_when_os_injector_fails(capsys;monkeypatch)
    test_calibrate_auto_ide_resolves_from_running_processes(capsys;monkeypatch;tmp_path)
    test_calibrate_writes_profile_from_mouse(capsys;monkeypatch;tmp_path)
    test_session_start_explicit_ides(capsys;monkeypatch;tmp_path)
    test_session_start_keeps_profile_when_smoke_fails(capsys;monkeypatch;tmp_path)
    test_session_start_warns_on_duplicate_coordinates(capsys;monkeypatch;tmp_path)
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
    e: _patch_no_running_ides,_daemon,_connect_plugin,_assert_no_more_data,running_daemon,test_ping_round_trip,test_is_running_true_when_daemon_alive,test_drive_falls_back_to_injector_when_no_plugin,test_drive_require_plugin_blocks_keyboard_fallback,test_drive_reports_injector_failure,test_drive_uses_os_injector_when_profile_available,test_drive_os_injector_skipped_when_env_disabled,test_drive_os_injector_forced_without_profile_falls_back_to_keyboard,test_drive_empty_text_returns_error,test_drive_unknown_type_returns_error,test_status_reports_socket_and_plugins,test_accept_rejects_foreign_peer_uid,test_plugin_hello_then_drive_forwards,test_visible_typing_prefers_keyboard_even_when_plugin_connected,test_plugin_ack_with_shutdown_info_is_relayed,test_plugin_ack_submit_failure_uses_os_fallback,test_default_handoff_builds_brief_for_uninitialised_project,test_session_ended_triggers_handoff_chat_send,test_session_ended_no_handoff_when_disabled,test_session_ended_skipped_during_cooldown,test_session_started_event_just_acks,test_shutdown_stops_daemon,_StubInjector,_LineReader,_DaemonHarness
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
    test_drive_require_plugin_blocks_keyboard_fallback(running_daemon)
    test_drive_reports_injector_failure(tmp_path;monkeypatch)
    test_drive_uses_os_injector_when_profile_available(tmp_path;monkeypatch)
    test_drive_os_injector_skipped_when_env_disabled(tmp_path;monkeypatch)
    test_drive_os_injector_forced_without_profile_falls_back_to_keyboard(tmp_path;monkeypatch)
    test_drive_empty_text_returns_error(running_daemon)
    test_drive_unknown_type_returns_error(running_daemon)
    test_status_reports_socket_and_plugins(running_daemon)
    test_accept_rejects_foreign_peer_uid(tmp_path;monkeypatch)
    test_plugin_hello_then_drive_forwards(tmp_path;monkeypatch)
    test_visible_typing_prefers_keyboard_even_when_plugin_connected(tmp_path;monkeypatch)
    test_plugin_ack_with_shutdown_info_is_relayed(tmp_path;monkeypatch)
    test_plugin_ack_submit_failure_uses_os_fallback(tmp_path;monkeypatch)
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
    e: fake_proc,test_detect_running_ides_finds_windsurf_and_jetbrains,test_detect_running_ides_deduplicates_same_ide,test_detect_running_ides_prefers_primary_windsurf_over_devin_helper,test_detect_running_ides_skips_unknown_processes,test_pick_target_prefers_user_choice,test_pick_target_returns_none_when_pref_not_running,test_pick_target_defaults_to_first,test_pick_target_prefers_koru_autopilot_ide_env,test_pick_target_ignores_koru_autopilot_ide_env_when_not_running,test_pick_target_empty_list_returns_none,test_detect_focused_ide_id_from_active_pid,test_detect_focused_ide_id_returns_none_for_unknown_pid,test_focused_ide_returns_matching_instance,test_pick_target_prefers_focused_when_no_explicit_prefer,test_pick_target_explicit_prefer_beats_focus,test_resolve_drive_target_auto_picks_first_ide_with_profile,test_detect_terminal_host_ide_id_cursor_env,test_detect_terminal_host_ide_id_cursor_beats_windsurf_token,test_detect_terminal_host_ide_id_vscode_nls_without_pid,test_pick_target_prefers_terminal_host_over_signature_order,test_resolve_drive_target_terminal_without_profile_skips_other_profiles,test_resolve_drive_target_auto_prefers_focused_when_it_has_profile,test_detect_cached_uses_cache_within_ttl,test_detect_cached_ttl_zero_always_refreshes,test_clear_detect_cache_forces_refresh
    fake_proc(tmp_path;monkeypatch)
    test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc)
    test_detect_running_ides_deduplicates_same_ide(fake_proc)
    test_detect_running_ides_prefers_primary_windsurf_over_devin_helper(tmp_path;monkeypatch)
    test_detect_running_ides_skips_unknown_processes(fake_proc)
    test_pick_target_prefers_user_choice(fake_proc)
    test_pick_target_returns_none_when_pref_not_running(fake_proc)
    test_pick_target_defaults_to_first(fake_proc;monkeypatch)
    test_pick_target_prefers_koru_autopilot_ide_env(fake_proc;monkeypatch)
    test_pick_target_ignores_koru_autopilot_ide_env_when_not_running(fake_proc;monkeypatch)
    test_pick_target_empty_list_returns_none()
    test_detect_focused_ide_id_from_active_pid(fake_proc)
    test_detect_focused_ide_id_returns_none_for_unknown_pid(fake_proc)
    test_focused_ide_returns_matching_instance(fake_proc)
    test_pick_target_prefers_focused_when_no_explicit_prefer(fake_proc)
    test_pick_target_explicit_prefer_beats_focus(fake_proc)
    test_resolve_drive_target_auto_picks_first_ide_with_profile(fake_proc;monkeypatch)
    test_detect_terminal_host_ide_id_cursor_env(monkeypatch)
    test_detect_terminal_host_ide_id_cursor_beats_windsurf_token(monkeypatch)
    test_detect_terminal_host_ide_id_vscode_nls_without_pid(monkeypatch)
    test_pick_target_prefers_terminal_host_over_signature_order(fake_proc;monkeypatch)
    test_resolve_drive_target_terminal_without_profile_skips_other_profiles(fake_proc;monkeypatch)
    test_resolve_drive_target_auto_prefers_focused_when_it_has_profile(fake_proc;monkeypatch)
    test_detect_cached_uses_cache_within_ttl(monkeypatch)
    test_detect_cached_ttl_zero_always_refreshes(monkeypatch)
    test_clear_detect_cache_forces_refresh(monkeypatch)
  tests/test_autopilot_injector.py:
    e: _fake_runner,_which_factory,test_select_backend_x11_prefers_xdotool,test_select_backend_wayland_prefers_wtype_over_ydotool,test_select_backend_wayland_falls_back_to_ydotool,test_select_backend_no_tools_returns_none,test_type_text_dry_run_does_not_call_runner,test_type_text_xdotool_types_and_submits,test_type_text_xdotool_supports_extra_enter,test_type_text_ydotool_uses_configurable_enter_key,test_type_text_ydotool_submit_newline_mode,test_type_text_ydotool_submit_ctrl_enter_mode,test_type_text_wtype_uses_modifiers_for_jetbrains,test_type_text_no_submit_only_types,test_type_text_propagates_runner_error,test_type_text_empty_raises,test_type_text_no_backend_raises,test_probe_marks_unavailable_when_missing_tool,test_probe_marks_unavailable_on_wrong_session,test_wtype_rejects_multi_modifier_submit_key,test_type_text_wayland_falls_back_when_wtype_fails,test_injector_forced_backend,test_wtype_single_modifier_still_works
    _fake_runner(commands)
    _which_factory(present)
    test_select_backend_x11_prefers_xdotool()
    test_select_backend_wayland_prefers_wtype_over_ydotool()
    test_select_backend_wayland_falls_back_to_ydotool()
    test_select_backend_no_tools_returns_none()
    test_type_text_dry_run_does_not_call_runner()
    test_type_text_xdotool_types_and_submits()
    test_type_text_xdotool_supports_extra_enter(monkeypatch)
    test_type_text_ydotool_uses_configurable_enter_key(monkeypatch)
    test_type_text_ydotool_submit_newline_mode(monkeypatch)
    test_type_text_ydotool_submit_ctrl_enter_mode(monkeypatch)
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
  tests/test_autopilot_jetbrains_scaffold.py:
    e: test_jetbrains_plugin_scaffold_files_exist,test_jetbrains_plugin_metadata_wires_service_and_action,test_jetbrains_plugin_readme_no_longer_stub
    test_jetbrains_plugin_scaffold_files_exist()
    test_jetbrains_plugin_metadata_wires_service_and_action()
    test_jetbrains_plugin_readme_no_longer_stub()
  tests/test_autopilot_os_injector.py:
    e: test_save_and_load_profile,test_load_profile_accepts_legacy_window_id,test_profile_from_mouse_builds_profile,test_capture_from_xdotool_parses_shell_output,test_inject_with_profile_paste_path_uses_clipboard_then_ctrl_v,test_inject_with_profile_type_fallback_when_no_clip_tools,test_load_profile_missing_raises,test_inject_with_profile_paste_timeout_is_reported,test_try_load_profile_prefers_project_over_cwd,test_iter_config_paths_dedupes_project_and_cwd,test_try_drive_with_profile_uses_saved_profile_on_wayland,test_try_drive_with_profile_forced_works_on_wayland,test_try_drive_with_profile_skips_when_env_disabled,test_try_drive_with_profile_uses_config,test_inject_post_focus_delay_env_controls_sleep,test_inject_post_focus_delay_zero_skips_sleep
    test_save_and_load_profile(tmp_path)
    test_load_profile_accepts_legacy_window_id(tmp_path)
    test_profile_from_mouse_builds_profile()
    test_capture_from_xdotool_parses_shell_output(monkeypatch)
    test_inject_with_profile_paste_path_uses_clipboard_then_ctrl_v(monkeypatch)
    test_inject_with_profile_type_fallback_when_no_clip_tools(monkeypatch)
    test_load_profile_missing_raises(tmp_path)
    test_inject_with_profile_paste_timeout_is_reported(monkeypatch)
    test_try_load_profile_prefers_project_over_cwd(tmp_path;monkeypatch)
    test_iter_config_paths_dedupes_project_and_cwd(tmp_path)
    test_try_drive_with_profile_uses_saved_profile_on_wayland(tmp_path;monkeypatch)
    test_try_drive_with_profile_forced_works_on_wayland(tmp_path;monkeypatch)
    test_try_drive_with_profile_skips_when_env_disabled(monkeypatch)
    test_try_drive_with_profile_uses_config(tmp_path;monkeypatch)
    test_inject_post_focus_delay_env_controls_sleep(monkeypatch)
    test_inject_post_focus_delay_zero_skips_sleep(monkeypatch)
  tests/test_autopilot_plugin_installer.py:
    e: test_resolve_target_ide_prefers_autopilot_env,test_resolve_target_ide_uses_running_supported_ide,test_resolve_target_ide_uses_integrated_terminal_hint,test_install_plugin_dry_run_builds_editor_command,test_install_plugin_configures_socket_path,test_install_plugin_targets_vscodium_from_integrated_terminal,test_install_plugin_skips_when_extension_already_installed
    test_resolve_target_ide_prefers_autopilot_env(monkeypatch)
    test_resolve_target_ide_uses_running_supported_ide(monkeypatch)
    test_resolve_target_ide_uses_integrated_terminal_hint(monkeypatch)
    test_install_plugin_dry_run_builds_editor_command(tmp_path;monkeypatch)
    test_install_plugin_configures_socket_path(tmp_path;monkeypatch)
    test_install_plugin_targets_vscodium_from_integrated_terminal(tmp_path;monkeypatch)
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
    e: _tmp_git_project,_run_main,TestBareInvocation,TestDoctorDispatch,TestInitDispatch,TestInitAgentLaneDispatch,TestContextDispatch,TestBareEmitsMarkdown,TestTopologySubcommand,TestInitCiSubcommand,TestAutoMain,TestSubcommandDispatch
    TestBareInvocation: _parse(0),test_no_args_is_bare(0),test_project_only_is_bare(0),test_init_is_not_bare(0),test_init_skip_host_environment_flag(0),test_init_agent_lane_is_not_bare(0),test_doctor_is_not_bare(0),test_context_is_not_bare(0),test_queue_is_not_bare(0),test_watch_is_not_bare(0),test_bootstrap_is_not_bare(0),test_command_is_not_bare(0)  # ``koru`` with no action flag should route to markdown brief.
    TestDoctorDispatch: setUp(0),tearDown(0),test_doctor_default_is_text(0),test_doctor_json(0),test_doctor_fix_text_is_guidance_only(0),test_doctor_fix_json(0),test_doctor_exit_0_on_no_failures(0)  # --doctor uses text by default, json when --format json.
    TestInitDispatch: setUp(0),tearDown(0),test_init_creates_planfile(0),test_init_duplicate_rejected(0),test_init_agent_lane_none_skips_helpers(0)  # --init creates project scaffold.
    TestInitAgentLaneDispatch: setUp(0),tearDown(0),test_fails_without_planfile(0),test_ok_when_planfile_exists(0)  # --init-agent-lane refreshes shell helpers without full re-in
    TestContextDispatch: setUp(0),tearDown(0),test_context_json_default(0),test_context_markdown(0)  # --context emits JSON or markdown.
    TestBareEmitsMarkdown: setUp(0),tearDown(0),test_bare_produces_markdown(0)  # Bare ``koru`` should produce a markdown brief.
    TestTopologySubcommand: setUp(0),tearDown(0),test_topology_json_lists_components_and_pipelines(0),test_topology_disable_then_is_enabled_false(0),test_topology_enabled_components_for_pipeline(0)
    TestInitCiSubcommand: test_init_ci_exits_zero_with_paths(0)
    TestAutoMain: test_auto_main_stops_prior_and_injects_replace_existing(0),test_auto_main_allow_duplicate_skips_stop_and_replace_flag(0),test_subcommand_auto_routes_to_auto_main(0)  # ``koru auto`` stops prior loops and forwards ``--replace-exi
    TestSubcommandDispatch: test_table_contains_all_documented_subcommands(0),test_table_values_are_callables(0),test_each_subcommand_routes_to_its_handler(0),test_unknown_first_arg_falls_through_to_argparse(0),test_empty_argv_does_not_call_any_handler(0)  # R6: routing through ``_SUBCOMMANDS`` dispatch table.
    _tmp_git_project(prefix)
    _run_main()
  tests/test_context.py:
    e: _ok,_fail,_no_git,_init_planfile,TestBuildContext,TestMarkdownHandoff,TestProjectPipelineInHandoff,TestSetupRequired
    TestBuildContext: test_brief_with_runnable_ticket(0),test_autonomy_loop_brief_reads_telemetry_file(0),test_brief_when_queue_idle(0),test_brief_when_queue_idle_ticket_next_json_null(0),test_brief_when_planfile_errors(0),test_specific_ticket_uses_show(0),test_instructions_include_no_commit_rule(0),test_instructions_include_ci_command_when_set(0),test_self_service_includes_concrete_ticket_commands(0),test_brief_is_json_serialisable(0),test_files_in_scope_appear_in_instructions(0),test_fixture_tickets_are_skipped_by_default(0),test_real_ticket_picked_over_fixture_in_mixed_queue(0),test_include_fixtures_flag_brings_them_back(0),test_single_object_fixture_is_filtered(0),test_explicit_ticket_id_bypasses_fixture_filter(0),test_all_tickets_are_populated_from_list(0)
    TestMarkdownHandoff: test_renders_ticket_section(0),test_renders_policy_table(0),test_renders_idle_brief_without_crash(0)
    TestProjectPipelineInHandoff: test_context_includes_pipeline_when_koru_yaml_present(0),test_pipeline_absent_without_koru_yaml(0)
    TestSetupRequired: test_instructions_swap_to_setup_guide(0),test_self_service_exposes_init_only(0),test_environment_planfile_initialised_false(0),test_markdown_renders_setup_required_block(0)  # When planfile is not initialised, the brief must steer to ko
    _ok(stdout)
    _fail(stderr)
    _no_git(_project)
    _init_planfile(project)
  tests/test_dashboard_topology_post.py:
    e: test_apply_topology_post_update_rejects_non_object_components,test_apply_topology_post_update_applies_component_toggle
    test_apply_topology_post_update_rejects_non_object_components()
    test_apply_topology_post_update_applies_component_toggle(tmp_path)
  tests/test_docker_e2e.py:
    e: TestDockerE2E,TestDockerComposeIntegration
    TestDockerE2E: docker_image(0),test_project(1),test_docker_image_builds_successfully(1),test_koru_help_in_docker(1),test_koru_doctor_in_docker(1),test_koru_init_in_docker(1),test_task_creation_with_priority_in_docker(2),test_autonomous_mode_single_cycle_in_docker(2),test_priority_ordering_in_docker(2),test_external_tool_detection_in_docker(1),test_agent_detection_in_docker(1),test_full_workflow_in_docker(2)  # Test Koru functionality in Docker containers.
    TestDockerComposeIntegration: test_docker_compose_build(0),test_docker_compose_test_profile(0),test_docker_compose_deps_profile(0)  # Test Docker Compose integration.
  tests/test_docs_ide_control_surfaces.py:
    e: test_ide_control_surfaces_doc_exists_with_key_sections,test_ide_router_doc_links_to_ide_control_surfaces,test_ide_router_doc_links_mcp_and_autopilot,test_mcp_ide_flow_doc_links_to_ide_control_surfaces,test_autopilot_design_doc_links_to_ide_control_surfaces,test_agent_guide_links_to_ide_control_surfaces,test_readme_links_ide_control_surfaces
    test_ide_control_surfaces_doc_exists_with_key_sections()
    test_ide_router_doc_links_to_ide_control_surfaces()
    test_ide_router_doc_links_mcp_and_autopilot()
    test_mcp_ide_flow_doc_links_to_ide_control_surfaces()
    test_autopilot_design_doc_links_to_ide_control_surfaces()
    test_agent_guide_links_to_ide_control_surfaces()
    test_readme_links_ide_control_surfaces()
  tests/test_doctor.py:
    e: _scaffold,_run,_named,TestHappyPath,TestKoruProjectPipelineProbe,TestPlanfileCliVersionProbe,TestAutonomousEnvironDoctorIntegration,TestPlanfileBinary,TestPlanfileConfigCheck,TestSprintsCheck,TestPolicyYamlCheck,TestGitignoreCheck,TestCiCommandCheck,TestPytestCollectProbe,TestReportShape
    TestHappyPath: test_full_scaffold_passes_all_required_checks(0)
    TestKoruProjectPipelineProbe: test_warns_when_planfile_ok_but_koru_yaml_missing(0)
    TestPlanfileCliVersionProbe: test_parses_version_from_stderr(0)
    TestAutonomousEnvironDoctorIntegration: test_doctor_includes_autonomous_environ_check(0),test_doctor_fails_on_invalid_ticket_sources_env(0),test_warns_when_no_git(0)
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
    TestE2EScan: setUp(0),tearDown(0),_marker_fixture(0),test_scan_detects_todo_markers(0),test_scan_json_format(0),test_scan_with_limit(0),test_scan_clean_project_no_suggestions(0)  # koru scan detects project issues and suggests tickets.
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
  tests/test_gc_cli_helpers.py:
    e: test_gc_statuses_from_args_splits_csv,test_gc_result_to_json_shape,test_print_gc_text_report_empty
    test_gc_statuses_from_args_splits_csv()
    test_gc_result_to_json_shape()
    test_print_gc_text_report_empty(capsys)
  tests/test_ide_client.py:
    e: test_legacy_adapter_forwards_all_operations,test_build_legacy_ide_client_uses_autopilot_client,test_build_koruide_client_uses_koruide_package,test_build_ide_client_defaults_to_legacy,test_build_ide_client_can_select_koruide,test_build_ide_client_uses_env_when_backend_not_passed
    test_legacy_adapter_forwards_all_operations()
    test_build_legacy_ide_client_uses_autopilot_client(monkeypatch)
    test_build_koruide_client_uses_koruide_package(monkeypatch)
    test_build_ide_client_defaults_to_legacy(monkeypatch)
    test_build_ide_client_can_select_koruide(monkeypatch)
    test_build_ide_client_uses_env_when_backend_not_passed(monkeypatch)
  tests/test_ide_client_contract.py:
    e: _legacy_factory,_koruide_factory,test_contract_is_running,test_contract_drive,test_contract_status,test_contract_shutdown,_TransportStub
    _TransportStub: __init__(0),is_running(0),drive(1),status(0),shutdown(0)
    _legacy_factory(transport)
    _koruide_factory(transport)
    test_contract_is_running(factory)
    test_contract_drive(factory)
    test_contract_status(factory)
    test_contract_shutdown(factory)
  tests/test_ide_router.py:
    e: test_is_headless_false_minimal_env,test_is_headless_koru_headless_yes,test_is_headless_koru_headless_on,test_is_headless_koru_headless_false_explicit,test_is_headless_ide_mode_whitespace_case_insensitive,test_is_headless_ssh_empty_display_still_headless,test_resolve_ide_route_env_ide_case_insensitive,test_resolve_ide_route_headless_sets_primary_surface,test_resolve_ide_route_ide_shell_surface,test_ide_router_main_help_exits_zero,test_ide_router_main_unknown_flag_exits_nonzero,test_ide_router_main_bad_format_exits_nonzero,test_is_headless_ssh_without_display,test_is_headless_ssh_with_display_not_headless,test_is_headless_windows_ignores_ssh_without_display,test_resolve_ide_route_bad_env_uses_cli,test_resolve_ide_route_whitespace_env_treated_as_missing,test_resolve_ide_route_cli_invalid_env_empty_uses_auto,test_resolve_ide_route_cli_auto_env_empty,test_resolve_ide_route_headless_notes_mention_escape_hatch,test_resolve_ide_route_ide_shell_notes_mention_mcp,test_ide_router_main_json,test_ide_router_main_text,test_resolve_ide_route_env_overrides_cli,test_resolve_ide_route_auto_env_does_not_override_cli,test_resolve_ide_route_headless_forces_auto,test_resolve_ide_route_headless_allow_autopilot_honors_env,test_is_headless_via_ide_mode,test_resolve_ide_route_cli_ide_whitespace_normalized,test_resolve_ide_route_headless_allow_autopilot_yes_string,test_resolve_ide_route_environ_none_uses_os_environ,test_resolve_ide_route_headless_all_recommend_flags_false,test_ide_router_main_json_when_headless,test_resolve_ide_route_vscode_explicit_env
    test_is_headless_false_minimal_env()
    test_is_headless_koru_headless_yes()
    test_is_headless_koru_headless_on()
    test_is_headless_koru_headless_false_explicit()
    test_is_headless_ide_mode_whitespace_case_insensitive()
    test_is_headless_ssh_empty_display_still_headless()
    test_resolve_ide_route_env_ide_case_insensitive()
    test_resolve_ide_route_headless_sets_primary_surface()
    test_resolve_ide_route_ide_shell_surface()
    test_ide_router_main_help_exits_zero()
    test_ide_router_main_unknown_flag_exits_nonzero()
    test_ide_router_main_bad_format_exits_nonzero(monkeypatch)
    test_is_headless_ssh_without_display()
    test_is_headless_ssh_with_display_not_headless()
    test_is_headless_windows_ignores_ssh_without_display(monkeypatch)
    test_resolve_ide_route_bad_env_uses_cli()
    test_resolve_ide_route_whitespace_env_treated_as_missing()
    test_resolve_ide_route_cli_invalid_env_empty_uses_auto()
    test_resolve_ide_route_cli_auto_env_empty()
    test_resolve_ide_route_headless_notes_mention_escape_hatch()
    test_resolve_ide_route_ide_shell_notes_mention_mcp()
    test_ide_router_main_json(monkeypatch;capsys)
    test_ide_router_main_text(monkeypatch;capsys)
    test_resolve_ide_route_env_overrides_cli()
    test_resolve_ide_route_auto_env_does_not_override_cli()
    test_resolve_ide_route_headless_forces_auto()
    test_resolve_ide_route_headless_allow_autopilot_honors_env()
    test_is_headless_via_ide_mode()
    test_resolve_ide_route_cli_ide_whitespace_normalized()
    test_resolve_ide_route_headless_allow_autopilot_yes_string()
    test_resolve_ide_route_environ_none_uses_os_environ(monkeypatch)
    test_resolve_ide_route_headless_all_recommend_flags_false()
    test_ide_router_main_json_when_headless(monkeypatch;capsys)
    test_resolve_ide_route_vscode_explicit_env()
  tests/test_ide_runtime.py:
    e: test_build_host_setup_report_delegates_to_legacy_backend,test_detect_running_ides_normalizes_rows
    test_build_host_setup_report_delegates_to_legacy_backend(monkeypatch)
    test_detect_running_ides_normalizes_rows(monkeypatch)
  tests/test_ide_work.py:
    e: _ok,TestIdeWork
    TestIdeWork: test_fetch_next_open_ticket_sorts_by_priority(0),test_resolve_idle_drive_prompt_uses_ticket_when_open(0),test_resolve_idle_drive_prompt_falls_back_when_no_open(0),test_release_stale_in_progress_reopens_old_ticket(0),test_extract_ticket_id_from_text(0),test_build_ide_work_prompt_includes_description(0)
    _ok(stdout)
  tests/test_init.py:
    e: _detach_ci_env,_reattach_ci_env,TestStarterInit,TestForceAndConflicts,TestFromExternalPipeline,TestRuntimeContract,TestAgentLaneArtifacts,TestRefreshInitAgentLane
    TestStarterInit: test_creates_planfile_layout(0),test_writes_policy_stub_and_loads_safe_defaults(0),test_policy_stub_constant_is_valid_yaml(0),test_appends_gitignore_entry(0),test_gitignore_idempotent(0),test_preserves_existing_gitignore_content(0),test_policy_stub_not_overwritten_on_force(0),test_no_starter_yaml_left_behind(0),test_writes_koru_yaml_on_first_init(0),test_host_environment_bundle_written_by_default(0),test_host_environment_skipped_when_disabled(0),test_force_init_preserves_existing_koru_yaml(0)
    TestForceAndConflicts: test_re_init_without_force_raises(0),test_re_init_with_force_succeeds(0)
    TestFromExternalPipeline: test_imports_user_supplied_pipeline(0)
    TestRuntimeContract: test_init_does_not_leave_files_outside_planfile(0)
    TestAgentLaneArtifacts: test_auto_local_writes_shell_helpers(0),test_auto_cursor_when_dot_cursor(0),test_auto_vscode_when_dot_vscode(0),test_auto_cursor_beats_vscode_when_both(0),test_auto_prefers_persisted_shell_env_lane(0),test_auto_ci_forces_local_even_with_dot_cursor(0),test_none_skips_helpers(0)
    TestRefreshInitAgentLane: test_requires_planfile(0),test_writes_after_init_with_agent_lane_none(0)
    _detach_ci_env()
    _reattach_ci_env(backup)
  tests/test_koru_gate_capture.py:
    e: test_first_meaningful_line_skips_cloud_init_noise,test_first_meaningful_line_falls_back_to_nonempty_when_only_noise
    test_first_meaningful_line_skips_cloud_init_noise()
    test_first_meaningful_line_falls_back_to_nonempty_when_only_noise()
  tests/test_koru_queue_argv.py:
    e: test_build_queue_argv_apply_minimal,test_build_queue_argv_dry_and_max_steps
    test_build_queue_argv_apply_minimal(tmp_path)
    test_build_queue_argv_dry_and_max_steps(tmp_path)
  tests/test_koruapi.py:
    e: test_list_integrations_has_dsl_and_scan,test_dsl_roundtrip_invoke,test_unknown_integration,test_wired_handlers_are_catalogued,test_tool_list_tickets_status_filters,test_openapi_document_lists_invoke_path
    test_list_integrations_has_dsl_and_scan()
    test_dsl_roundtrip_invoke()
    test_unknown_integration()
    test_wired_handlers_are_catalogued()
    test_tool_list_tickets_status_filters(monkeypatch)
    test_openapi_document_lists_invoke_path()
  tests/test_koruapi_transports.py:
    e: test_build_serve_parser_defaults,test_integrations_include_gate_regix,test_mcp_main_version_exit
    test_build_serve_parser_defaults()
    test_integrations_include_gate_regix()
    test_mcp_main_version_exit()
  tests/test_korudsl.py:
    e: test_normalize_and_roundtrip,test_library_to_dsl_objectives
    test_normalize_and_roundtrip()
    test_library_to_dsl_objectives()
  tests/test_koruide_bridges.py:
    e: test_koruide_ide_bridge_exports_legacy_symbols,test_koruide_injector_bridge_exports_legacy_symbols,test_koruide_os_injector_bridge_exports_legacy_symbols,test_autopilot_daemon_shim_points_to_koruide_implementation,test_autopilot_audit_shim_points_to_koruide_implementation,test_autopilot_host_setup_shim_points_to_koruide_implementation,test_autopilot_plugin_installer_shim_points_to_koruide_implementation,test_autopilot_config_shim_points_to_koruide_implementation
    test_koruide_ide_bridge_exports_legacy_symbols()
    test_koruide_injector_bridge_exports_legacy_symbols()
    test_koruide_os_injector_bridge_exports_legacy_symbols()
    test_autopilot_daemon_shim_points_to_koruide_implementation()
    test_autopilot_audit_shim_points_to_koruide_implementation()
    test_autopilot_host_setup_shim_points_to_koruide_implementation()
    test_autopilot_plugin_installer_shim_points_to_koruide_implementation()
    test_autopilot_config_shim_points_to_koruide_implementation()
  tests/test_koruide_client.py:
    e: test_koruide_client_forwards_all_operations,test_build_client_sets_socket_path_and_timeout,test_injected_client_without_request_raises_on_request_path,test_drive_missing_socket_returns_ok_false
    test_koruide_client_forwards_all_operations()
    test_build_client_sets_socket_path_and_timeout()
    test_injected_client_without_request_raises_on_request_path()
    test_drive_missing_socket_returns_ok_false(tmp_path)
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
  tests/test_mcp_provision.py:
    e: test_detect_ides_uses_runtime_bridge,test_provision_cursor_dry_run_does_not_write,test_provision_cursor_writes_file_and_then_is_idempotent,test_provision_upgrades_bare_koru_command_to_absolute,test_remove_from_config_removes_koru_entry,test_init_ide_main_json_output_for_cursor_dry_run,test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command,test_ensure_koru_mcp_not_disabled_includes_global_windsurf
    test_detect_ides_uses_runtime_bridge(monkeypatch)
    test_provision_cursor_dry_run_does_not_write(tmp_path)
    test_provision_cursor_writes_file_and_then_is_idempotent(tmp_path)
    test_provision_upgrades_bare_koru_command_to_absolute(tmp_path;monkeypatch)
    test_remove_from_config_removes_koru_entry(tmp_path)
    test_init_ide_main_json_output_for_cursor_dry_run(capsys;tmp_path)
    test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command(tmp_path;monkeypatch)
    test_ensure_koru_mcp_not_disabled_includes_global_windsurf(tmp_path;monkeypatch)
  tests/test_mcp_server.py:
    e: test_initialize_message_returns_server_info,test_tools_list_includes_required_koru_tools,test_tools_call_unknown_tool_returns_error_payload,test_tool_job_status_unknown_job,test_run_ticket_invokes_queue_mode_without_ticket_flag,test_run_ticket_timeout_updates_job_status,test_run_ticket_error_updates_job_status,test_regix_gate_command_uses_workdir_not_project,test_redup_gate_command_uses_supported_cli_shape,test_job_store_is_ephemeral_across_imports,test_job_store_persists_to_disk_and_reloads
    test_initialize_message_returns_server_info()
    test_tools_list_includes_required_koru_tools()
    test_tools_call_unknown_tool_returns_error_payload()
    test_tool_job_status_unknown_job()
    test_run_ticket_invokes_queue_mode_without_ticket_flag(monkeypatch;tmp_path)
    test_run_ticket_timeout_updates_job_status(monkeypatch;tmp_path)
    test_run_ticket_error_updates_job_status(monkeypatch;tmp_path)
    test_regix_gate_command_uses_workdir_not_project(tmp_path)
    test_redup_gate_command_uses_supported_cli_shape(tmp_path)
    test_job_store_is_ephemeral_across_imports(tmp_path)
    test_job_store_persists_to_disk_and_reloads(tmp_path)
  tests/test_operator_pipeline.py:
    e: probe,test_build_operator_steps_mcp_pending_without_config,test_build_operator_steps_mcp_ok_when_configured,test_run_startup_operator_pipeline_creates_tickets,test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing,test_candidate_planfile_health_urls_use_serve_endpoint,test_run_startup_operator_pipeline_dedup_markers,test_run_startup_operator_pipeline_closes_resolved_marker_ticket
    probe(tmp_path)
    test_build_operator_steps_mcp_pending_without_config(tmp_path;probe)
    test_build_operator_steps_mcp_ok_when_configured(tmp_path;probe)
    test_run_startup_operator_pipeline_creates_tickets(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing(tmp_path;probe;monkeypatch)
    test_candidate_planfile_health_urls_use_serve_endpoint(tmp_path)
    test_run_startup_operator_pipeline_dedup_markers(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_closes_resolved_marker_ticket(tmp_path;probe;monkeypatch)
  tests/test_planfile_queue.py:
    e: _ok,_ticket_args,TestPlanfileQueue,TestPlanfileQueueLlm,TestPlanfileQueueLoop,TestAppendShellEvidenceNote
    TestPlanfileQueue: test_shell_ticket_runs_lifecycle_commands(0),test_ticket_claim_failure_returns_claim_failed(0),test_human_ticket_returns_waiting_input(0),test_shell_failure_marks_ticket_failed(0),test_api_ticket_runs_lifecycle_commands(0),test_api_failure_marks_ticket_failed(0),test_idle_when_planfile_returns_no_ticket(0),test_planfile_error_propagates(0),test_dry_run_returns_command_without_executing(0),test_unsupported_executor_kind(0),test_shell_ticket_without_command_auto_completes(0),test_scan_ticket_without_executor_waits_for_ide_prompt(0),test_api_ticket_without_endpoint_requests_input(0),test_interactive_human_ticket_completes_with_answer(0),test_interactive_human_ticket_cancellation_leaves_ticket(0),test_interactive_with_dry_run_does_not_prompt(0)
    TestPlanfileQueueLlm: _llm_ticket(0),test_llm_ticket_runs_lifecycle_commands(0),test_llm_ticket_failure_marks_failed(0),test_llm_ticket_without_prompt_requests_input(0),test_llm_dry_run_returns_request_without_calling(0),test_llm_default_runner_without_api_key_returns_clear_error(0)  # Tests for the executor.kind=llm path.
    TestPlanfileQueueLoop: _make_runner(1),test_loop_drains_three_shell_tickets_to_idle(0),test_loop_breaks_on_waiting_input_without_interactive(0),test_loop_continues_past_failed_ticket(0),test_loop_respects_max_iterations_cap(0),test_loop_with_interactive_drains_human_tickets(0),test_loop_validates_max_iterations(0)  # Tests for run_planfile_queue_loop — the queue-draining drive
    TestAppendShellEvidenceNote: test_short_flag_when_long_option_unsupported(0),test_artifact_when_both_note_flags_missing(0)  # Regression: planfile CLIs without ``--note`` still persist s
    _ok(stdout)
    _ticket_args(command)
  tests/test_policy.py:
    e: _write_policy,TestDefaults,TestLoad,TestViolations
    TestDefaults: test_defaults_are_strict(0),test_default_forbidden_paths_include_critical(0),test_default_shell_patterns_include_critical(0),test_to_dict_keys_are_sorted(0)
    TestLoad: test_missing_file_returns_defaults(0),test_malformed_yaml_falls_back_to_defaults(0),test_top_level_non_mapping_falls_back_to_defaults(0),test_string_truthy_value_is_rejected(0),test_explicit_loosening_is_honoured(0),test_zero_or_negative_timeout_falls_back_to_default(0),test_unknown_keys_are_ignored(0)
    TestViolations: test_git_commit_blocked_by_default(0),test_git_push_blocked_by_default(0),test_force_push_double_flag(0),test_branch_create_blocked(0),test_rm_rf_root_blocked(0),test_safe_command_passes(0),test_empty_command_passes(0),test_loosened_policy_allows_commit(0),test_path_helper_resolves(0)
    _write_policy(project;content)
  tests/test_post_run_verify.py:
    e: _ok,_fail,_State,TestPostRunVerify
    _State:
    TestPostRunVerify: test_load_from_koru_yaml(0),test_verify_reopens_on_failure(0),test_verify_after_ide_work_pending_done(0),test_fetch_recently_done_ticket_ids(0),test_run_verify_commands_success(0)
    _ok(stdout)
    _fail(stderr)
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
  tests/test_queue_cli_helpers.py:
    e: test_queue_status_marker_known_status,test_queue_loop_exit_code_success,test_single_task_ticket_lists,test_emit_queue_run_started_does_not_raise
    test_queue_status_marker_known_status()
    test_queue_loop_exit_code_success()
    test_single_task_ticket_lists()
    test_emit_queue_run_started_does_not_raise()
  tests/test_refactor_planfile_handoff.py:
    e: test_render_handoff_mentions_analysis_paths,test_render_handoff_notes_when_analysis_present
    test_render_handoff_mentions_analysis_paths(tmp_path)
    test_render_handoff_notes_when_analysis_present(tmp_path)
  tests/test_regix_taskfile.py:
    e: test_quality_regix_uses_current_regix_gates_command
    test_quality_regix_uses_current_regix_gates_command()
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
    e: _ok,_marker_fixture,TestScanPytestCollect,TestScanTodoMarkers,TestScanMissingGates,TestScanMissingTools,TestScanGitignoreDrift,TestRunScan,TestScanSemcodArtifacts
    TestScanPytestCollect: test_returns_empty_when_no_tests_and_no_pyproject(0),test_empty_on_clean_collect(0),test_parses_per_file_collection_errors(0),test_falls_back_to_umbrella_import_ticket(0),test_collection_timeout_emits_diagnostic_ticket(0),test_timeout_value_is_reflected_in_ticket(0),test_pytest_not_installed_stays_silent(0)
    TestScanTodoMarkers: test_filters_files_below_threshold(0),test_groups_markers_per_file(0),test_respects_koruignore_file_glob(0),test_respects_koruignore_directory_prefix(0)
    TestScanMissingGates: test_no_suggestions_when_tool_missing(0),test_skips_when_config_already_present(0)
    TestScanMissingTools: test_no_pyproject_returns_empty(0),test_skips_tools_not_in_registry(0)
    TestScanGitignoreDrift: test_no_gitignore_returns_empty(0),test_present_entry_skips_suggestion(0),test_missing_entry_suggests(0)
    TestRunScan: test_dry_run_returns_suggestions_no_apply(0),test_apply_creates_tickets_and_skips_duplicates(0),test_apply_create_failure_is_skipped(0),test_apply_creates_human_executor_tickets_without_custom_runner(0),test_apply_uses_stable_title_and_deduplicates_by_signal(0),test_apply_deduplicates_planfile_source_tool_payload(0),test_existing_scan_titles_ignores_done_tickets(0),test_limit_caps_suggestions(0),test_priority_ordering_critical_first(0)
    TestScanSemcodArtifacts: test_jscpd_report_emits_when_duplicates(0),test_code2llm_analysis_emits_when_god_rows(0),test_code2llm_analysis_emits_dup_ticket(0),test_code2llm_analysis_emits_cc_ticket(0),test_code2llm_analysis_emits_refactor_items(0),test_testql_export_emits_when_many_failures(0),test_redup_filtered_emits_when_many_groups(0),test_redup_changed_emits_when_wup_scan_has_groups(0)
    _ok(stdout;returncode;stderr)
    _marker_fixture()
  tests/test_semcod_tools.py:
    e: test_detect_semcod_tools_covers_core_semcod_extensions,test_detect_semcod_tools_marks_pyproject_config_without_binary
    test_detect_semcod_tools_covers_core_semcod_extensions(tmp_path)
    test_detect_semcod_tools_marks_pyproject_config_without_binary(tmp_path)
  tests/test_serve.py:
    e: _minimal_planfile_project,_free_port,_start,_get,_post_json,test_cmdline_suggests_koru_serve_from_bytes,test_bulk_waiting_input_action_approve,test_bulk_waiting_input_action_reject,test_start_serve_background_shutdown,TestServe,TestServeAutoPort,TestServeReplacePrior
    TestServe: setUp(0),tearDown(0),test_health_endpoint(0),test_dashboard_html_served_on_root(0),test_api_context_returns_brief(0),test_api_handoff_returns_markdown(0),test_api_topology_returns_components_and_pipelines(0),test_api_topology_post_persists_toggle(0),test_api_topology_post_rejects_empty_update(0),test_unknown_path_returns_404(0)
    TestServeAutoPort: test_auto_port_skips_busy_port(0),test_without_auto_port_busy_raises(0)
    TestServeReplacePrior: test_bind_retries_after_prior_listener_stopped(0)
    _minimal_planfile_project()
    _free_port()
    _start(project;port)
    _get(port;path)
    _post_json(port;path;payload)
    test_cmdline_suggests_koru_serve_from_bytes()
    test_bulk_waiting_input_action_approve()
    test_bulk_waiting_input_action_reject()
    test_start_serve_background_shutdown()
  tests/test_shell_evidence.py:
    e: test_format_shell_run_note_includes_meta_and_streams,test_format_shell_run_note_truncates_long_stdout,test_format_shell_run_note_hard_total_cap
    test_format_shell_run_note_includes_meta_and_streams()
    test_format_shell_run_note_truncates_long_stdout()
    test_format_shell_run_note_hard_total_cap()
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
  tests/test_topology_cli.py:
    e: test_render_topology_text_includes_components_and_pipelines
    test_render_topology_text_includes_components_and_pipelines()
  tests/test_watch.py:
    e: FakeWebSocket,TestWatch
    FakeWebSocket: __init__(1),__aenter__(0),__aexit__(0),recv(0)
    TestWatch: test_format_queue_event_for_execution_change(0),test_format_management_event(0),test_watch_planfile_events_prints_compact_lines(0)
  tests/test_wup_taskfile.py:
    e: test_quality_wup_checks_status_and_respects_topology_gate,test_operator_pipeline_taskfile_commands_exist,test_wup_yaml_is_bootstrapped_for_koru_project
    test_quality_wup_checks_status_and_respects_topology_gate()
    test_operator_pipeline_taskfile_commands_exist()
    test_wup_yaml_is_bootstrapped_for_koru_project()
```

## Call Graph

*446 nodes · 500 edges · 71 modules · CC̄=4.4*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 282 | 0 | **282** |
| `run_cycle` *(in src.koru.autonomous_cycle)* | 89 ⚠ | 0 | 168 | **168** |
| `_build_handler` *(in src.koruapi.dashboard_serve)* | 1 | 1 | 82 | **83** |
| `_action_up` *(in src.koru.autonomous)* | 50 ⚠ | 1 | 77 | **78** |
| `_build_parser` *(in src.koru.autonomous)* | 1 | 1 | 64 | **65** |
| `detect_agent_options` *(in src.koru.agents)* | 16 ⚠ | 3 | 61 | **64** |
| `create_nl_task` *(in src.koru.tasks)* | 23 ⚠ | 6 | 47 | **53** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 5 | 47 | **52** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.35s
# nodes: 446 | edges: 500 | modules: 71
# CC̄=4.4

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:282  out:0  total:282
  src.koru.autonomous_cycle.run_cycle
    CC=89  in:0  out:168  total:168
  src.koruapi.dashboard_serve._build_handler
    CC=1  in:1  out:82  total:83
  src.koru.autonomous._action_up
    CC=50  in:1  out:77  total:78
  src.koru.autonomous._build_parser
    CC=1  in:1  out:64  total:65
  src.koru.agents.detect_agent_options
    CC=16  in:3  out:61  total:64
  src.koru.tasks.create_nl_task
    CC=23  in:6  out:47  total:53
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:47  total:52
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=11  in:0  out:46  total:46
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.activity_log.activity
    CC=4  in:32  out:7  total:39
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.autonomous._stdio_info
    CC=1  in:31  out:1  total:32
  src.koru.events.emit_management_event
    CC=8  in:25  out:7  total:32
  src.koru.autonomy.post_run_verify.load_post_run_verify_config
    CC=19  in:1  out:31  total:32
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  src.koru.local_service._build_handler
    CC=1  in:1  out:30  total:31
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koru.tools.detect_tools
    CC=26  in:1  out:25  total:26
  src.koruide.ide.detect_running_ides
    CC=13  in:16  out:10  total:26

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [2 funcs]
    connect  CC=2  out:7
    next  CC=2  out:1
  scripts.koru-soak-monitor  [1 funcs]
    print  CC=0  out:0
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
  src.koru.activity_log  [2 funcs]
    activity  CC=4  out:7
    activity_info  CC=5  out:11
  src.koru.agent_backends  [6 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    list_agent_backend_ids  CC=2  out:1
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.agent_cli_helpers  [3 funcs]
    print_agent_list  CC=10  out:7
    run_agent_handoff  CC=3  out:10
    try_agent_env_exports  CC=7  out:7
  src.koru.agents  [7 funcs]
    agent_lane_environment  CC=1  out:3
    detect_agent_options  CC=16  out:61
    format_agent_lane_exports  CC=2  out:6
    launch_agent  CC=4  out:8
    normalize_agent_lane_id  CC=6  out:8
    save_agent_prompt  CC=1  out:3
    select_agent  CC=14  out:8
  src.koru.autonomous  [28 funcs]
    _action_up  CC=50  out:77
    _ancestor_pids  CC=7  out:8
    _apply_agent_lane_environ  CC=3  out:3
    _as_managed  CC=1  out:1
    _build_parser  CC=1  out:64
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _create_diagnostic_ticket  CC=2  out:8
    _daemon_activity_log  CC=2  out:3
    _ensure_init  CC=4  out:3
  src.koru.autonomous_cycle  [9 funcs]
    _autopilot_event_path  CC=1  out:2
    _create_diagnostic_ticket  CC=2  out:6
    _drain_autopilot_events  CC=6  out:8
    _is_topology_enabled  CC=4  out:2
    _queue_loop_waiting_ticket_label  CC=3  out:1
    _run_command_check  CC=2  out:4
    _run_idle_diagnostics  CC=1  out:3
    _stdio_info  CC=1  out:1
    run_cycle  CC=89  out:168
  src.koru.autonomous_parser  [1 funcs]
    looks_like_autonomous_up_command  CC=15  out:8
  src.koru.autonomous_startup  [6 funcs]
    _terminal_agent_lane_from_env  CC=5  out:4
    build_startup_probe  CC=8  out:21
    format_startup_banner  CC=5  out:8
    koru_distribution_version  CC=2  out:1
    resolve_agent_lane_id  CC=11  out:11
    resolve_autopilot_ide_for_autonomous  CC=4  out:4
  src.koru.autonomy.env  [1 funcs]
    env_truthy  CC=3  out:3
  src.koru.autonomy.ide_work  [1 funcs]
    resolve_in_progress_stale_minutes  CC=10  out:9
  src.koru.autonomy.post_run_verify  [2 funcs]
    load_post_run_verify_config  CC=19  out:31
    verify_after_ide_work  CC=13  out:7
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.bootstrap  [9 funcs]
    _detect_cycle  CC=10  out:13
    _validate_cross_task_dependencies  CC=10  out:13
    _validate_id  CC=4  out:6
    _validate_name  CC=4  out:5
    _validate_task  CC=3  out:15
    import_flat_pipeline  CC=9  out:12
    load_flat_pipeline  CC=9  out:12
    materialize_to_planfile  CC=6  out:16
    validate_flat_pipeline  CC=3  out:9
  src.koru.context  [20 funcs]
    _auto_promote_blocking_tickets  CC=4  out:5
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_ticket_args  CC=3  out:1
    _extract_error_from_stderr  CC=7  out:4
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=18  out:15
    _is_fixture_ticket  CC=4  out:6
    _load_project_dotenv  CC=3  out:2
    _load_sprint_data  CC=6  out:4
  src.koru.doctor  [13 funcs]
    _check_agent_backends_registry  CC=1  out:3
    _check_ci_command  CC=5  out:6
    _check_koru_project_pipeline  CC=7  out:9
    _check_planfile_cli_version  CC=9  out:9
    _check_planfile_config  CC=4  out:7
    _check_planfile_sprints  CC=10  out:17
    _check_planfile_sprints_yaml  CC=6  out:8
    _check_policy_yaml  CC=11  out:13
    _check_pytest_collect  CC=8  out:6
    _check_runtime_dir  CC=6  out:6
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
  src.koru.gc_cli_helpers  [4 funcs]
    emit_gc_management_event  CC=2  out:3
    gc_result_to_json  CC=3  out:1
    print_gc_report  CC=2  out:4
    print_gc_text_report  CC=12  out:14
  src.koru.ide_client  [5 funcs]
    drive  CC=1  out:8
    adapt_legacy_autopilot_client  CC=1  out:1
    build_ide_client  CC=3  out:5
    build_koruide_client  CC=1  out:1
    build_legacy_ide_client  CC=1  out:2
  src.koru.ide_router  [2 funcs]
    is_headless_environment  CC=8  out:6
    resolve_ide_route  CC=8  out:9
  src.koru.ide_runtime  [2 funcs]
    build_host_setup_report  CC=1  out:1
    detect_running_ides  CC=5  out:12
  src.koru.init  [11 funcs]
    _ensure_gitignore_entry  CC=8  out:12
    _init_auto_agent_lane  CC=6  out:7
    _read_persisted_agent_lane  CC=12  out:20
    _remove_agent_lane_artifacts  CC=5  out:3
    _resolve_init_agent_lane  CC=4  out:4
    _write_agent_lane_artifacts  CC=2  out:10
    _write_autopilot_host_setup_script  CC=1  out:5
    _write_policy_stub_if_absent  CC=3  out:6
    init_project  CC=8  out:22
    refresh_init_agent_lane  CC=4  out:11
  src.koru.init_host_environment  [1 funcs]
    write_host_environment_bundle  CC=2  out:12
  src.koru.local_service  [8 funcs]
    _build_handler  CC=1  out:30
    _env_int  CC=3  out:3
    _koru_version  CC=2  out:1
    _read_bounded_json_object  CC=7  out:6
    build_local_service_server  CC=1  out:4
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:11
    start_local_service_background  CC=1  out:4
  src.koru.loop  [2 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
  src.koru.mcp_provision  [21 funcs]
    _apply_target  CC=4  out:5
    _cursor_project_config  CC=1  out:0
    _koru_mcp_entry  CC=1  out:1
    _koru_mcp_entry_cursor  CC=1  out:1
    _maybe_upgrade_koru_command  CC=5  out:3
    _read_json  CC=3  out:3
    _removal_paths_for_ide  CC=4  out:4
    _render_results  CC=5  out:8
    _resolve_targets  CC=4  out:4
    _resolved_koru_command  CC=2  out:1
  src.koru.policy  [2 funcs]
    load_policy  CC=9  out:43
    policy_path  CC=1  out:1
  src.koru.project_pipeline  [3 funcs]
    build_project_pipeline_brief  CC=9  out:14
    project_pipeline_path  CC=1  out:1
    write_koru_project_pipeline_if_absent  CC=2  out:5
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=12  out:8
  src.koru.queue.runners  [1 funcs]
    run_process  CC=1  out:2
  src.koru.queue.ticket  [1 funcs]
    planfile_command  CC=3  out:4
  src.koru.queue_clean  [11 funcs]
    _build_close_note  CC=1  out:4
    _candidate_from_ticket  CC=6  out:9
    _cleanable_statuses  CC=2  out:1
    _close_ticket  CC=5  out:6
    _list_tickets  CC=11  out:11
    _matched_rules  CC=14  out:16
    _maybe_skip_active_ticket  CC=3  out:3
    _parse_age_days  CC=8  out:10
    _planfile_base  CC=4  out:3
    clean_queue  CC=5  out:7
  src.koru.run_log  [1 funcs]
    _emit  CC=3  out:5
  src.koru.runtime  [4 funcs]
    ensure_runs_dir  CC=2  out:5
    planfile_dir  CC=1  out:1
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=23  out:47
  src.koru.tools  [7 funcs]
    _first_token  CC=2  out:1
    build_tool_task_scaffold  CC=16  out:21
    default_registry_path  CC=1  out:2
    detect_tools  CC=26  out:25
    infer_adapter_kind  CC=5  out:4
    load_tool_registry  CC=11  out:13
    resolve_registry_path  CC=4  out:7
  src.koru.topology  [5 funcs]
    is_component_enabled  CC=3  out:6
    is_pipeline_enabled  CC=3  out:6
    load_topology  CC=1  out:9
    save_topology  CC=1  out:6
    set_component_enabled  CC=1  out:1
  src.koru.utils.subprocess_runner  [2 funcs]
    get_python_cmd  CC=3  out:3
    resolve_planfile_subpath  CC=1  out:3
  src.koru.watch  [5 funcs]
    _format_connected_event  CC=1  out:0
    _format_management_event  CC=9  out:16
    _format_ticket_event  CC=9  out:20
    format_queue_event  CC=5  out:6
    watch_planfile_events  CC=7  out:7
  src.koru.wup_testql_compat  [4 funcs]
    _normalize_args  CC=6  out:14
    _normalize_timeout  CC=4  out:7
    _real_testql  CC=5  out:9
    main  CC=2  out:4
  src.koruapi.cli  [2 funcs]
    _build_parser  CC=2  out:15
    main  CC=11  out:20
  src.koruapi.dashboard  [3 funcs]
    _env_truthy  CC=1  out:3
    build_serve_parser  CC=1  out:10
    dashboard_main  CC=5  out:9
  src.koruapi.dashboard_serve  [16 funcs]
    _address_in_use  CC=4  out:4
    _build_handler  CC=1  out:82
    _bulk_waiting_input_action  CC=13  out:14
    _cmdline_suggests_koru_serve  CC=3  out:3
    _cmdline_suggests_koru_serve_from_bytes  CC=3  out:7
    _list_tickets  CC=9  out:6
    _listener_pids_for_tcp_port  CC=7  out:7
    _try_stop_prior_koru_serve_listener  CC=12  out:13
    apply_topology_post_update  CC=14  out:22
    bind_serve_server  CC=11  out:10
  src.koruapi.integrations  [2 funcs]
    get_integration  CC=1  out:1
    list_integrations  CC=4  out:2
  src.koruapi.invoke  [1 funcs]
    invoke_integration  CC=4  out:6
  src.koruapi.invoke_handlers  [15 funcs]
    _handle_autopilot_drive  CC=5  out:17
    _handle_autopilot_status  CC=2  out:3
    _handle_context_build  CC=1  out:3
    _handle_doctor_run  CC=1  out:2
    _handle_dsl_roundtrip  CC=3  out:6
    _handle_dsl_to_dsl  CC=2  out:3
    _handle_dsl_to_library  CC=3  out:4
    _handle_gate_regix  CC=3  out:5
    _handle_mcp_list_tickets  CC=1  out:2
    _handle_mcp_quality_gates  CC=1  out:2
  src.koruapi.local  [2 funcs]
    build_local_parser  CC=1  out:4
    local_main  CC=6  out:9
  src.koruapi.mcp  [1 funcs]
    mcp_main  CC=2  out:2
  src.koruapi.mcp_server  [4 funcs]
    mcp_serve_main  CC=2  out:10
    tool_list_tickets  CC=3  out:9
    tool_run_quality_gates  CC=6  out:13
    tool_run_ticket  CC=14  out:33
  src.koruapi.openapi  [1 funcs]
    build_openapi_document  CC=2  out:1
  src.koruapi.server  [8 funcs]
    do_GET  CC=5  out:12
    do_POST  CC=2  out:4
    log_message  CC=1  out:2
    _handle_invoke_post  CC=5  out:13
    _json_response  CC=1  out:9
    _parse_invoke_request  CC=9  out:16
    _read_json_body  CC=5  out:7
    serve  CC=2  out:8
  src.korudsl.cli  [3 funcs]
    _build_parser  CC=1  out:11
    _read_input  CC=2  out:2
    main  CC=11  out:18
  src.korudsl.library  [11 funcs]
    _apply_prefixed_line  CC=4  out:3
    _emit_functions  CC=4  out:8
    _emit_goal  CC=9  out:12
    _emit_goals  CC=3  out:4
    _emit_objective  CC=5  out:5
    _handle_func  CC=3  out:1
    _start_goal  CC=2  out:2
    convert_goals_json_to_library  CC=9  out:7
    ensure_library_structure  CC=2  out:4
    library_to_dsl  CC=4  out:6
  src.korudsl.transform  [3 funcs]
    dsl_roundtrip_report  CC=1  out:7
    library_from_any  CC=12  out:15
    library_to_any  CC=2  out:3
  src.koruide.client  [2 funcs]
    __init__  CC=2  out:1
    request  CC=7  out:15
  src.koruide.config  [4 funcs]
    _merge_submit_keys  CC=7  out:5
    cached_config  CC=1  out:2
    default_config_path  CC=1  out:1
    load_config  CC=4  out:10
  src.koruide.daemon  [16 funcs]
    __init__  CC=7  out:8
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=11  out:46
    _drive_via_plugin  CC=2  out:10
    _handle_ack  CC=9  out:9
    _handle_hello  CC=5  out:12
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=6  out:11
  src.koruide.host_setup  [12 funcs]
    _human_followups  CC=14  out:10
    _package_manager_hint  CC=5  out:4
    _print_setup_host_apt_section  CC=2  out:6
    _print_setup_host_backends  CC=3  out:6
    _print_setup_host_header  CC=2  out:4
    _print_setup_host_human_followups  CC=3  out:4
    _print_setup_host_ides  CC=4  out:8
    _print_setup_host_install_details  CC=6  out:10
    _print_text_report  CC=2  out:1
    _try_apt_install  CC=5  out:11
  src.koruide.ide  [25 funcs]
    _active_window_pid_x11  CC=7  out:6
    _auto_profile_candidate_ids  CC=3  out:10
    _candidate_score  CC=1  out:3
    _ide_id_from_process  CC=5  out:4
    _iter_proc_pids  CC=4  out:6
    _matches  CC=7  out:5
    _read_cmdline  CC=2  out:5
    _read_comm  CC=2  out:3
    _read_exe  CC=2  out:1
    _resolve_auto_drive_target  CC=13  out:6
  src.koruide.injector  [9 funcs]
    _candidate_backends  CC=5  out:10
    _type_with_backend  CC=14  out:21
    submit_only  CC=5  out:9
    type_text  CC=8  out:11
    _extra_enter_count  CC=3  out:4
    _forced_injector_backend  CC=2  out:3
    _submit_key_for  CC=1  out:2
    _ydotool_enter_keycode  CC=2  out:3
    _ydotool_submit_mode  CC=3  out:3
  src.koruide.os_injector  [22 funcs]
    _clipboard_backend  CC=3  out:2
    _cmd_timeout_seconds  CC=3  out:4
    _post_focus_delay_seconds  CC=3  out:5
    _read_json  CC=4  out:5
    _run_cmd  CC=5  out:7
    _set_clipboard  CC=3  out:6
    _tool_pid  CC=4  out:2
    _xdotool  CC=1  out:1
    capture_from_xdotool  CC=1  out:1
    capture_mouse_xy  CC=6  out:10
  src.koruide.plugin_installer  [14 funcs]
    _configure_socket_path  CC=8  out:12
    _env_reassert_extension_install  CC=1  out:3
    _extension_is_installed  CC=4  out:5
    _ide_from_terminal_env  CC=1  out:1
    _install_extension_vsix  CC=10  out:14
    _reassert_extension_extra  CC=9  out:5
    _resolve_ide_command  CC=7  out:4
    _result_already_installed  CC=2  out:3
    _settings_path_for_ide  CC=3  out:6
    _terminal_vscode_flavor  CC=5  out:4
  src.koruide.protocol  [6 funcs]
    to_dict  CC=4  out:1
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    chat_send  CC=1  out:1
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koruide.socket  [2 funcs]
    _autopilot_socket_basename  CC=6  out:7
    default_socket_path  CC=5  out:14
  src.koruide.utils  [1 funcs]
    resolve_xdg_path  CC=2  out:3

EDGES:
  services.healing-webhook.app._enrich_ticket_with_vallm → services.healing-webhook.app._resolve_affected_files
  services.healing-webhook.app._enrich_ticket_with_vallm → services.healing-webhook.app._run_vallm_check
  services.healing-webhook.app._execute_planfile_create → services.healing-webhook.app._extract_ticket_id_from_stdout
  services.healing-webhook.app.create_planfile_ticket → services.healing-webhook.app._enrich_ticket_with_vallm
  services.healing-webhook.app.create_planfile_ticket → plugins.koru-autopilot-vscode.src.extension.AutopilotBridge.next
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
  src.korudsl.cli.main → src.korudsl.cli._read_input
  src.korudsl.cli.main → src.korudsl.transform.library_from_any
  src.korudsl.cli.main → src.korudsl.transform.library_to_any
  src.korudsl.cli.main → src.korudsl.transform.dsl_roundtrip_report
  src.korudsl.cli.main → src.korudsl.cli._build_parser
  src.korudsl.transform.library_from_any → src.korudsl.library.ensure_library_structure
  src.korudsl.transform.library_from_any → src.korudsl.library.convert_goals_json_to_library
  src.korudsl.transform.library_from_any → src.korudsl.library.normalize_dsl_to_library
  src.korudsl.transform.library_to_any → src.korudsl.library.library_to_dsl
  src.korudsl.transform.library_to_any → src.korudsl.library.ensure_library_structure
  src.korudsl.transform.dsl_roundtrip_report → src.korudsl.library.normalize_dsl_to_library
  src.korudsl.transform.dsl_roundtrip_report → src.korudsl.library.library_to_dsl
  src.korudsl.library._apply_prefixed_line → src.korudsl.library._handle_func
  src.korudsl.library.normalize_dsl_to_library → src.korudsl.library.ensure_library_structure
  src.korudsl.library.normalize_dsl_to_library → src.korudsl.library._apply_prefixed_line
  src.korudsl.library.normalize_dsl_to_library → src.korudsl.library._start_goal
  src.korudsl.library.convert_goals_json_to_library → src.korudsl.library.ensure_library_structure
  src.korudsl.library._emit_goal → src.korudsl.library._emit_objective
  src.korudsl.library._emit_goals → src.korudsl.library._emit_goal
  src.korudsl.library.library_to_dsl → src.korudsl.library.ensure_library_structure
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

Closed-loop automation across semcod/* repositories.
