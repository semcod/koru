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
- **version**: `0.1.130`
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
  version: 0.1.130;
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

## Call Graph

*442 nodes · 500 edges · 82 modules · CC̄=4.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 283 | 0 | **283** |
| `run_cycle` *(in src.koru.autonomous_cycle)* | 89 ⚠ | 0 | 168 | **168** |
| `invoke_integration` *(in src.koruapi.invoke)* | 35 ⚠ | 2 | 70 | **72** |
| `detect_agent_options` *(in src.koru.agents)* | 16 ⚠ | 2 | 61 | **63** |
| `run_next_planfile_task` *(in src.koru.queue.runner)* | 43 ⚠ | 2 | 57 | **59** |
| `apply_autoloop_env_to_args` *(in src.koru.autonomy.env)* | 31 ⚠ | 1 | 53 | **54** |
| `create_nl_task` *(in src.koru.tasks)* | 23 ⚠ | 6 | 47 | **53** |
| `from_env` *(in src.koru.autonomy.config.AutonomyConfig)* | 4 | 0 | 50 | **50** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.19s
# nodes: 442 | edges: 500 | modules: 82
# CC̄=4.7

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:283  out:0  total:283
  src.koru.autonomous_cycle.run_cycle
    CC=89  in:0  out:168  total:168
  src.koruapi.invoke.invoke_integration
    CC=35  in:2  out:70  total:72
  src.koru.agents.detect_agent_options
    CC=16  in:2  out:61  total:63
  src.koru.queue.runner.run_next_planfile_task
    CC=43  in:2  out:57  total:59
  src.koru.autonomy.env.apply_autoloop_env_to_args
    CC=31  in:1  out:53  total:54
  src.koru.tasks.create_nl_task
    CC=23  in:6  out:47  total:53
  src.koru.autonomy.config.AutonomyConfig.from_env
    CC=4  in:0  out:50  total:50
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.local_service._build_handler
    CC=1  in:1  out:39  total:40
  src.koru.activity_log.activity
    CC=4  in:32  out:7  total:39
  src.koru.init_host_environment._render_host_environment_md
    CC=15  in:1  out:38  total:39
  src.koruide.host_setup._print_text_report
    CC=15  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.events.emit_management_event
    CC=8  in:26  out:7  total:33
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  scripts.planfile-sync-todo.do_from_todo
    CC=19  in:1  out:31  total:32
  src.koru.autonomy.post_run_verify.load_post_run_verify_config
    CC=19  in:1  out:31  total:32
  src.koru.autonomous_cycle._run_idle_diagnostics
    CC=17  in:1  out:30  total:31

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [2 funcs]
    connect  CC=2  out:7
    next  CC=2  out:1
  scripts.koru-gate-capture  [13 funcs]
    _append_existing_note  CC=8  out:9
    _create_ticket  CC=3  out:5
    _existing_finding_tickets  CC=9  out:7
    _extract_finding_keys_from_item  CC=5  out:6
    _first_meaningful_line  CC=3  out:4
    _first_nonempty_line  CC=3  out:2
    _handle_existing_finding  CC=4  out:2
    _is_noise_line  CC=4  out:4
    _matched_failure_line  CC=4  out:4
    _parse_args  CC=1  out:10
  scripts.koru-soak-monitor  [1 funcs]
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
  src.koru.activity_log  [5 funcs]
    _out_stream  CC=2  out:0
    activity  CC=4  out:7
    activity_enabled  CC=1  out:3
    activity_info  CC=5  out:11
    preview_text  CC=2  out:3
  src.koru.agent_backend_runtime  [1 funcs]
    send_chat  CC=2  out:3
  src.koru.agent_backends  [6 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    list_agent_backend_ids  CC=2  out:1
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.agents  [12 funcs]
    _marker  CC=1  out:2
    _which  CC=1  out:1
    agent_lane_environment  CC=1  out:3
    autopilot_backend_for_agent_id  CC=3  out:1
    detect_agent_environment  CC=6  out:7
    detect_agent_options  CC=16  out:61
    detect_project_environment  CC=4  out:22
    format_agent_lane_exports  CC=2  out:6
    launch_agent  CC=4  out:8
    normalize_agent_lane_id  CC=6  out:8
  src.koru.autonomous_cycle  [8 funcs]
    _autopilot_event_path  CC=1  out:2
    _create_diagnostic_ticket  CC=2  out:6
    _drain_autopilot_events  CC=6  out:8
    _is_topology_enabled  CC=4  out:2
    _run_command_check  CC=2  out:4
    _run_idle_diagnostics  CC=17  out:30
    _stdio_info  CC=1  out:1
    run_cycle  CC=89  out:168
  src.koru.autonomous_diagnostics  [1 funcs]
    create_diagnostic_ticket  CC=2  out:6
  src.koru.autonomous_env  [1 funcs]
    apply_autonomous_env_overrides  CC=1  out:1
  src.koru.autonomous_wup  [7 funcs]
    _resolve_wup_testql_bin  CC=4  out:3
    _start_wup_watch  CC=9  out:12
    _stop_process  CC=4  out:6
    _wup_cpu_throttle_arg  CC=2  out:1
    _wup_stdio_info  CC=2  out:1
    _wup_topology_gate  CC=4  out:2
    _wup_watch_command  CC=3  out:9
  src.koru.autonomy.config  [1 funcs]
    from_env  CC=4  out:50
  src.koru.autonomy.env  [5 funcs]
    _env_get  CC=4  out:5
    _env_ticket_sources  CC=5  out:7
    apply_autoloop_env_to_args  CC=31  out:53
    autonomous_environ_doctor_probe  CC=12  out:29
    env_truthy  CC=3  out:3
  src.koru.autonomy.environment  [3 funcs]
    probe_environment  CC=15  out:11
    probe_ide_presence  CC=14  out:17
    probe_socket_health  CC=5  out:11
  src.koru.autonomy.heal  [2 funcs]
    heal_environment  CC=3  out:2
    remove_stale_socket  CC=5  out:6
  src.koru.autonomy.ide_work  [9 funcs]
    _list_in_progress_tickets  CC=9  out:5
    _parse_iso_datetime  CC=5  out:5
    _parse_open_tickets  CC=11  out:14
    _ticket_in_progress_started_at  CC=3  out:6
    build_ide_work_prompt  CC=12  out:23
    fetch_next_open_ticket  CC=5  out:2
    release_stale_in_progress_tickets  CC=8  out:9
    resolve_idle_drive_prompt  CC=2  out:2
    resolve_in_progress_stale_minutes  CC=10  out:9
  src.koru.autonomy.post_run_verify  [11 funcs]
    _parse_iso_datetime  CC=5  out:5
    _record_verify_outcomes  CC=5  out:5
    _truncate  CC=2  out:3
    _truthy_env  CC=2  out:3
    apply_verify_failure  CC=2  out:3
    fetch_recently_done_ticket_ids  CC=14  out:13
    fetch_ticket_status  CC=9  out:7
    load_post_run_verify_config  CC=19  out:31
    run_verify_commands  CC=8  out:7
    verify_after_ide_work  CC=13  out:7
  src.koru.autonomy.telemetry_snapshot  [3 funcs]
    autonomy_telemetry_path  CC=1  out:1
    build_autonomy_loop_brief  CC=5  out:12
    write_autonomy_cycle_telemetry  CC=2  out:9
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.autopilot.utils.client_helpers  [1 funcs]
    call_daemon_method  CC=4  out:7
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
  src.koru.context  [25 funcs]
    _auto_promote_blocking_tickets  CC=4  out:5
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _build_ticket_args  CC=3  out:1
    _extract_error_from_stderr  CC=7  out:4
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=18  out:15
    _find_blocking_tickets  CC=6  out:8
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
  src.koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
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
  src.koru.init_host_environment  [5 funcs]
    _id_group_names  CC=4  out:3
    _read_os_release  CC=6  out:10
    _render_host_environment_md  CC=15  out:38
    build_host_environment_report  CC=2  out:18
    write_host_environment_bundle  CC=2  out:12
  src.koru.local_service  [7 funcs]
    _build_handler  CC=1  out:39
    _env_int  CC=3  out:3
    _koru_version  CC=2  out:1
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
  src.koru.project_pipeline  [5 funcs]
    build_project_pipeline_brief  CC=9  out:14
    default_koru_project_pipeline_text  CC=1  out:0
    load_koru_project_pipeline  CC=4  out:5
    project_pipeline_path  CC=1  out:1
    write_koru_project_pipeline_if_absent  CC=2  out:5
  src.koru.queue.human  [1 funcs]
    default_human_prompt  CC=5  out:12
  src.koru.queue.koru_queue_argv  [1 funcs]
    build_koru_queue_argv  CC=5  out:7
  src.koru.queue.locking  [4 funcs]
    claim_lease_seconds_str  CC=2  out:6
    queue_lock_wanted  CC=1  out:3
    queue_runner_lock  CC=3  out:6
    ticket_claim_or_error  CC=4  out:4
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=12  out:8
  src.koru.queue.planfile_ticket_note  [2 funcs]
    _stderr_unknown_option  CC=3  out:0
    append_shell_evidence_note  CC=5  out:7
  src.koru.queue.runner  [1 funcs]
    run_next_planfile_task  CC=43  out:57
  src.koru.queue.runners  [2 funcs]
    _planfile_env  CC=1  out:0
    run_process  CC=1  out:2
  src.koru.queue.shell_evidence  [2 funcs]
    _tail_stream  CC=3  out:2
    format_shell_run_note  CC=7  out:8
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
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.semcod_tools  [3 funcs]
    _config_present  CC=3  out:2
    _read_pyproject  CC=3  out:3
    detect_semcod_tools  CC=7  out:9
  src.koru.stdio_events  [3 funcs]
    default_stdio_format_from_env  CC=3  out:3
    iso_ts  CC=1  out:4
    write_stdio_event  CC=2  out:4
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
  src.koruapi.integrations  [2 funcs]
    get_integration  CC=1  out:1
    list_integrations  CC=4  out:2
  src.koruapi.invoke  [1 funcs]
    invoke_integration  CC=35  out:70
  src.koruapi.local  [2 funcs]
    build_local_parser  CC=1  out:4
    local_main  CC=6  out:9
  src.koruapi.mcp  [1 funcs]
    mcp_main  CC=2  out:2
  src.koruapi.mcp_server  [25 funcs]
    _create_job  CC=1  out:4
    _detect_enabled_gates  CC=5  out:6
    _find_ticket  CC=3  out:1
    _gate_commands  CC=1  out:6
    _get_job_store_path  CC=2  out:1
    _get_process_memory_mb  CC=3  out:2
    _get_python_cmd  CC=1  out:1
    _jsonrpc_error  CC=2  out:0
    _jsonrpc_response  CC=1  out:0
    _load_jobs  CC=3  out:4
  src.koruapi.openapi  [1 funcs]
    build_openapi_document  CC=2  out:1
  src.koruapi.server  [1 funcs]
    serve  CC=2  out:8
  src.korudsl.cli  [3 funcs]
    _build_parser  CC=1  out:11
    _read_input  CC=2  out:2
    main  CC=11  out:18
  src.korudsl.library  [7 funcs]
    _apply_prefixed_line  CC=4  out:3
    _handle_func  CC=3  out:1
    _start_goal  CC=2  out:2
    convert_goals_json_to_library  CC=9  out:7
    ensure_library_structure  CC=2  out:4
    library_to_dsl  CC=17  out:26
    normalize_dsl_to_library  CC=7  out:9
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
  src.koruide.host_setup  [6 funcs]
    _human_followups  CC=14  out:10
    _package_manager_hint  CC=5  out:4
    _print_text_report  CC=15  out:38
    _try_apt_install  CC=5  out:11
    build_setup_host_report  CC=7  out:11
    run_host_setup  CC=6  out:8
  src.koruide.ide  [18 funcs]
    _active_window_pid_x11  CC=7  out:6
    _auto_profile_candidate_ids  CC=3  out:10
    _candidate_score  CC=17  out:7
    _ide_id_from_process  CC=5  out:4
    _iter_proc_pids  CC=4  out:6
    _matches  CC=7  out:5
    _read_cmdline  CC=2  out:5
    _read_comm  CC=2  out:3
    _read_exe  CC=2  out:1
    _vscode_family_env_present  CC=3  out:3
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
  src.koruide.protocol  [3 funcs]
    to_dict  CC=4  out:1
    _filter_extras  CC=6  out:4
    decode  CC=12  out:21
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
  src.koruide.config.default_config_path → src.koruide.utils.resolve_xdg_path
  src.koruide.config.load_config → src.koruide.config._merge_submit_keys
  src.koruide.config.load_config → src.koruide.config.default_config_path
  src.koruide.config.load_config → scripts.koru-soak-monitor.print
  src.koruide.config.cached_config → src.koruide.config.load_config
  src.koruide.protocol.decode → src.koruide.protocol._filter_extras
  src.koruide.host_setup.build_setup_host_report → src.koruide.ide.detect_focused_ide_id
  src.koruide.host_setup.build_setup_host_report → src.koruide.host_setup._package_manager_hint
  src.koruide.host_setup.build_setup_host_report → src.koruide.host_setup._human_followups
  src.koruide.host_setup.build_setup_host_report → src.koru.ide_runtime.detect_running_ides
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup.build_setup_host_report
  src.koruide.host_setup.run_host_setup → scripts.koru-soak-monitor.print
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup._print_text_report
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup._try_apt_install
  src.koruide.host_setup._print_text_report → scripts.koru-soak-monitor.print
  src.koruide.client.KoruIDEClient.__init__ → src.koruide.socket.default_socket_path
  src.koruide.client.KoruIDEClient.request → src.koruide.protocol.decode
  src.koruide.injector._submit_key_for → src.koruide.config.cached_config
  src.koruide.injector.Injector._candidate_backends → src.koruide.injector._forced_injector_backend
  src.koruide.injector.Injector._type_with_backend → src.koruide.injector._extra_enter_count
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
# generated in 0.19s
# nodes: 442 | edges: 500 | modules: 82
# CC̄=4.7

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:283  out:0  total:283
  src.koru.autonomous_cycle.run_cycle
    CC=89  in:0  out:168  total:168
  src.koruapi.invoke.invoke_integration
    CC=35  in:2  out:70  total:72
  src.koru.agents.detect_agent_options
    CC=16  in:2  out:61  total:63
  src.koru.queue.runner.run_next_planfile_task
    CC=43  in:2  out:57  total:59
  src.koru.autonomy.env.apply_autoloop_env_to_args
    CC=31  in:1  out:53  total:54
  src.koru.tasks.create_nl_task
    CC=23  in:6  out:47  total:53
  src.koru.autonomy.config.AutonomyConfig.from_env
    CC=4  in:0  out:50  total:50
  src.koru.policy.load_policy
    CC=9  in:2  out:43  total:45
  src.koru.local_service._build_handler
    CC=1  in:1  out:39  total:40
  src.koru.activity_log.activity
    CC=4  in:32  out:7  total:39
  src.koru.init_host_environment._render_host_environment_md
    CC=15  in:1  out:38  total:39
  src.koruide.host_setup._print_text_report
    CC=15  in:1  out:38  total:39
  src.koru.watch.format_queue_event
    CC=19  in:1  out:35  total:36
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.events.emit_management_event
    CC=8  in:26  out:7  total:33
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  scripts.planfile-sync-todo.do_from_todo
    CC=19  in:1  out:31  total:32
  src.koru.autonomy.post_run_verify.load_post_run_verify_config
    CC=19  in:1  out:31  total:32
  src.koru.autonomous_cycle._run_idle_diagnostics
    CC=17  in:1  out:30  total:31

MODULES:
  plugins.koru-autopilot-vscode.src.extension  [2 funcs]
    connect  CC=2  out:7
    next  CC=2  out:1
  scripts.koru-gate-capture  [13 funcs]
    _append_existing_note  CC=8  out:9
    _create_ticket  CC=3  out:5
    _existing_finding_tickets  CC=9  out:7
    _extract_finding_keys_from_item  CC=5  out:6
    _first_meaningful_line  CC=3  out:4
    _first_nonempty_line  CC=3  out:2
    _handle_existing_finding  CC=4  out:2
    _is_noise_line  CC=4  out:4
    _matched_failure_line  CC=4  out:4
    _parse_args  CC=1  out:10
  scripts.koru-soak-monitor  [1 funcs]
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
  src.koru.activity_log  [5 funcs]
    _out_stream  CC=2  out:0
    activity  CC=4  out:7
    activity_enabled  CC=1  out:3
    activity_info  CC=5  out:11
    preview_text  CC=2  out:3
  src.koru.agent_backend_runtime  [1 funcs]
    send_chat  CC=2  out:3
  src.koru.agent_backends  [6 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    list_agent_backend_ids  CC=2  out:1
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.agents  [12 funcs]
    _marker  CC=1  out:2
    _which  CC=1  out:1
    agent_lane_environment  CC=1  out:3
    autopilot_backend_for_agent_id  CC=3  out:1
    detect_agent_environment  CC=6  out:7
    detect_agent_options  CC=16  out:61
    detect_project_environment  CC=4  out:22
    format_agent_lane_exports  CC=2  out:6
    launch_agent  CC=4  out:8
    normalize_agent_lane_id  CC=6  out:8
  src.koru.autonomous_cycle  [8 funcs]
    _autopilot_event_path  CC=1  out:2
    _create_diagnostic_ticket  CC=2  out:6
    _drain_autopilot_events  CC=6  out:8
    _is_topology_enabled  CC=4  out:2
    _run_command_check  CC=2  out:4
    _run_idle_diagnostics  CC=17  out:30
    _stdio_info  CC=1  out:1
    run_cycle  CC=89  out:168
  src.koru.autonomous_diagnostics  [1 funcs]
    create_diagnostic_ticket  CC=2  out:6
  src.koru.autonomous_env  [1 funcs]
    apply_autonomous_env_overrides  CC=1  out:1
  src.koru.autonomous_wup  [7 funcs]
    _resolve_wup_testql_bin  CC=4  out:3
    _start_wup_watch  CC=9  out:12
    _stop_process  CC=4  out:6
    _wup_cpu_throttle_arg  CC=2  out:1
    _wup_stdio_info  CC=2  out:1
    _wup_topology_gate  CC=4  out:2
    _wup_watch_command  CC=3  out:9
  src.koru.autonomy.config  [1 funcs]
    from_env  CC=4  out:50
  src.koru.autonomy.env  [5 funcs]
    _env_get  CC=4  out:5
    _env_ticket_sources  CC=5  out:7
    apply_autoloop_env_to_args  CC=31  out:53
    autonomous_environ_doctor_probe  CC=12  out:29
    env_truthy  CC=3  out:3
  src.koru.autonomy.environment  [3 funcs]
    probe_environment  CC=15  out:11
    probe_ide_presence  CC=14  out:17
    probe_socket_health  CC=5  out:11
  src.koru.autonomy.heal  [2 funcs]
    heal_environment  CC=3  out:2
    remove_stale_socket  CC=5  out:6
  src.koru.autonomy.ide_work  [9 funcs]
    _list_in_progress_tickets  CC=9  out:5
    _parse_iso_datetime  CC=5  out:5
    _parse_open_tickets  CC=11  out:14
    _ticket_in_progress_started_at  CC=3  out:6
    build_ide_work_prompt  CC=12  out:23
    fetch_next_open_ticket  CC=5  out:2
    release_stale_in_progress_tickets  CC=8  out:9
    resolve_idle_drive_prompt  CC=2  out:2
    resolve_in_progress_stale_minutes  CC=10  out:9
  src.koru.autonomy.post_run_verify  [11 funcs]
    _parse_iso_datetime  CC=5  out:5
    _record_verify_outcomes  CC=5  out:5
    _truncate  CC=2  out:3
    _truthy_env  CC=2  out:3
    apply_verify_failure  CC=2  out:3
    fetch_recently_done_ticket_ids  CC=14  out:13
    fetch_ticket_status  CC=9  out:7
    load_post_run_verify_config  CC=19  out:31
    run_verify_commands  CC=8  out:7
    verify_after_ide_work  CC=13  out:7
  src.koru.autonomy.telemetry_snapshot  [3 funcs]
    autonomy_telemetry_path  CC=1  out:1
    build_autonomy_loop_brief  CC=5  out:12
    write_autonomy_cycle_telemetry  CC=2  out:9
  src.koru.autopilot.audit  [4 funcs]
    __init__  CC=5  out:11
    record  CC=7  out:6
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koru.autopilot.utils.client_helpers  [1 funcs]
    call_daemon_method  CC=4  out:7
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
  src.koru.context  [25 funcs]
    _auto_promote_blocking_tickets  CC=4  out:5
    _build_instructions  CC=2  out:4
    _build_self_service  CC=5  out:2
    _build_setup_instructions  CC=1  out:0
    _build_shared_rules  CC=15  out:17
    _build_ticket_args  CC=3  out:1
    _extract_error_from_stderr  CC=7  out:4
    _fetch_all_tickets  CC=9  out:5
    _fetch_ticket_data  CC=18  out:15
    _find_blocking_tickets  CC=6  out:8
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
  src.koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
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
  src.koru.init_host_environment  [5 funcs]
    _id_group_names  CC=4  out:3
    _read_os_release  CC=6  out:10
    _render_host_environment_md  CC=15  out:38
    build_host_environment_report  CC=2  out:18
    write_host_environment_bundle  CC=2  out:12
  src.koru.local_service  [7 funcs]
    _build_handler  CC=1  out:39
    _env_int  CC=3  out:3
    _koru_version  CC=2  out:1
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
  src.koru.project_pipeline  [5 funcs]
    build_project_pipeline_brief  CC=9  out:14
    default_koru_project_pipeline_text  CC=1  out:0
    load_koru_project_pipeline  CC=4  out:5
    project_pipeline_path  CC=1  out:1
    write_koru_project_pipeline_if_absent  CC=2  out:5
  src.koru.queue.human  [1 funcs]
    default_human_prompt  CC=5  out:12
  src.koru.queue.koru_queue_argv  [1 funcs]
    build_koru_queue_argv  CC=5  out:7
  src.koru.queue.locking  [4 funcs]
    claim_lease_seconds_str  CC=2  out:6
    queue_lock_wanted  CC=1  out:3
    queue_runner_lock  CC=3  out:6
    ticket_claim_or_error  CC=4  out:4
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=12  out:8
  src.koru.queue.planfile_ticket_note  [2 funcs]
    _stderr_unknown_option  CC=3  out:0
    append_shell_evidence_note  CC=5  out:7
  src.koru.queue.runner  [1 funcs]
    run_next_planfile_task  CC=43  out:57
  src.koru.queue.runners  [2 funcs]
    _planfile_env  CC=1  out:0
    run_process  CC=1  out:2
  src.koru.queue.shell_evidence  [2 funcs]
    _tail_stream  CC=3  out:2
    format_shell_run_note  CC=7  out:8
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
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.semcod_tools  [3 funcs]
    _config_present  CC=3  out:2
    _read_pyproject  CC=3  out:3
    detect_semcod_tools  CC=7  out:9
  src.koru.stdio_events  [3 funcs]
    default_stdio_format_from_env  CC=3  out:3
    iso_ts  CC=1  out:4
    write_stdio_event  CC=2  out:4
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
  src.koruapi.integrations  [2 funcs]
    get_integration  CC=1  out:1
    list_integrations  CC=4  out:2
  src.koruapi.invoke  [1 funcs]
    invoke_integration  CC=35  out:70
  src.koruapi.local  [2 funcs]
    build_local_parser  CC=1  out:4
    local_main  CC=6  out:9
  src.koruapi.mcp  [1 funcs]
    mcp_main  CC=2  out:2
  src.koruapi.mcp_server  [25 funcs]
    _create_job  CC=1  out:4
    _detect_enabled_gates  CC=5  out:6
    _find_ticket  CC=3  out:1
    _gate_commands  CC=1  out:6
    _get_job_store_path  CC=2  out:1
    _get_process_memory_mb  CC=3  out:2
    _get_python_cmd  CC=1  out:1
    _jsonrpc_error  CC=2  out:0
    _jsonrpc_response  CC=1  out:0
    _load_jobs  CC=3  out:4
  src.koruapi.openapi  [1 funcs]
    build_openapi_document  CC=2  out:1
  src.koruapi.server  [1 funcs]
    serve  CC=2  out:8
  src.korudsl.cli  [3 funcs]
    _build_parser  CC=1  out:11
    _read_input  CC=2  out:2
    main  CC=11  out:18
  src.korudsl.library  [7 funcs]
    _apply_prefixed_line  CC=4  out:3
    _handle_func  CC=3  out:1
    _start_goal  CC=2  out:2
    convert_goals_json_to_library  CC=9  out:7
    ensure_library_structure  CC=2  out:4
    library_to_dsl  CC=17  out:26
    normalize_dsl_to_library  CC=7  out:9
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
  src.koruide.host_setup  [6 funcs]
    _human_followups  CC=14  out:10
    _package_manager_hint  CC=5  out:4
    _print_text_report  CC=15  out:38
    _try_apt_install  CC=5  out:11
    build_setup_host_report  CC=7  out:11
    run_host_setup  CC=6  out:8
  src.koruide.ide  [18 funcs]
    _active_window_pid_x11  CC=7  out:6
    _auto_profile_candidate_ids  CC=3  out:10
    _candidate_score  CC=17  out:7
    _ide_id_from_process  CC=5  out:4
    _iter_proc_pids  CC=4  out:6
    _matches  CC=7  out:5
    _read_cmdline  CC=2  out:5
    _read_comm  CC=2  out:3
    _read_exe  CC=2  out:1
    _vscode_family_env_present  CC=3  out:3
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
  src.koruide.protocol  [3 funcs]
    to_dict  CC=4  out:1
    _filter_extras  CC=6  out:4
    decode  CC=12  out:21
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
  src.koruide.config.default_config_path → src.koruide.utils.resolve_xdg_path
  src.koruide.config.load_config → src.koruide.config._merge_submit_keys
  src.koruide.config.load_config → src.koruide.config.default_config_path
  src.koruide.config.load_config → scripts.koru-soak-monitor.print
  src.koruide.config.cached_config → src.koruide.config.load_config
  src.koruide.protocol.decode → src.koruide.protocol._filter_extras
  src.koruide.host_setup.build_setup_host_report → src.koruide.ide.detect_focused_ide_id
  src.koruide.host_setup.build_setup_host_report → src.koruide.host_setup._package_manager_hint
  src.koruide.host_setup.build_setup_host_report → src.koruide.host_setup._human_followups
  src.koruide.host_setup.build_setup_host_report → src.koru.ide_runtime.detect_running_ides
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup.build_setup_host_report
  src.koruide.host_setup.run_host_setup → scripts.koru-soak-monitor.print
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup._print_text_report
  src.koruide.host_setup.run_host_setup → src.koruide.host_setup._try_apt_install
  src.koruide.host_setup._print_text_report → scripts.koru-soak-monitor.print
  src.koruide.client.KoruIDEClient.__init__ → src.koruide.socket.default_socket_path
  src.koruide.client.KoruIDEClient.request → src.koruide.protocol.decode
  src.koruide.injector._submit_key_for → src.koruide.config.cached_config
  src.koruide.injector.Injector._candidate_backends → src.koruide.injector._forced_injector_backend
  src.koruide.injector.Injector._type_with_backend → src.koruide.injector._extra_enter_count
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 207f 36948L | python:120,shell:41,yaml:16,yml:8,typescript:6,kotlin:6,json:3,txt:1,properties:1,xml:1,toml:1 | 2026-05-19
# generated in 0.05s
# CC̄=4.7 | critical:48/1037 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    _print_text_report CC=15 (limit:15)
  🟡 CC    run_idle_diagnostics CC=17 (limit:15)
  🟡 CC    format_queue_event CC=19 (limit:15)
  🟡 CC    find_candidates CC=15 (limit:15)
  🟡 CC    detect_tools CC=26 (limit:15)
  🟡 CC    build_tool_task_scaffold CC=16 (limit:15)
  🟡 CC    summary CC=15 (limit:15)
  🟡 CC    _fetch_ticket_data CC=18 (limit:15)
  🟡 CC    _build_shared_rules CC=15 (limit:15)
  🟡 CC    policy_violations CC=22 (limit:15)
  🟡 CC    detect_agent_options CC=16 (limit:15)
  🟡 CC    _recommended_next_steps CC=15 (limit:15)
  🟡 CC    _render_host_environment_md CC=15 (limit:15)
  🟡 CC    _read_wup_health CC=23 (limit:15)
  🟡 CC    load_post_run_verify_config CC=19 (limit:15)
  🟡 CC    probe_environment CC=15 (limit:15)
  🟡 CC    run_llm_request CC=23 (limit:15)
  🟡 CC    do_from_todo CC=19 (limit:15)
  🟡 CC    library_to_dsl CC=17 (limit:15)
  🟡 CC    invoke_integration CC=35 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[299]:
  [1] Src [heal_rebuild_restore]: heal_rebuild_restore → _run_docker
      PURITY: 100% pure
  [2] Src [heal_annotate]: heal_annotate → _record_action
      PURITY: 100% pure
  [3] Src [_run_vallm_validate]: _run_vallm_validate
      PURITY: 100% pure
  [4] Src [heal_vallm_validate]: heal_vallm_validate → _resolve_affected_files → _infer_paths
      PURITY: 100% pure
  [5] Src [heal_redup_check]: heal_redup_check → _run_redup_check → _update_redup_metrics
      PURITY: 100% pure

LAYERS:
  src/                            CC̄=5.1    ←in:0  →out:0
  │ !! cli                       2143L  0C   52m  CC=26     ←0
  │ !! autonomous                1646L  2C   37m  CC=50     ←1
  │ !! dashboard_serve           1301L  1C   15m  CC=13     ←1
  │ !! cli_command               1282L  0C   37m  CC=15     ←0
  │ !! context                   1199L  0C   43m  CC=18     ←6
  │ !! mcp_server                1023L  0C   32m  CC=15     ←2
  │ !! scan                       864L  2C   18m  CC=15     ←3
  │ !! autonomous_cycle           860L  2C   16m  CC=89     ←0
  │ !! daemon                     708L  2C   29m  CC=21     ←0
  │ !! init                       610L  1C   12m  CC=15     ←2
  │ !! operator_pipeline          531L  2C   18m  CC=15     ←1
  │ !! doctor                     513L  2C   21m  CC=11     ←2
  │ !! ide                        508L  1C   22m  CC=27     ←5
  │ bootstrap                  446L  2C   19m  CC=10     ←2
  │ topology                   415L  1C   15m  CC=12     ←7
  │ injector                   403L  4C   20m  CC=14     ←0
  │ mcp_provision              397L  0C   21m  CC=10     ←3
  │ os_injector                392L  2C   24m  CC=14     ←2
  │ autonomous_parser          378L  0C    1m  CC=1      ←0
  │ gc                         371L  2C   12m  CC=11     ←1
  │ !! agents                     370L  1C   13m  CC=16     ←3
  │ !! plugin_installer           363L  1C   14m  CC=28     ←1
  │ !! post_run_verify            354L  2C   11m  CC=19     ←1
  │ !! queue_clean                350L  2C   10m  CC=15     ←1
  │ !! runner                     300L  0C    2m  CC=43     ←2
  │ ide_work                   296L  0C   11m  CC=12     ←2
  │ !! init_host_environment      260L  0C    7m  CC=15     ←1
  │ autonomous_startup         256L  1C    8m  CC=11     ←1
  │ !! autonomous_wup             253L  3C   10m  CC=23     ←1
  │ !! tools                      251L  0C    9m  CC=26     ←1
  │ !! policy                     234L  1C    4m  CC=22     ←2
  │ protocol                   231L  2C   14m  CC=12     ←3
  │ !! environment                224L  3C    3m  CC=15     ←1
  │ !! autonomous_process_guard   219L  2C    9m  CC=15     ←0
  │ agent_backends             214L  3C    7m  CC=11     ←2
  │ !! env                        210L  0C    6m  CC=31     ←3
  │ !! runners                    208L  0C    5m  CC=23     ←1
  │ !! host_setup                 207L  0C    6m  CC=15     ←3
  │ local_service              203L  2C   10m  CC=3      ←1
  │ gate                       202L  1C    5m  CC=12     ←1
  │ integrations               198L  1C    2m  CC=4      ←4
  │ !! library                    192L  0C   16m  CC=17     ←1
  │ !! autonomous_diagnostics     188L  0C    5m  CC=17     ←1
  │ agent_backend_runtime      180L  5C    6m  CC=9      ←0
  │ !! invoke                     178L  1C    1m  CC=35     ←2
  │ !! tasks                      176L  1C    5m  CC=23     ←6
  │ openapi                    155L  0C    1m  CC=2      ←1
  │ project_pipeline           150L  0C    5m  CC=9      ←5
  │ ide_client                 145L  2C   12m  CC=3      ←2
  │ !! server                     144L  1C    5m  CC=16     ←1
  │ semcod_tools               143L  1C    4m  CC=7      ←3
  │ ticket                     138L  0C    6m  CC=10     ←5
  │ loop                       131L  3C    4m  CC=12     ←1
  │ client                     128L  1C    8m  CC=7      ←0
  │ cli                        128L  0C    3m  CC=11     ←0
  │ run_log                    124L  1C    7m  CC=4      ←2
  │ config                     121L  1C    1m  CC=4      ←0
  │ config                     120L  1C    6m  CC=7      ←1
  │ heal                       112L  1C    3m  CC=5      ←1
  │ loop                       109L  0C    1m  CC=12     ←3
  │ runtime                    105L  0C    5m  CC=2      ←6
  │ dotenv_loader              104L  0C    3m  CC=7      ←0
  │ prompts                    101L  1C    1m  CC=10     ←1
  │ ide_router                  98L  1C    2m  CC=8      ←4
  │ dashboard                   91L  0C    3m  CC=5      ←2
  │ events                      90L  0C    2m  CC=8      ←3
  │ types                       88L  5C    1m  CC=2      ←0
  │ locking                     87L  0C    4m  CC=4      ←1
  │ !! watch                       81L  0C    3m  CC=19     ←1
  │ cli                         81L  0C    3m  CC=11     ←0
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ shell_evidence              72L  0C    2m  CC=7      ←1
  │ transform                   70L  0C    4m  CC=12     ←2
  │ __init__                    69L  0C    0m  CC=0.0    ←0
  │ activity_log                68L  0C    5m  CC=5      ←13
  │ __init__                    67L  0C    0m  CC=0.0    ←0
  │ wup_testql_compat           65L  0C    4m  CC=6      ←0
  │ client_helpers              57L  0C    2m  CC=4      ←1
  │ planfile_ticket_note        56L  0C    2m  CC=5      ←1
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ protocol                    49L  0C    0m  CC=0.0    ←0
  │ socket                      45L  0C    2m  CC=6      ←6
  │ ide_runtime                 44L  0C    2m  CC=5      ←8
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ refactor_planfile_handoff    42L  0C    1m  CC=6      ←1
  │ subprocess_runner           40L  0C    3m  CC=3      ←5
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ local                       37L  0C    2m  CC=6      ←2
  │ planfile_queue              37L  0C    0m  CC=0.0    ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ autonomous_env              26L  0C    1m  CC=1      ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ utils                       21L  0C    1m  CC=2      ←2
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←2
  │ client                      11L  0C    0m  CC=0.0    ←0
  │ audit                        9L  2C    6m  CC=7      ←1
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ injector                     9L  0C    0m  CC=0.0    ←0
  │ os_injector                  9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    2m  CC=4      ←0
  │ commands                     0L  0C    0m  CC=0.0    ←0
  │
  services/                       CC̄=4.9    ←in:0  →out:0
  │ !! app                        702L  0C   27m  CC=11     ←0
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=3.1    ←in:0  →out:0
  │ !! extension.ts               590L  2C   63m  CC=18     ←5
  │ probe-ladder.ts            251L  3C   24m  CC=9      ←0
  │ KoruAutopilotService.kt    136L  1C    5m  CC=0.0    ←0
  │ package.json               112L  0C    0m  CC=0.0    ←0
  │ dispatch-plan.test.ts       94L  0C   11m  CC=4      ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ probe-ladder.test.ts        68L  0C    9m  CC=2      ←0
  │ socketPath.ts               66L  0C   15m  CC=9      ←0
  │ build.gradle.kts            49L  0C    4m  CC=0.0    ←0
  │ SocketPath.kt               33L  0C    0m  CC=0.0    ←0
  │ dispatch-plan.ts            26L  1C    1m  CC=7      ←0
  │ plugin.xml                  24L  0C    0m  CC=0.0    ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │ ChatInjector.kt             11L  1C    0m  CC=0.0    ←0
  │ KoruAutopilotReconnectAction.kt    10L  1C    0m  CC=0.0    ←0
  │ settings.gradle.kts          8L  0C    2m  CC=0.0    ←0
  │ gradle.properties            6L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=1.8    ←in:268  →out:0
  │ !! koru-autoloop.sh           576L  0C   14m  CC=0.0    ←0
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ !! planfile-sync-todo         234L  0C    9m  CC=19     ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←26
  │ koru-queue-diagnose.sh     124L  0C    0m  CC=0.0    ←0
  │ koru-soak-stop.sh          123L  0C    5m  CC=0.0    ←0
  │ koru-soak-status.sh        100L  0C    6m  CC=0.0    ←0
  │ koru-semcod-gates.sh        99L  0C    2m  CC=0.0    ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←0
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │ koru-soak-start.sh          39L  0C    1m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1319L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               893L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  511L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              95L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                91L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ wup.yaml                    56L  0C    0m  CC=0.0    ←0
  │ project.sh                  54L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │
  schemas/                        CC̄=0.0    ←in:0  →out:0
  │ koru-stdio-event.schema.json    16L  0C    0m  CC=0.0    ←0
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
  │ python-quality-baseline.yaml    14L  0C    0m  CC=0.0    ←0
  │ monorepo-hygiene.yaml       13L  0C    0m  CC=0.0    ←0
  │
  redeploy/                       CC̄=0.0    ←in:0  →out:0
  │ manifest.yaml              125L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=0.0    ←in:0  →out:0
  │ bootstrap.planfile.yaml    425L  0C    0m  CC=0.0    ←0
  │ run-e2e.sh                  43L  0C    0m  CC=0.0    ←0
  │ gitlab-ci.example.yml       41L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      21L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      19L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      15L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ run-docker.sh                7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ generated-cli-tests.testql.toon.yaml    19L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │
  testql-testing/                 CC̄=0.0    ←in:0  →out:0
  │ realtime-health.testql.toon.yaml    11L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     src/koru/cli/__init__.py                  0L
     src/koru/cli/commands.py                  0L

COUPLING:
                                                      src.koru                        scripts                    src.koruapi                    src.koruide  plugins.koru-autopilot-vscode                    src.korudsl       services.healing-webhook
                       src.koru                             ──                            222                              5                             24                              5                                                                hub
                        scripts                           ←222                             ──                            ←20                            ←26                                                                                               hub
                    src.koruapi                             41                             20                             ──                                                                                            4                                 hub
                    src.koruide                              8                             26                                                            ──                                                                                               hub
  plugins.koru-autopilot-vscode                             ←5                                                                                                                          ──                                                            ←1  hub
                    src.korudsl                                                                                           ←4                                                                                           ──                               
       services.healing-webhook                                                                                                                                                          1                                                            ──
  CYCLES: none
  HUB: src.koruide/ (fan-in=24)
  HUB: scripts/ (fan-in=268)
  HUB: plugins.koru-autopilot-vscode/ (fan-in=6)
  HUB: src.koru/ (fan-in=49)
  HUB: src.koruapi/ (fan-in=5)
  SMELL: src.koruide/ fan-out=34 → split needed
  SMELL: src.koru/ fan-out=256 → split needed
  SMELL: src.koruapi/ fan-out=65 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 30 groups | 120f 27688L | 2026-05-19

SUMMARY:
  files_scanned: 120
  total_lines:   27688
  dup_groups:    30
  dup_fragments: 69
  saved_lines:   394
  scan_ms:       2654

HOTSPOTS[7] (files with most duplication):
  src/koru/autonomous.py  dup=176L  groups=12  frags=12  (0.6%)
  src/koru/autonomous_cycle.py  dup=154L  groups=9  frags=9  (0.6%)
  src/koru/cli.py  dup=101L  groups=3  frags=8  (0.4%)
  src/koruapi/dashboard.py  dup=45L  groups=1  frags=1  (0.2%)
  src/koru/mcp_provision.py  dup=39L  groups=2  frags=5  (0.1%)
  src/koruide/protocol.py  dup=24L  groups=1  frags=2  (0.1%)
  src/korudsl/library.py  dup=22L  groups=2  frags=6  (0.1%)

DUPLICATES[30] (ranked by impact):
  [b9219889c3cb4859] ! EXAC  _run_idle_diagnostics  L=97 N=2 saved=97 sim=1.00
      src/koru/autonomous.py:1091-1187  (_run_idle_diagnostics)
      src/koru/autonomous_cycle.py:187-283  (_run_idle_diagnostics)
  [b79fb4d314048ea0] ! STRU  _build_serve_parser  L=48 N=2 saved=48 sim=1.00
      src/koru/cli.py:402-449  (_build_serve_parser)
      src/koruapi/dashboard.py:17-61  (build_serve_parser)
  [cfa0e91c669b55c5]   STRU  _build_local_serve_parser  L=29 N=2 saved=29 sim=1.00
      src/koru/cli.py:452-480  (_build_local_serve_parser)
      src/koruapi/local.py:12-20  (build_local_parser)
  [077cfa61a2943c36]   STRU  _serve_main  L=4 N=6 saved=20 sim=1.00
      src/koru/cli.py:1113-1116  (_serve_main)
      src/koru/cli.py:1119-1122  (_local_serve_main)
      src/koru/cli.py:1441-1444  (_mcp_serve_main)
      src/koru/cli.py:1506-1509  (_init_ide_main)
      src/koru/cli.py:1568-1571  (_dsl_main)
      src/koru/cli.py:1574-1577  (_api_main)
  [13996a2247a97ed8]   EXAC  _read_wup_health  L=16 N=2 saved=16 sim=1.00
      src/koru/autonomous.py:1073-1088  (_read_wup_health)
      src/koru/autonomous_cycle.py:169-184  (_read_wup_health)
  [400f9f906a729d1a]   STRU  provision_cursor  L=15 N=2 saved=15 sim=1.00
      src/koru/mcp_provision.py:194-208  (provision_cursor)
      src/koru/mcp_provision.py:211-225  (provision_vscode)
  [d69cbedeb6dc8f2f]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:135-147  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:107-119  (_parse_iso_datetime)
  [07394d97ab843be1]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:9-21  (resolve_xdg_path)
  [d4d1a15bc8e8affa]   STRU  message_received  L=12 N=2 saved=12 sim=1.00
      src/koruide/protocol.py:184-195  (message_received)
      src/koruide/protocol.py:198-209  (status_error)
  [db3e3e3ad621b70e]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:111-120  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve.py:237-246  (read_serve_endpoint)
  [c66988d54f59cb9c]   STRU  _ydotool_enter_keycode  L=10 N=2 saved=10 sim=1.00
      src/koruide/injector.py:59-68  (_ydotool_enter_keycode)
      src/koruide/injector.py:81-86  (_ydotool_ctrl_keycode)
  [30376722d90c4f75]   EXAC  _is_topology_enabled  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:910-918  (_is_topology_enabled)
      src/koru/autonomous_cycle.py:74-82  (_is_topology_enabled)
  [0a213b0b7ddbf9fc]   EXAC  _current_head  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:921-929  (_current_head)
      src/koru/autonomous_cycle.py:85-93  (_current_head)
  [66e72bbc9f334365]   EXAC  _run_command_check  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:1021-1029  (_run_command_check)
      src/koru/autonomous_cycle.py:121-129  (_run_command_check)
  [823aa4659db9c93d]   STRU  _handle_wait  L=3 N=4 saved=9 sim=1.00
      src/korudsl/library.py:38-40  (_handle_wait)
      src/korudsl/library.py:43-45  (_handle_get)
      src/korudsl/library.py:48-50  (_handle_save)
      src/korudsl/library.py:53-55  (_handle_if)
  [abf90bbbadf601ec]   STRU  _as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous.py:342-348  (_as_managed)
      src/koru/autonomous_process_guard.py:169-175  (as_managed)
  [8e12ae22db3cad29]   STRU  _confirm_replace_existing  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous.py:393-399  (_confirm_replace_existing)
      src/koru/autonomous_process_guard.py:213-219  (confirm_replace_existing)
  [2d7b9210c1b65241]   STRU  activity_enabled  L=3 N=3 saved=6 sim=1.00
      src/koru/activity_log.py:12-14  (activity_enabled)
      src/koru/autonomy/operator_pipeline.py:163-165  (_operator_autostart_server_enabled)
      src/koruide/plugin_installer.py:213-215  (_env_reassert_extension_install)
  [9b7967c4c573e5f1]   STRU  _process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous.py:186-191  (_process_cwd)
      src/koru/autonomous_process_guard.py:38-43  (process_cwd)
  [d3fe48eeadbdaf2c]   STRU  _cursor_project_config  L=3 N=3 saved=6 sim=1.00
      src/koru/mcp_provision.py:40-42  (_cursor_project_config)
      src/koru/mcp_provision.py:45-47  (_vscode_project_config)
      src/koru/mcp_provision.py:50-52  (_windsurf_project_config)
  [c7374d52504d8e71]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:354-359  (set_component_enabled)
      src/koru/topology.py:362-367  (set_pipeline_enabled)
  [cede1a8630b48984]   STRU  os_injector_env_disabled  L=3 N=3 saved=6 sim=1.00
      src/koruide/os_injector.py:61-63  (os_injector_env_disabled)
      src/koruide/os_injector.py:66-68  (os_injector_env_forced)
      src/koruide/os_injector.py:71-73  (dry_run_from_env)
  [825007d92835d4b3]   EXAC  _stdio_info  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous.py:122-126  (_stdio_info)
      src/koru/autonomous_cycle.py:40-43  (_stdio_info)
  [a0375ffb77746a3f]   EXAC  _open_later  L=5 N=2 saved=5 sim=1.00
      src/koruapi/dashboard_serve.py:1235-1239  (_open_later)
      src/koruapi/dashboard_serve.py:1286-1290  (_open_later)
  [c4200e7110d9ebe1]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [774459a6d92b5dbd]   EXAC  _queue_loop_waiting_ticket_label  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous.py:904-907  (_queue_loop_waiting_ticket_label)
      src/koru/autonomous_cycle.py:69-71  (_queue_loop_waiting_ticket_label)
  [a7174a018322bcf8]   EXAC  _status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous.py:1015-1018  (_status_in_skip_list)
      src/koru/autonomous_cycle.py:96-99  (_status_in_skip_list)
  [fdccb72b1fbbe81c]   EXAC  _allow_keyboard_autopilot_fallback  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:138-140  (_allow_keyboard_autopilot_fallback)
      src/koru/autonomous_cycle.py:102-104  (_allow_keyboard_autopilot_fallback)
  [be027ff698a2786c]   STRU  _action_status  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/cli_command.py:764-766  (_action_status)
      src/koru/autopilot/cli_command.py:769-773  (_action_shutdown)
  [781cd2265323c713]   STRU  _systemd_user_dir  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/cli_command.py:1165-1167  (_systemd_user_dir)
      src/koruide/config.py:63-65  (default_config_path)

REFACTOR[30] (ranked by priority):
  [1] ◐ extract_module     → src/koru/utils/_run_idle_diagnostics.py
      WHY: 2 occurrences of 97-line block across 2 files — saves 97 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [2] ◐ extract_function   → src/utils/_build_serve_parser.py
      WHY: 2 occurrences of 48-line block across 2 files — saves 48 lines
      FILES: src/koru/cli.py, src/koruapi/dashboard.py
  [3] ○ extract_function   → src/utils/_build_local_serve_parser.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/cli.py, src/koruapi/local.py
  [4] ○ extract_function   → src/koru/utils/_serve_main.py
      WHY: 6 occurrences of 4-line block across 1 files — saves 20 lines
      FILES: src/koru/cli.py
  [5] ○ extract_function   → src/koru/utils/_read_wup_health.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [6] ○ extract_function   → src/koru/utils/provision_cursor.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/mcp_provision.py
  [7] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [8] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [9] ○ extract_function   → src/koruide/utils/message_received.py
      WHY: 2 occurrences of 12-line block across 1 files — saves 12 lines
      FILES: src/koruide/protocol.py
  [10] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve.py
  [11] ○ extract_function   → src/koruide/utils/_ydotool_enter_keycode.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/koruide/injector.py
  [12] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [13] ○ extract_function   → src/koru/utils/_current_head.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [14] ○ extract_function   → src/koru/utils/_run_command_check.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [15] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [16] ○ extract_function   → src/koru/utils/_as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [17] ○ extract_function   → src/koru/utils/_confirm_replace_existing.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [18] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/activity_log.py, src/koru/autonomy/operator_pipeline.py, src/koruide/plugin_installer.py
  [19] ○ extract_function   → src/koru/utils/_process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [20] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koru/mcp_provision.py
  [21] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [22] ○ extract_function   → src/koruide/utils/os_injector_env_disabled.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koruide/os_injector.py
  [23] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [24] ○ extract_function   → src/koruapi/utils/_open_later.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koruapi/dashboard_serve.py
  [25] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [26] ○ extract_function   → src/koru/utils/_queue_loop_waiting_ticket_label.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [27] ○ extract_function   → src/koru/utils/_status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [28] ○ extract_function   → src/koru/utils/_allow_keyboard_autopilot_fallback.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [29] ○ extract_function   → src/koru/autopilot/utils/_action_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autopilot/cli_command.py
  [30] ○ extract_function   → src/utils/_systemd_user_dir.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autopilot/cli_command.py, src/koruide/config.py

QUICK_WINS[20] (low risk, high savings — do first):
  [3] extract_function   saved=29L  → src/utils/_build_local_serve_parser.py
      FILES: cli.py, local.py
  [4] extract_function   saved=20L  → src/koru/utils/_serve_main.py
      FILES: cli.py
  [5] extract_function   saved=16L  → src/koru/utils/_read_wup_health.py
      FILES: autonomous.py, autonomous_cycle.py
  [6] extract_function   saved=15L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [7] extract_function   saved=13L  → src/koru/autonomy/utils/_parse_iso_datetime.py
      FILES: ide_work.py, post_run_verify.py
  [8] extract_function   saved=12L  → src/utils/resolve_xdg_path.py
      FILES: client_helpers.py, utils.py
  [9] extract_function   saved=12L  → src/koruide/utils/message_received.py
      FILES: protocol.py
  [10] extract_function   saved=10L  → src/utils/load_koru_project_pipeline.py
      FILES: project_pipeline.py, dashboard_serve.py
  [11] extract_function   saved=10L  → src/koruide/utils/_ydotool_enter_keycode.py
      FILES: injector.py
  [12] extract_function   saved=9L  → src/koru/utils/_is_topology_enabled.py
      FILES: autonomous.py, autonomous_cycle.py

EFFORT_ESTIMATE (total ≈ 15.6h):
  hard   _run_idle_diagnostics               saved=97L  ~291min
  hard   _build_serve_parser                 saved=48L  ~144min
  medium _build_local_serve_parser           saved=29L  ~58min
  medium _serve_main                         saved=20L  ~40min
  medium _read_wup_health                    saved=16L  ~32min
  medium provision_cursor                    saved=15L  ~30min
  easy   _parse_iso_datetime                 saved=13L  ~26min
  easy   resolve_xdg_path                    saved=12L  ~24min
  easy   message_received                    saved=12L  ~24min
  easy   load_koru_project_pipeline          saved=10L  ~20min
  ... +20 more (~244min)

METRICS-TARGET:
  dup_groups:  30 → 0
  saved_lines: 394 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 972 func | 101f | 2026-05-19
# generated in 0.00s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           src/koru/autonomous.py
      WHY: 1646L, 2 classes, max CC=50
      EFFORT: ~4h  IMPACT: 82300

  [2] !! SPLIT           src/koru/cli.py
      WHY: 2143L, 0 classes, max CC=26
      EFFORT: ~4h  IMPACT: 55718

  [3] !! SPLIT-FUNC      run_cycle  CC=89  fan=58
      WHY: CC=89 exceeds 15
      EFFORT: ~1h  IMPACT: 5162

  [4] !! SPLIT-FUNC      _action_up  CC=50  fan=49
      WHY: CC=50 exceeds 15
      EFFORT: ~1h  IMPACT: 2450

  [5] !! SPLIT-FUNC      run_next_planfile_task  CC=43  fan=29
      WHY: CC=43 exceeds 15
      EFFORT: ~1h  IMPACT: 1247

  [6] !! SPLIT-FUNC      invoke_integration  CC=35  fan=35
      WHY: CC=35 exceeds 15
      EFFORT: ~1h  IMPACT: 1225

  [7] !  SPLIT-FUNC      create_nl_task  CC=23  fan=22
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 506

  [8] !  SPLIT-FUNC      _read_wup_health  CC=23  fan=19
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 437

  [9] !  SPLIT-FUNC      run_llm_request  CC=23  fan=19
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 437

  [10] !  SPLIT-FUNC      _agent_main  CC=19  fan=18
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 342


RISKS[3]:
  ⚠ Splitting src/koru/cli.py may break 52 import paths
  ⚠ Splitting src/koru/autonomous.py may break 37 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          4.8 → ≤3.4
  max-CC:      89 → ≤20
  god-modules: 18 → 0
  high-CC(≥15): 47 → ≤23
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
  prev CC̄=4.9 → now CC̄=4.8
```

## Intent

Closed-loop automation across semcod/* repositories.
