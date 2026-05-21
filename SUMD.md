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
- **version**: `0.1.177`
- **python_requires**: `>=3.12`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, project/(3 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.177;
}

dependencies {
  runtime: "pyyaml>=6.0,<7.0";
  dev: "pytest>=8.0,<9.0, pytest-cov>=5.0,<7.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, ruff>=0.11,<0.14, mypy>=1.11,<2.0, pyright>=1.1.390,<2.0, hypothesis>=6.112,<7.0, pre-commit>=3.8,<5.0, types-PyYAML>=6.0,<7.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60";
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
  step-1: run cmd=pip install planfile wup testql regix "redup>=0.4.28" vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun;
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

workflow[name="test:docker:ide-matrix"] {
  trigger: manual;
  step-1: run cmd=KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh;
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
  step-1: run cmd={{.PYTHON}} -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open;
}

workflow[name="koru:mcp:bootstrap"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli init-ide --project . --ide all;
}

workflow[name="koru:operator:plugin-probe"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot manage --ide "{{.IDE}}";
}

workflow[name="koru:operator:setup-host"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot setup-host;
}

workflow[name="koru:ide-os:calibrate"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot calibrate --ide "{{.IDE}}";
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
  python3 -m redup scan . --min-lines 10
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:redup skipped (gate:redup disabled in topology)"
    exit 0
  fi
  python3 -m redup scan . --min-lines 10
fi;
}

workflow[name="quality:redup:changed"] {
  trigger: manual;
  step-1: run cmd=bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-{{.BASE_REF | default "HEAD"}}}"; OUT="${OUT:-{{.OUT | default ".redup/wup-changed.json"}}}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi';
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
  PYTHON:
    sh: if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi

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
      - pip install planfile wup testql regix "redup>=0.4.28" vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun
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

  test:docker:ide-matrix:
    desc: 'Run Docker OS x IDE smoke matrix. Vars: SYSTEMS, IDES (defaults cover Debian/Ubuntu/Fedora/Alpine and VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed)'
    cmds:
      - KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh
    vars:
      SYSTEMS: '{{.SYSTEMS | default ""}}'
      IDES: '{{.IDES | default ""}}'

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
      - '{{.PYTHON}} -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open'
    vars:
      HOST: '{{.HOST | default "127.0.0.1"}}'
      PORT: '{{.PORT | default "8765"}}'
    interactive: true

  koru:mcp:bootstrap:
    desc: Provision koru MCP config for Cursor, VS Code, and Windsurf
    cmds:
      - '{{.PYTHON}} -m koru.cli init-ide --project . --ide all'

  koru:operator:plugin-probe:
    desc: Check autopilot daemon/plugin install, live version, and socket status
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot manage --ide "{{.IDE}}"'
    vars:
      IDE: '{{.IDE | default "auto"}}'

  koru:operator:setup-host:
    desc: Probe host injector dependencies for autopilot
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot setup-host'

  koru:ide-os:calibrate:
    desc: Calibrate OS injector chat coordinates for an IDE (IDE=vscode|vscodium|cursor|windsurf|jetbrains|zed)
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot calibrate --ide "{{.IDE}}"'
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
          python3 -m redup scan . --min-lines 10
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:redup skipped (gate:redup disabled in topology)"
            exit 0
          fi
          python3 -m redup scan . --min-lines 10
        fi
    preconditions:
      - sh: python3 -m redup --help >/dev/null
        msg: "redup Python module not installed. Run: task install:tools"

  quality:redup:changed:
    desc: 'Run incremental redup scan over files changed since BASE_REF (default: HEAD)'
    cmds:
      - bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-{{.BASE_REF | default "HEAD"}}}"; OUT="${OUT:-{{.OUT | default ".redup/wup-changed.json"}}}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi'
    preconditions:
      - sh: python3 -m redup --help >/dev/null
        msg: "redup Python module not installed. Run: task install:tools"

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
  version: 0.1.177
  env: local
```

## Dependencies

### Runtime

```text markpact:deps python
pyyaml>=6.0,<7.0
```

### Development

```text markpact:deps python scope=dev
pytest>=8.0,<9.0
pytest-cov>=5.0,<7.0
pytest-rerunfailures>=14.0,<17.0
pytest-timeout>=2.3,<3.0
pytest-xdist>=3.0,<4.0
ruff>=0.11,<0.14
mypy>=1.11,<2.0
pyright>=1.1.390,<2.0
hypothesis>=6.112,<7.0
pre-commit>=3.8,<5.0
types-PyYAML>=6.0,<7.0
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
# koru | 311f 64461L | python:246,shell:52,javascript:6,typescript:6,less:1 | 2026-05-21
# stats: 1867 func | 197 cls | 311 mod | CC̄=4.1 | critical:137 | cycles:0
# alerts[5]: CC _run_autonomous_cycle=21; CC _action_up=17; CC test_autonomy_config_from_env=16; CC autonomous_main=15; CC build_startup_probe=15
# hotspots[5]: _build_handler fan=31; _build_handler fan=28; _action_up fan=26; run_cycle fan=23; init_project fan=21
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[311]:
  app.doql.less,681
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
  examples/planfile/http-api-curl/e2e.sh,20
  examples/planfile/http-api-curl/run-docker.sh,8
  examples/planfile/queue-cli-dryrun/e2e.sh,16
  examples/planfile/queue-cli-dryrun/run-docker.sh,8
  examples/protocol/autopilot-socket-smoke/e2e.sh,27
  examples/protocol/autopilot-socket-smoke/run-docker.sh,8
  examples/run-e2e.sh,44
  examples/runtime/koru-serve-health/e2e.sh,22
  examples/runtime/koru-serve-health/run-docker.sh,8
  plugins/koru-autopilot-vscode/out/dispatch-plan.js,19
  plugins/koru-autopilot-vscode/out/dispatch-plan.test.js,117
  plugins/koru-autopilot-vscode/out/extension.js,702
  plugins/koru-autopilot-vscode/out/probe-ladder.js,220
  plugins/koru-autopilot-vscode/out/probe-ladder.test.js,48
  plugins/koru-autopilot-vscode/out/socketPath.js,100
  plugins/koru-autopilot-vscode/src/dispatch-plan.test.ts,123
  plugins/koru-autopilot-vscode/src/dispatch-plan.ts,27
  plugins/koru-autopilot-vscode/src/extension.ts,754
  plugins/koru-autopilot-vscode/src/probe-ladder.test.ts,79
  plugins/koru-autopilot-vscode/src/probe-ladder.ts,261
  plugins/koru-autopilot-vscode/src/socketPath.ts,67
  project.sh,54
  scripts/_koru_autodiag_filter_tickets.py,56
  scripts/autopilot-ide-autodetect-smoke.sh,183
  scripts/docker-ide-matrix-entrypoint.sh,32
  scripts/docker-ide-matrix.sh,93
  scripts/koru-autoloop-reset-diag-markers.sh,97
  scripts/koru-autoloop.sh,677
  scripts/koru-gate-capture.py,315
  scripts/koru-queue-diagnose.sh,125
  scripts/koru-semcod-gates.sh,100
  scripts/koru-soak-monitor.sh,129
  scripts/koru-soak-start.sh,40
  scripts/koru-soak-status.sh,100
  scripts/koru-soak-stop.sh,124
  scripts/planfile-export-prompt.sh,82
  scripts/planfile-sync-todo.py,261
  services/healing-webhook/app.py,703
  services/healing-webhook/ticket_builder.py,224
  src/koru/__init__.py,70
  src/koru/__main__.py,9
  src/koru/activity_log.py,68
  src/koru/agent_backend_runtime.py,181
  src/koru/agent_backends.py,215
  src/koru/agent_cli_helpers.py,88
  src/koru/agents.py,323
  src/koru/api/__init__.py,10
  src/koru/autoloop_cli.py,91
  src/koru/autonomous.py,2236
  src/koru/autonomous_cycle.py,1390
  src/koru/autonomous_diagnostics.py,259
  src/koru/autonomous_env.py,26
  src/koru/autonomous_parser.py,399
  src/koru/autonomous_process_guard.py,207
  src/koru/autonomous_startup.py,313
  src/koru/autonomous_wup.py,539
  src/koru/autonomy/__init__.py,25
  src/koru/autonomy/config.py,124
  src/koru/autonomy/env.py,305
  src/koru/autonomy/environment.py,246
  src/koru/autonomy/heal.py,117
  src/koru/autonomy/ide_work.py,302
  src/koru/autonomy/operator_pipeline.py,840
  src/koru/autonomy/post_run_verify.py,382
  src/koru/autonomy/prompts.py,102
  src/koru/autonomy/telemetry_snapshot.py,80
  src/koru/autopilot/__init__.py,19
  src/koru/autopilot/audit.py,10
  src/koru/autopilot/calibrate_cli.py,211
  src/koru/autopilot/cli_command.py,849
  src/koru/autopilot/client.py,11
  src/koru/autopilot/config.py,10
  src/koru/autopilot/daemon.py,17
  src/koru/autopilot/daemon_cli.py,110
  src/koru/autopilot/doctor_cli.py,153
  src/koru/autopilot/host_setup.py,10
  src/koru/autopilot/ide.py,10
  src/koru/autopilot/injector.py,10
  src/koru/autopilot/install_manager.py,585
  src/koru/autopilot/install_plugin_cli.py,427
  src/koru/autopilot/local_manager.py,67
  src/koru/autopilot/os_injector.py,10
  src/koru/autopilot/plugin_installer.py,10
  src/koru/autopilot/protocol.py,49
  src/koru/autopilot/systemd_cli.py,104
  src/koru/autopilot/tail_cli.py,74
  src/koru/autopilot/utils/__init__.py,6
  src/koru/autopilot/utils/client_helpers.py,58
  src/koru/bootstrap.py,453
  src/koru/cli/__init__.py,56
  src/koru/cli/__main__.py,8
  src/koru/cli/commands.py,1
  src/koru/cli/parsers.py,1
  src/koru/cli.py,1744
  src/koru/cli_doctor.py,87
  src/koru/cli_gate.py,117
  src/koru/cli_gc.py,88
  src/koru/cli_init.py,103
  src/koru/cli_queue.py,164
  src/koru/cli_scan.py,130
  src/koru/cli_topology.py,123
  src/koru/cli_watch.py,42
  src/koru/context.py,1254
  src/koru/context_render.py,472
  src/koru/dev_sync.py,134
  src/koru/doctor.py,546
  src/koru/dotenv_loader.py,105
  src/koru/dsl/__init__.py,10
  src/koru/events.py,91
  src/koru/gate.py,203
  src/koru/gc.py,372
  src/koru/gc_cli_helpers.py,82
  src/koru/ide_client.py,153
  src/koru/ide_router.py,99
  src/koru/ide_runtime.py,45
  src/koru/init.py,611
  src/koru/init_host_environment.py,315
  src/koru/local_manager_client.py,252
  src/koru/local_manager_state.py,292
  src/koru/local_service.py,313
  src/koru/loop.py,132
  src/koru/mcp_provision.py,450
  src/koru/mcp_server.py,10
  src/koru/planfile_queue.py,37
  src/koru/policy.py,263
  src/koru/project_pipeline.py,151
  src/koru/queue/__init__.py,39
  src/koru/queue/human.py,32
  src/koru/queue/koru_queue_argv.py,45
  src/koru/queue/local_manager.py,136
  src/koru/queue/locking.py,87
  src/koru/queue/loop.py,116
  src/koru/queue/planfile_ticket_note.py,56
  src/koru/queue/runner.py,394
  src/koru/queue/runners.py,250
  src/koru/queue/shell_evidence.py,73
  src/koru/queue/ticket.py,148
  src/koru/queue/types.py,89
  src/koru/queue_clean.py,392
  src/koru/queue_cli_helpers.py,291
  src/koru/redup_integration.py,190
  src/koru/refactor_planfile_handoff.py,47
  src/koru/run_log.py,124
  src/koru/runtime.py,105
  src/koru/scan.py,933
  src/koru/scripts/koru-autoloop.sh,677
  src/koru/semcod_tools.py,149
  src/koru/serve.py,10
  src/koru/stdio_events.py,50
  src/koru/tasks.py,228
  src/koru/tools.py,319
  src/koru/topology.py,415
  src/koru/topology_cli.py,76
  src/koru/utils/__init__.py,6
  src/koru/utils/subprocess_runner.py,41
  src/koru/watch.py,94
  src/koru/wup_testql_compat.py,65
  src/koruapi/__init__.py,26
  src/koruapi/cli.py,129
  src/koruapi/dashboard.py,91
  src/koruapi/dashboard_serve.py,1401
  src/koruapi/integrations.py,199
  src/koruapi/invoke.py,32
  src/koruapi/invoke_handlers.py,200
  src/koruapi/local.py,37
  src/koruapi/mcp.py,16
  src/koruapi/mcp_server.py,1041
  src/koruapi/openapi.py,156
  src/koruapi/runtime_insights.py,190
  src/koruapi/server.py,176
  src/koruapi/topology_post.py,69
  src/korudsl/__init__.py,26
  src/korudsl/cli.py,82
  src/korudsl/library.py,208
  src/korudsl/transform.py,71
  src/koruide/__init__.py,68
  src/koruide/audit.py,155
  src/koruide/client.py,129
  src/koruide/config.py,122
  src/koruide/daemon.py,897
  src/koruide/drive_orchestrator.py,201
  src/koruide/host_setup.py,227
  src/koruide/ide.py,680
  src/koruide/injector.py,407
  src/koruide/os_injector.py,401
  src/koruide/plugin_installer.py,495
  src/koruide/plugin_router.py,75
  src/koruide/plugin_version.py,9
  src/koruide/protocol.py,232
  src/koruide/socket.py,45
  src/koruide/utils.py,22
  tests/e2e/bootstrap.sh,94
  tests/e2e/init.sh,29
  tests/e2e/smoke.sh,112
  tests/test_activity_log.py,25
  tests/test_agent_backend_runtime.py,156
  tests/test_agent_backends.py,88
  tests/test_agent_backends_cli.py,34
  tests/test_agent_cli.py,108
  tests/test_agents.py,208
  tests/test_autoloop_cli.py,52
  tests/test_autonomous.py,2588
  tests/test_autonomous_diagnostics.py,71
  tests/test_autonomous_parser_detection.py,16
  tests/test_autonomous_process_detection.py,37
  tests/test_autonomous_scenarios.py,305
  tests/test_autonomous_startup.py,204
  tests/test_autonomy_config.py,141
  tests/test_autonomy_env.py,83
  tests/test_autonomy_environment.py,219
  tests/test_autonomy_prompts.py,162
  tests/test_autopilot_audit.py,125
  tests/test_autopilot_cli.py,1128
  tests/test_autopilot_client_drive_errors.py,16
  tests/test_autopilot_config.py,148
  tests/test_autopilot_daemon.py,1187
  tests/test_autopilot_host_setup.py,125
  tests/test_autopilot_ide.py,460
  tests/test_autopilot_injector.py,287
  tests/test_autopilot_jetbrains_scaffold.py,45
  tests/test_autopilot_os_injector.py,318
  tests/test_autopilot_plugin_installer.py,326
  tests/test_autopilot_protocol.py,154
  tests/test_autopilot_socket_path.py,36
  tests/test_bootstrap.py,298
  tests/test_cli.py,465
  tests/test_context.py,586
  tests/test_dashboard_topology_post.py,36
  tests/test_dev_sync.py,43
  tests/test_docker_e2e.py,582
  tests/test_docker_ide_matrix.py,63
  tests/test_docker_ide_matrix_config.py,116
  tests/test_docs_ide_control_surfaces.py,85
  tests/test_doctor.py,512
  tests/test_dotenv_loader.py,117
  tests/test_drive_orchestrator.py,115
  tests/test_e2e.py,1138
  tests/test_events.py,67
  tests/test_gate.py,167
  tests/test_gc.py,323
  tests/test_gc_cli_helpers.py,29
  tests/test_ide_client.py,115
  tests/test_ide_client_contract.py,106
  tests/test_ide_router.py,268
  tests/test_ide_runtime.py,39
  tests/test_ide_work.py,140
  tests/test_init.py,337
  tests/test_install_manager.py,382
  tests/test_koru_gate_capture.py,34
  tests/test_koru_queue_argv.py,24
  tests/test_koruapi.py,80
  tests/test_koruapi_transports.py,21
  tests/test_korudsl.py,31
  tests/test_koruide_bridges.py,78
  tests/test_koruide_client.py,83
  tests/test_local_service.py,265
  tests/test_loop.py,95
  tests/test_mcp_provision.py,277
  tests/test_mcp_server.py,245
  tests/test_operator_pipeline.py,446
  tests/test_planfile_queue.py,1222
  tests/test_plugin_router.py,67
  tests/test_policy.py,194
  tests/test_post_run_verify.py,156
  tests/test_pyproject_metadata.py,51
  tests/test_queue_clean.py,341
  tests/test_queue_cli_helpers.py,120
  tests/test_redup_integration.py,97
  tests/test_refactor_planfile_handoff.py,21
  tests/test_regix_taskfile.py,22
  tests/test_run_log.py,144
  tests/test_runtime.py,133
  tests/test_runtime_insights.py,60
  tests/test_scan.py,651
  tests/test_semcod_tools.py,51
  tests/test_serve.py,371
  tests/test_shell_evidence.py,51
  tests/test_stdio_autonomous_jsonl.py,99
  tests/test_tasks.py,77
  tests/test_tools.py,119
  tests/test_topology.py,55
  tests/test_topology_cli.py,28
  tests/test_watch.py,101
  tests/test_wup_taskfile.py,40
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
    e: _find_scripts_dir_with_settings,run_planfile,load_tickets,build_auto_section,replace_auto_section,do_from_planfile,_extract_todo_items,_resolve_import_labels,_create_ticket,do_from_todo,_llm_stub,main
    _find_scripts_dir_with_settings()
    run_planfile()
    load_tickets()
    build_auto_section(tickets)
    replace_auto_section(current;new_section)
    do_from_planfile(check)
    _extract_todo_items(text;heading)
    _resolve_import_labels(repo)
    _create_ticket(item;heading;todo_file_name;import_labels;existing_names;check)
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
    e: normalize_agent_lane_id,autopilot_backend_for_agent_id,_which,_marker,_detect_agent_commands,_build_cli_agent_option,detect_agent_options,detect_project_environment,detect_agent_environment,select_agent,save_agent_prompt,agent_lane_environment,format_agent_lane_exports,launch_agent,AgentOption
    AgentOption: to_dict(0)
    normalize_agent_lane_id(raw)
    autopilot_backend_for_agent_id(agent_id)
    _which(command)
    _marker(project)
    _detect_agent_commands()
    _build_cli_agent_option(agent_id;label;cmd;project;marker_name)
    detect_agent_options(project)
    detect_project_environment(project)
    detect_agent_environment(project)
    select_agent(agents)
    save_agent_prompt(project;prompt)
    agent_lane_environment(agent_id)
    format_agent_lane_exports(env)
    launch_agent(agent;project;prompt)
  src/koru/api/__init__.py:
  src/koru/autoloop_cli.py:
    e: _packaged_script_path,_build_parser,_env_from_assignments,autoloop_main
    _packaged_script_path()
    _build_parser()
    _env_from_assignments(assignments)
    autoloop_main(argv)
  src/koru/autonomous.py:
    e: _try_os_injector_fallback,_stdio_info,_daemon_activity_log,_allow_keyboard_autopilot_fallback,_effective_cycle_autopilot_enabled,_scan_while_waiting_input_enabled,_effective_cycle_scan_enabled,_resolve_autopilot_ide,_apply_agent_lane_environ,_command_project,_process_cwd,_ancestor_pids,_looks_like_autonomous_up_command,_find_existing_autonomous_processes,stop_prior_autonomous_for_auto_start,_find_existing_wup_processes,_as_managed,_terminate_existing_processes,_confirm_replace_existing,_guard_existing_autonomous_processes,_build_parser,_ensure_init,_current_koru_version,_daemon_status_version,_daemon_status_compatible,_stop_reused_daemon,_start_or_reuse_daemon,_status_has_autopilot_plugin,_wait_for_autopilot_plugin,_queue_loop_waiting_ticket_label,_is_topology_enabled,_current_head,_compute_backoff_sleep,_load_loop_checkpoint,_save_loop_checkpoint,_status_in_skip_list,_run_command_check,_create_diagnostic_ticket,_clear_diagnostic_marker,_read_wup_health,_run_idle_diagnostics,_run_cycle,_setup_autonomous_session,_setup_autopilot_daemon,_enable_autonomous_strict_plugin_policy,_configure_loop_state,_run_mcp_provision,_setup_autopilot_plugin,_run_operator_pipeline,_unblock_queue_if_needed,_restart_daemon_if_needed,_handle_cycle_exit_conditions,_cleanup_autonomous_session,_run_autonomous_cycle,_action_up,_argv_has_option,_expand_auto_up_defaults,_collect_argv_options,_user_option,_auto_value,_auto_pipeline_has_pressure,_auto_pipeline_stage,_select_auto_pipeline_profile,_update_auto_pipeline_state,autonomous_main,ExistingAutonomousProcess,ExistingManagedProcess,AutoPipelineState,AutoPipelineProfile
    ExistingAutonomousProcess:
    ExistingManagedProcess:
    AutoPipelineState:
    AutoPipelineProfile:
    _try_os_injector_fallback(prompt)
    _stdio_info(msg)
    _daemon_activity_log(msg)
    _allow_keyboard_autopilot_fallback()
    _effective_cycle_autopilot_enabled(enabled)
    _scan_while_waiting_input_enabled()
    _effective_cycle_scan_enabled(enabled)
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
    _current_koru_version()
    _daemon_status_version(status)
    _daemon_status_compatible(status)
    _stop_reused_daemon(client;socket_path)
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
    _enable_autonomous_strict_plugin_policy(args)
    _configure_loop_state(args;project)
    _run_mcp_provision(project;stdio_format)
    _setup_autopilot_plugin(args;autopilot_ide;socket_path;client)
    _run_operator_pipeline(args;project;startup_probe;plugin_connected;mcp_provision_ran;correlation_id)
    _unblock_queue_if_needed(project;stdio_format)
    _restart_daemon_if_needed(args;client;socket_path;daemon;thread;autopilot_socket_observed_at_boot;project)
    _handle_cycle_exit_conditions(args;queue_result;cycle;correlation_id)
    _cleanup_autonomous_session(previous_stdio_format_env;previous_sigterm;daemon;thread;wup_process;stdio_format)
    _run_autonomous_cycle()
    _action_up(args)
    _argv_has_option(argv;names)
    _expand_auto_up_defaults(argv)
    _collect_argv_options(argv)
    _user_option(options;names)
    _auto_value(args;names;attr;value)
    _auto_pipeline_has_pressure(state;max_iterations)
    _auto_pipeline_stage(state;max_iterations)
    _select_auto_pipeline_profile(args;state)
    _update_auto_pipeline_state(state;queue_result;diag_result;autopilot_status)
    autonomous_main(argv)
  src/koru/autonomous_cycle.py:
    e: _stdio_info,_queue_loop_waiting_ticket_label,_is_topology_enabled,_current_head,_status_in_skip_list,_allow_keyboard_autopilot_fallback,_prefer_keyboard_autopilot,_plugin_required_for_ide,_client_plugin_rows,_wanted_plugin_ide,_plugin_row_matches_ide,_plugin_row_version_block_reason,_missing_plugin_label,_client_has_usable_plugin,_try_os_injector_fallback,_run_command_check,_create_diagnostic_ticket,_clear_diagnostic_marker,_read_wup_health,_run_idle_diagnostics,_autopilot_event_path,_drain_autopilot_events,_initialize_cycle_telemetry,_heal_stale_socket,_handle_autopilot_events,_handle_queue_hygiene,_handle_post_run_verify_ide,_handle_scan_phase,_build_queue_command,_run_queue_loop,_emit_queue_iteration_event,_handle_post_run_verify,_handle_queue_loop_phase,_handle_scan_after_idle,_update_stagnation_state,_waiting_ticket_has_label,_handle_diagnostics,_check_autopilot_skip_conditions,_resolve_autopilot_drive_decision,_drive_autopilot_once,_reply_missing_autopilot_plugin,_reply_needs_focus_retry,_warn_autopilot_focus_retry,_execute_autopilot_drive,_update_autopilot_state,_log_autopilot_result,_handle_autopilot_phase,_emit_cycle_completion_events,run_cycle,DiagnosticResult,AutoloopState
    DiagnosticResult:
    AutoloopState:
    _stdio_info(msg)
    _queue_loop_waiting_ticket_label(queue_result)
    _is_topology_enabled(project;key)
    _current_head(project)
    _status_in_skip_list(status;skip_statuses)
    _allow_keyboard_autopilot_fallback()
    _prefer_keyboard_autopilot()
    _plugin_required_for_ide(autopilot_ide)
    _client_plugin_rows(client)
    _wanted_plugin_ide(autopilot_ide)
    _plugin_row_matches_ide(row;wanted)
    _plugin_row_version_block_reason(row;wanted)
    _missing_plugin_label(wanted)
    _client_has_usable_plugin(client;autopilot_ide)
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
    _build_queue_command(max_iterations;queue_name)
    _run_queue_loop(project;actor;queue_name;max_iterations)
    _emit_queue_iteration_event(queue_result;cycle;queue_name;actor;qcmd;_emit)
    _handle_post_run_verify(project;state;cycle;queue_result;verify_config;_hp;_emit)
    _handle_queue_loop_phase(project;state;cycle;actor;queue_name;max_iterations;topology_integration;verify_config;_hp;_emit)
    _handle_scan_after_idle(project;state;cycle;queue_result;scan_after_idle_queue;include_semcod_artifacts;scan_after_idle_min_interval_seconds;topology_integration;cycle_telemetry;_hp;_emit)
    _update_stagnation_state(state;queue_result)
    _waiting_ticket_has_label(project;queue_result;label)
    _handle_diagnostics(project;state;cycle;queue_result;idle_diagnostics;diagnostic_tickets;diagnostic_ticket_queue;diagnostic_ticket_priority;diagnostic_state_dir;wup_watch_enabled;wup_diagnostic_tickets;wup_ticket_queue;topology_integration;_hp;_emit)
    _check_autopilot_skip_conditions(project;queue_result;state;autopilot_action;autopilot_on_idle_only;autopilot_skip_on_diagnostics_fail;autopilot_skip_drive_idle_streak;autopilot_skip_statuses;diag_result;topology_integration;cycle_telemetry;_hp)
    _resolve_autopilot_drive_decision(project;state;queue_result)
    _drive_autopilot_once(client)
    _reply_missing_autopilot_plugin(reply)
    _reply_needs_focus_retry(reply)
    _warn_autopilot_focus_retry(attempt;attempts)
    _execute_autopilot_drive(project;state;queue_result;client;autopilot_ide;drive_prompt;submit;autopilot_action;_hp)
    _update_autopilot_state(state;ok;decision_kind;autopilot_drive_kind;decision_prompt)
    _log_autopilot_result(ok;queue_result;autopilot_ide;decision_kind;reply;_hp)
    _handle_autopilot_phase(project;state;cycle;queue_result;enable_autopilot;client;autopilot_ide;drive_prompt;submit;autopilot_action;autopilot_on_idle_only;autopilot_skip_on_diagnostics_fail;autopilot_skip_drive_idle_streak;autopilot_skip_statuses;diag_result;topology_integration;cycle_telemetry;_hp;_emit)
    _emit_cycle_completion_events(project;state;cycle;queue_result;diag_result;wup_health;autopilot_status;autopilot_ide;autopilot_backend;autopilot_drive_kind;cycle_telemetry;scan_after_idle_queue;scan_after_idle_min_interval_seconds;autopilot_skip_drive_idle_streak;_hp;_emit)
    run_cycle()
  src/koru/autonomous_diagnostics.py:
    e: _has_redup_module,build_idle_checks,run_idle_check_loop,create_diagnostic_ticket,clear_diagnostic_marker,run_command_check,read_wup_health,run_idle_diagnostics
    _has_redup_module()
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
    e: build_parser,_match_koru_auto_parts,looks_like_autonomous_up_command
    build_parser()
    _match_koru_auto_parts(parts)
    looks_like_autonomous_up_command(command)
  src/koru/autonomous_process_guard.py:
    e: command_project,process_cwd,ancestor_pids,find_existing_autonomous_processes,find_existing_wup_processes,as_managed,terminate_existing_processes,confirm_replace_existing,ExistingAutonomousProcess,ExistingManagedProcess
    ExistingAutonomousProcess:
    ExistingManagedProcess:
    command_project(command)
    process_cwd(pid)
    ancestor_pids(pid)
    find_existing_autonomous_processes(project)
    find_existing_wup_processes(project)
    as_managed(proc)
    terminate_existing_processes(processes)
    confirm_replace_existing(processes)
  src/koru/autonomous_startup.py:
    e: supports_autopilot_plugin_ide,koru_distribution_version,_session_label,_terminal_agent_lane_from_env,resolve_agent_lane_id,resolve_autopilot_ide_for_autonomous,build_startup_probe,format_startup_banner,format_post_startup_operator_hints,AutonomousStartupProbe
    AutonomousStartupProbe:
    supports_autopilot_plugin_ide(ide)
    koru_distribution_version()
    _session_label()
    _terminal_agent_lane_from_env()
    resolve_agent_lane_id(project;agent_lane_cli)
    resolve_autopilot_ide_for_autonomous(autopilot_ide_cli;lane)
    build_startup_probe(project)
    format_startup_banner(probe)
    format_post_startup_operator_hints(probe)
  src/koru/autonomous_wup.py:
    e: _wup_stdio_info,_wup_topology_gate,_build_wup_watch_config,_resolve_wup_testql_bin,_wup_cpu_throttle_arg,_wup_watch_command,_wup_autodetect,_wup_config_path,_load_project_env,_wup_subprocess_env,_parse_wup_services,_extract_docker_items,_profiled_compose_services,_compose_ps_command,_parse_compose_ps_json,_compose_service_ready,_wait_for_compose_service_ready,_ensure_wup_profiled_compose_services,_start_wup_watch,_stop_process,_load_wup_health,_identify_failing_services,_create_wup_diagnostic_tickets,_count_wup_events,_read_wup_health,WupWatchConfig,WupHealthResult,_WupEventState
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
    _wup_config_path(config)
    _load_project_env(project)
    _wup_subprocess_env(config)
    _parse_wup_services(config)
    _extract_docker_items(service)
    _profiled_compose_services(config)
    _compose_ps_command(compose_file;profiles;compose_service)
    _parse_compose_ps_json(raw)
    _compose_service_ready(items)
    _wait_for_compose_service_ready(config;compose_file;profiles;compose_service)
    _ensure_wup_profiled_compose_services(config)
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
    e: probe_ide_presence,probe_socket_health,_check_socket_health,_build_fixable_issues,_build_notes,probe_environment,IDEPresence,SocketHealth,EnvironmentReport
    IDEPresence: installed(0)  # Per-IDE detection result.
    SocketHealth: healthy(0)  # State of a Unix-socket file (typically autopilot).
    EnvironmentReport: installed_ides(0),mcp_enabled_ides(0)  # Snapshot of the autonomy-relevant environment.
    probe_ide_presence(project)
    probe_socket_health(path)
    _check_socket_health(autopilot_socket)
    _build_fixable_issues(socket_health;ides)
    _build_notes(headless;ides)
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
    e: _operator_state_dir,_marker_path,_read_marker,_write_marker,_clear_marker,_ticket_matches_step,_ticket_text,_ticket_matches_current_step,_find_ticket_by_id,_find_existing_step_ticket,_close_resolved_step_ticket,_mcp_koru_configured,_candidate_planfile_health_urls,_planfile_api_ok,_operator_autostart_server_enabled,_try_start_planfile_api,_os_profile_ok,_host_injectors_ok,build_operator_steps,_emit_step,_create_step_ticket,_ensure_planfile_api,_discard_stale_pending_marker,_close_finished_step_marker,_recover_matching_step_ticket,_create_pending_step_ticket,_process_operator_step,_emit_operator_step_event,run_startup_operator_pipeline,sys_stdout_for_format,OperatorStep,OperatorPipelineResult
    OperatorStep:
    OperatorPipelineResult:
    _operator_state_dir(project)
    _marker_path(state_dir;step_id)
    _read_marker(state_dir;step_id)
    _write_marker(state_dir;step_id;ticket_id)
    _clear_marker(state_dir;step_id)
    _ticket_matches_step(ticket)
    _ticket_text(ticket)
    _ticket_matches_current_step(ticket;step)
    _find_ticket_by_id(project;ticket_id)
    _find_existing_step_ticket(project)
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
    _ensure_planfile_api(project;stdio_format;correlation_id)
    _discard_stale_pending_marker(project;step)
    _close_finished_step_marker(project;step)
    _recover_matching_step_ticket(project;step)
    _create_pending_step_ticket(project;step)
    _process_operator_step(project;step;index;total;state_dir;create_tickets;ticket_queue;ticket_priority;stdio_format;result)
    _emit_operator_step_event(out;index;total;step;stdio_format;correlation_id)
    run_startup_operator_pipeline()
    sys_stdout_for_format(fmt)
  src/koru/autonomy/post_run_verify.py:
    e: _truthy_env,_extract_post_run_verify_block,_parse_verify_commands,_parse_verify_on_failure,_parse_verify_max_output,_parse_verify_ide_settings,load_post_run_verify_config,_parse_iso_datetime,fetch_ticket_status,fetch_recently_done_ticket_ids,_record_verify_outcomes,verify_after_ide_work,run_verify_commands,_truncate,apply_verify_failure,verify_completed_tickets,_HasIdeVerifyState,PostRunVerifyConfig
    _HasIdeVerifyState:
    PostRunVerifyConfig:
    _truthy_env(name)
    _extract_post_run_verify_block(raw)
    _parse_verify_commands(block)
    _parse_verify_on_failure(block)
    _parse_verify_max_output(block)
    _parse_verify_ide_settings(block)
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
  src/koru/autopilot/calibrate_cli.py:
    e: resolve_session_ides,action_calibrate,capture_ide_profile,detect_duplicate_coordinates,action_session_start
    resolve_session_ides(raw)
    action_calibrate(args)
    capture_ide_profile(ide;delay;args;captured)
    detect_duplicate_coordinates(captured)
    action_session_start(args)
  src/koru/autopilot/cli_command.py:
    e: _action_calibrate,_action_session_start,_build_parser,_client,_auto_direct_fallback_enabled,_should_fallback_to_direct,_print_drive_delay_message,_handle_os_injector_fallback,_run_direct_drive,_action_drive,_action_status,_action_shutdown,_action_doctor,_action_setup_host,_action_manage,_action_install_plugin,_action_install_plugin_jetbrains,_build_brief,_action_handoff,_action_tail,_action_install_unit,autopilot_main
    _action_calibrate(args)
    _action_session_start(args)
    _build_parser()
    _client(args)
    _auto_direct_fallback_enabled()
    _should_fallback_to_direct(args;reply)
    _print_drive_delay_message(delay_seconds)
    _handle_os_injector_fallback(args;profile_id;injector)
    _run_direct_drive(args;text)
    _action_drive(args)
    _action_status(args)
    _action_shutdown(args)
    _action_doctor(args)
    _action_setup_host(args)
    _action_manage(args)
    _action_install_plugin(args)
    _action_install_plugin_jetbrains(args)
    _build_brief(project)
    _action_handoff(args)
    _action_tail(args)
    _action_install_unit(args)
    autopilot_main(argv)
  src/koru/autopilot/client.py:
  src/koru/autopilot/config.py:
  src/koru/autopilot/daemon.py:
  src/koru/autopilot/daemon_cli.py:
    e: action_daemon,action_shutdown,action_ide_list
    action_daemon(args)
    action_shutdown(args)
    action_ide_list(_args)
  src/koru/autopilot/doctor_cli.py:
    e: doctor_fix_payload,render_doctor_session_info,render_doctor_backends,render_doctor_ides,render_doctor_fix_steps,render_doctor_text,render_doctor_json,action_doctor,action_setup_host
    doctor_fix_payload()
    render_doctor_session_info(injector;selected)
    render_doctor_backends(statuses)
    render_doctor_ides()
    render_doctor_fix_steps(fix_payload)
    render_doctor_text(injector;statuses;selected;fix_payload)
    render_doctor_json(injector;statuses;selected;fix_payload)
    action_doctor(args)
    action_setup_host(args)
  src/koru/autopilot/host_setup.py:
  src/koru/autopilot/ide.py:
  src/koru/autopilot/injector.py:
  src/koru/autopilot/install_manager.py:
    e: _source_root,_source_version,_package_version,_repo_koru_bin,_path_koru_bin,_is_pyenv_shim,_expected_plugin_version,_resolve_ide,_manager_socket_path,_daemon_status,_plugin_for_ide,_check_koru_path_issues,_check_pyenv_shim_issue,_check_version_mismatch_issue,_check_daemon_issues,_check_plugin_version_missing_issue,_check_plugin_installed_version_mismatch_issue,_check_plugin_installed_ok_but_not_connected_issue,_check_plugin_live_host_stale_issue,_check_plugin_version_mismatch_issue,_check_plugin_not_connected_issue,_issue_list,collect_install_manager_report,repair_installation,format_install_manager_report,ManagerIssue,InstallManagerReport
    ManagerIssue: to_dict(0)
    InstallManagerReport: to_dict(0)
    _source_root()
    _source_version(root)
    _package_version()
    _repo_koru_bin(root)
    _path_koru_bin()
    _is_pyenv_shim(path)
    _expected_plugin_version(root)
    _resolve_ide(raw)
    _manager_socket_path(ide;socket_path)
    _daemon_status(socket_path)
    _plugin_for_ide(status;ide)
    _check_koru_path_issues(path_koru;repo_koru)
    _check_pyenv_shim_issue(path_koru)
    _check_version_mismatch_issue(source_version;package_version)
    _check_daemon_issues(daemon)
    _check_plugin_version_missing_issue(daemon;plugin;ide)
    _check_plugin_installed_version_mismatch_issue(plugin;ide)
    _check_plugin_installed_ok_but_not_connected_issue(daemon;plugin;ide)
    _check_plugin_live_host_stale_issue(daemon;plugin;ide)
    _check_plugin_version_mismatch_issue(daemon;plugin;ide)
    _check_plugin_not_connected_issue(daemon;plugin;ide)
    _issue_list()
    collect_install_manager_report()
    repair_installation()
    format_install_manager_report(report)
  src/koru/autopilot/install_plugin_cli.py:
    e: plugin_repo_dir,_plugin_package_version,_versioned_plugin_vsix_candidates,jetbrains_plugin_repo_dir,resolve_plugin_vsix_path,resolve_jetbrains_plugin_dir,resolve_gradle_bin,resolve_jetbrains_plugin_artifact,ide_from_terminal_env,resolve_plugin_target_ide,resolve_plugin_editor_bin,render_install_plugin_dry_run,render_install_plugin_result,action_install_plugin,_render_jetbrains_failure,_render_jetbrains_success,action_install_plugin_jetbrains
    plugin_repo_dir()
    _plugin_package_version(plugin_dir)
    _versioned_plugin_vsix_candidates(plugin_dir)
    jetbrains_plugin_repo_dir()
    resolve_plugin_vsix_path(vsix)
    resolve_jetbrains_plugin_dir(raw_dir)
    resolve_gradle_bin(raw)
    resolve_jetbrains_plugin_artifact(plugin_dir)
    ide_from_terminal_env()
    resolve_plugin_target_ide(raw_ide)
    resolve_plugin_editor_bin(ide)
    render_install_plugin_dry_run(ide;editor_bin;vsix_path;cmd;output_format)
    render_install_plugin_result(ide;editor_bin;cmd;ok;stdout;stderr;output_format)
    action_install_plugin(args)
    _render_jetbrains_failure()
    _render_jetbrains_success()
    action_install_plugin_jetbrains(args)
  src/koru/autopilot/local_manager.py:
    e: autopilot_local_manager_session,start_autopilot_manager_heartbeat
    autopilot_local_manager_session()
    start_autopilot_manager_heartbeat(manager;daemon)
  src/koru/autopilot/os_injector.py:
  src/koru/autopilot/plugin_installer.py:
  src/koru/autopilot/protocol.py:
  src/koru/autopilot/systemd_cli.py:
    e: systemd_user_dir,resolve_koru_bin,render_unit,action_install_unit
    systemd_user_dir()
    resolve_koru_bin()
    render_unit(koru_bin)
    action_install_unit(args)
  src/koru/autopilot/tail_cli.py:
    e: format_tail_entry,render_tail_json,render_tail_text,action_tail
    format_tail_entry(entry)
    render_tail_json(tail)
    render_tail_text(tail)
    action_tail(args)
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
    e: _env_truthy,_command_value,_cli_version,_build_parser,_build_tools_parser,_tools_main,_build_task_parser,_build_serve_parser,_build_local_serve_parser,_build_gate_parser,_gate_main,_build_gc_parser,_gc_main,_build_queue_parser,_render_clean_report_text,_queue_main,_build_agent_parser,_task_main,_serve_main,_local_serve_main,_agent_main,_is_bare_invocation,_build_topology_parser,_render_topology_text,_topology_main,_build_runtime_context_parser,_render_runtime_context_text,_runtime_context_main,_init_ci_main,_mcp_serve_main,_agent_backends_main,_init_ide_main,_refactor_planfile_handoff_main,ide_router_main,_dsl_main,_api_main,_peek_project_from_argv,_auto_main,_doctor_main,_doctor_fix_payload,_render_doctor_with_fix,_init_main,_init_agent_lane_main,_context_main,_bootstrap_main,_watch_main,_queue_run_main,_command_loop_main,main
    _env_truthy(name)
    _command_value(value)
    _cli_version()
    _build_parser()
    _build_tools_parser()
    _tools_main(argv)
    _build_task_parser()
    _build_serve_parser()
    _build_local_serve_parser()
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
  src/koru/cli_doctor.py:
    e: doctor_fix_payload,render_doctor_with_fix,doctor_main
    doctor_fix_payload(report)
    render_doctor_with_fix(report;fix_payload)
    doctor_main(args;raw_args)
  src/koru/cli_gate.py:
    e: build_gate_parser,gate_main
    build_gate_parser()
    gate_main(argv)
  src/koru/cli_gc.py:
    e: build_gc_parser,gc_main
    build_gc_parser()
    gc_main(argv)
  src/koru/cli_init.py:
    e: init_main,init_agent_lane_main
    init_main(args)
    init_agent_lane_main(args)
  src/koru/cli_queue.py:
    e: build_queue_parser,render_clean_report_text,queue_main
    build_queue_parser()
    render_clean_report_text(report)
    queue_main(argv)
  src/koru/cli_scan.py:
    e: build_scan_parser,render_scan_text,render_scan_markdown,scan_main
    build_scan_parser()
    render_scan_text(result)
    render_scan_markdown(result)
    scan_main(argv)
  src/koru/cli_topology.py:
    e: build_topology_parser,render_topology_text,topology_main
    build_topology_parser()
    render_topology_text(topology)
    topology_main(argv)
  src/koru/cli_watch.py:
    e: watch_main
    watch_main(args)
  src/koru/context.py:
    e: _is_fixture_ticket,_resolve_include_fixtures,_load_project_dotenv,_planfile_command_base,_planfile_env,_fetch_all_tickets,_run_planfile,_safe_json,_git_probe,_build_ticket_args,_try_fallback_ticket_list,_process_list_payload,_process_dict_payload,_extract_error_from_stderr,_execute_ticket_query,_handle_idle_queue,_parse_ticket_response,_fetch_ticket_data,build_context,_load_sprint_data,_find_blocking_tickets,_promote_blocking_to_critical,_promote_bug_priority,_write_sprint_data,_auto_promote_blocking_tickets,_build_instructions,_build_setup_instructions,_build_policy_rules,_build_ticket_rules,_build_shared_rules,_build_self_service,_render_header,_render_environment,_render_agent_lanes,_render_autonomous_mode,_render_ai_tool_support_2026,_render_semcod_tools,_render_setup_required,_render_active_ticket,_compact_ticket_error,_render_no_active_ticket,_render_gates,_render_project_pipeline,_render_policy,_render_rules,_render_self_service,_render_dashboard,_render_autonomy_loop_brief,render_markdown_handoff
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
    _execute_ticket_query(project;ticket_id;queue_name;planfile_runner)
    _handle_idle_queue(project;planfile_runner;include_fixtures)
    _parse_ticket_response(ticket_proc;ticket_id;include_fixtures;project;planfile_runner)
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
    _build_policy_rules(policy)
    _build_ticket_rules(ticket)
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
    _compact_ticket_error(ticket_error)
    _render_no_active_ticket(ticket_error)
    _render_gates(markers)
    _render_project_pipeline(pipeline)
    _render_policy(policy)
    _render_rules(instructions)
    _render_self_service(self_service)
    _render_dashboard()
    _render_autonomy_loop_brief(ctx)
    render_markdown_handoff(context)
  src/koru/context_render.py:
    e: render_header,render_environment,render_agent_lanes,render_autonomous_mode,render_ai_tool_support_2026,render_semcod_tools,render_setup_required,render_active_ticket,_compact_ticket_error,render_no_active_ticket,render_gates,render_project_pipeline,render_policy,render_rules,render_self_service,render_dashboard,render_autonomy_loop_brief,render_markdown_handoff
    render_header(project)
    render_environment(env;project)
    render_agent_lanes(agents)
    render_autonomous_mode()
    render_ai_tool_support_2026()
    render_semcod_tools(semcod_tools)
    render_setup_required(project)
    render_active_ticket(ticket)
    _compact_ticket_error(ticket_error)
    render_no_active_ticket(ticket_error)
    render_gates(markers)
    render_project_pipeline(pipeline)
    render_policy(policy)
    render_rules(instructions)
    render_self_service(self_service)
    render_dashboard()
    render_autonomy_loop_brief(ctx)
    render_markdown_handoff(context)
  src/koru/dev_sync.py:
    e: _default_semcod_root,_run,_is_dirty,_pull_repo,sync_developer_packages,dev_main,SyncItem
    SyncItem:
    _default_semcod_root()
    _run(command;cwd)
    _is_dirty(repo;runner)
    _pull_repo(repo;runner)
    sync_developer_packages()
    dev_main(argv)
  src/koru/doctor.py:
    e: run_diagnostics,_check_agent_backends_registry,_check_git_repo,_check_planfile_binary,_planfile_version_argv,_check_koru_package_version,_check_planfile_cli_version,_check_planfile_config,_check_planfile_sprints,_check_planfile_sprints_yaml,_check_runtime_dir,_check_koru_project_pipeline,_check_policy_yaml,_check_gitignore,_resolve_pytest_collect_timeout,_check_pytest_collect,_check_inotify_watches,_check_wup_binary,_check_ci_command,render_text,Check,DoctorReport
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
    _check_inotify_watches(project)
    _check_wup_binary(_project)
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
    InitReport: _env_bit(0),_lane_summary(0),_init_summary(0),summary(0)  # Summary of what ``init_project`` actually changed on disk.
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
    e: _read_os_release,_id_group_names,_uinput_snapshot,build_host_environment_report,_build_backend_steps,_build_pm_steps,_recommended_next_steps,_render_session_section,_render_os_section,_render_injector_section,_render_clipboard_section,_render_uinput_section,_render_next_steps_section,_render_human_actions_section,_render_apt_suggestion_section,_render_host_environment_md,write_host_environment_bundle
    _read_os_release()
    _id_group_names()
    _uinput_snapshot()
    build_host_environment_report()
    _build_backend_steps(session;selected;groups)
    _build_pm_steps(pm;base)
    _recommended_next_steps(base;groups)
    _render_session_section(report)
    _render_os_section(report)
    _render_injector_section(report)
    _render_clipboard_section(report)
    _render_uinput_section(report)
    _render_next_steps_section(report)
    _render_human_actions_section(report)
    _render_apt_suggestion_section(report)
    _render_host_environment_md(report)
    write_host_environment_bundle(project)
  src/koru/local_manager_client.py:
    e: _truthy,_koru_version,default_local_manager_url,lifecycle_decision_action,lifecycle_should_stop,LocalManagerClient,LocalManagerSession
    LocalManagerClient: from_env(1),enabled(0),post(2),register_worker(0),heartbeat_worker(0),claim_action(0),complete_action(0)  # Tiny JSON-over-HTTP client for ``koru local-serve``.
    LocalManagerSession: enabled(0),start(0),heartbeat(0),should_stop(0),complete(0)  # Small lifecycle session for one CLI worker invocation.
    _truthy(raw)
    _koru_version()
    default_local_manager_url()
    lifecycle_decision_action(reply)
    lifecycle_should_stop(reply)
  src/koru/local_manager_state.py:
    e: utc_now,koru_version,normalize_capabilities,_action_type,_required_capabilities,_version_key,EventBuffer,ActionQueue,WorkerRegistry,ServiceState
    EventBuffer: __init__(1),append(1),snapshot(0)  # Thread-safe ring of recent event records (oldest dropped at 
    ActionQueue: __init__(1),enqueue(3),claim(0),complete(0),snapshot(0)  # Single in-process queue for local koru actions with simple l
    WorkerRegistry: __init__(0),register(1),heartbeat(1),_reconcile_locked(0),_reply_locked(1),snapshot(0)  # Registry and lifecycle policy for versioned koru workers.
    ServiceState: __init__(1)
    utc_now()
    koru_version()
    normalize_capabilities(raw)
    _action_type(payload)
    _required_capabilities(payload)
    _version_key(raw)
  src/koru/local_service.py:
    e: _env_int,_read_bounded_json_object,default_local_service_config,_build_handler,build_local_service_server,run_local_service,start_local_service_background,LocalServiceConfig
    LocalServiceConfig:  # Configuration for ``koru local-serve``.
    _env_int(name;default)
    _read_bounded_json_object(handler)
    default_local_service_config()
    _build_handler(state;koru_version)
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
    e: _windsurf_global_config,_cursor_project_config,_vscode_project_config,_windsurf_project_config,_zed_project_settings,_resolved_koru_command,_koru_mcp_entry,_koru_mcp_entry_cursor,_maybe_upgrade_koru_command,detect_ides,_read_json,_write_json,provision_windsurf,provision_cursor,provision_vscode,provision_vscodium,provision_zed,remove_from_config,ensure_koru_mcp_not_disabled,_resolve_targets,_removal_paths_for_ide,_apply_target,_render_results,init_ide_main
    _windsurf_global_config()
    _cursor_project_config(project)
    _vscode_project_config(project)
    _windsurf_project_config(project)
    _zed_project_settings(project)
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
    provision_vscodium(project)
    provision_zed(project)
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
    e: policy_path,load_policy,_check_git_commit_policy,_check_git_push_policy,_check_git_branch_create_policy,_check_git_branch_switch_policy,_check_git_tag_policy,_check_destructive_shell_policy,policy_violations,Policy
    Policy: to_dict(0)  # Resolved policy for an LLM agent operating on a koru project
    policy_path(project)
    load_policy(project)
    _check_git_commit_policy(policy;command;violations)
    _check_git_push_policy(policy;command;violations)
    _check_git_branch_create_policy(policy;command;violations)
    _check_git_branch_switch_policy(policy;command;violations)
    _check_git_tag_policy(policy;command;violations)
    _check_destructive_shell_policy(policy;command;violations)
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
  src/koru/queue/local_manager.py:
    e: queue_local_manager_session,queue_manager_start,queue_manager_health,queue_manager_decision_action,queue_manager_stop_callback,queue_manager_complete,QueueManagerEarlyExit
    QueueManagerEarlyExit:
    queue_local_manager_session(args)
    queue_manager_start(args;manager)
    queue_manager_health(result)
    queue_manager_decision_action(reply)
    queue_manager_stop_callback(manager)
    queue_manager_complete(manager)
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
    e: _source_tool,_resolve_executor_kind,_handle_human_ticket,_resolve_ticket_action,_handle_dry_run,_claim_and_start,_execute_action,_append_shell_evidence,_finalize_ticket,run_next_planfile_task
    _source_tool(ticket)
    _resolve_executor_kind(ticket;interactive;dry_run)
    _handle_human_ticket(ticket;ticket_id;interactive;dry_run;project;actor;planfile_runner;prompt_runner)
    _resolve_ticket_action(ticket;executor_kind)
    _handle_dry_run(ticket_id;executor_kind;action)
    _claim_and_start(project;ticket_id;actor;planfile_runner)
    _execute_action(executor_kind;action;project;ticket_id;api_runner;llm_runner;shell_runner)
    _append_shell_evidence(project;ticket_id;result;planfile_runner)
    _finalize_ticket(project;ticket_id;executor_kind;result;action_label;planfile_runner)
    run_next_planfile_task()
  src/koru/queue/runners.py:
    e: _planfile_env,run_process,run_shell_command,run_api_request,_resolve_llm_endpoint_and_key,_build_llm_messages,_build_llm_request_body,_build_llm_headers,_parse_llm_response,_handle_llm_error,run_llm_request
    _planfile_env()
    run_process(command;project)
    run_shell_command(command;project)
    run_api_request(request;_project)
    _resolve_llm_endpoint_and_key(request)
    _build_llm_messages(request)
    _build_llm_request_body(request;model;messages)
    _build_llm_headers(endpoint;api_key)
    _parse_llm_response(response;model)
    _handle_llm_error(exc;model)
    run_llm_request(request;_project)
  src/koru/queue/shell_evidence.py:
    e: _tail_stream,format_shell_run_note
    _tail_stream(text;limit)
    format_shell_run_note()
  src/koru/queue/ticket.py:
    e: parse_next_ticket,ticket_command,ticket_llm_request,ticket_api_request,_has_planfile_cli_module,planfile_command,result_json
    parse_next_ticket(stdout)
    ticket_command(ticket)
    ticket_llm_request(ticket)
    ticket_api_request(ticket)
    _has_planfile_cli_module()
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
    e: _redup_module_command,redup_scan_command,redup_check_command,redup_changed_scan_command,redup_changed_scan_runner_command,_redup_scan_supports,_redup_json_scan_command,_env_bool,_write_skipped_changed_report,run_changed_scan,main
    _redup_module_command()
    redup_scan_command(path)
    redup_check_command(path)
    redup_changed_scan_command(path)
    redup_changed_scan_runner_command()
    _redup_scan_supports(option)
    _redup_json_scan_command(path)
    _env_bool(name)
    _write_skipped_changed_report(output)
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
    e: scan_pytest_collect,_load_koruignore_patterns,_is_koruignored,scan_todo_markers,scan_missing_gates,scan_missing_tools,scan_gitignore_drift,_scan_jscpd_report,_find_analysis_file,_parse_dup_suggestions,_parse_god_module_suggestions,_parse_high_cc_suggestions,_parse_refactor_suggestions,_scan_code2llm_analysis,_scan_testql_export,_scan_redup_filtered,_scan_redup_changed,scan_semcod_quality_artifacts,collect_suggestions,_existing_scan_titles,_create_ticket,run_scan,Suggestion,ScanResult
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
    _find_analysis_file(project)
    _parse_dup_suggestions(text;rel)
    _parse_god_module_suggestions(text;rel)
    _parse_high_cc_suggestions(text;rel)
    _parse_refactor_suggestions(text;rel)
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
    e: default_registry_path,resolve_registry_path,load_tool_registry,_first_token,_extract_detect_config,_check_commands_exist,_check_markers_exist,_check_env_vars_exist,_build_detection_result,detect_tools,find_tool_entry,infer_adapter_kind,_extract_tool_metadata,_validate_adapter_kind,_build_scaffold_prompt_lines,_build_scaffold_labels,_build_scaffold_inputs,build_tool_task_scaffold,render_tools_detect_text
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
    _extract_tool_metadata(tool)
    _validate_adapter_kind(tool;adapter_kind)
    _build_scaffold_prompt_lines(metadata;plugin_bridge;kind)
    _build_scaffold_labels(metadata;plugin_bridge)
    _build_scaffold_inputs(metadata;plugin_bridge;kind)
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
    e: _list_tickets,_bulk_waiting_input_action,_address_in_use,_listener_pids_for_tcp_port,_cmdline_suggests_koru_serve_from_bytes,_cmdline_suggests_koru_serve,_try_stop_prior_koru_serve_listener,serve_endpoint_path,read_serve_endpoint,_build_handler,build_server,write_serve_endpoint_file,bind_serve_server,serve,start_serve_background,ServeConfig
    ServeConfig:
    _list_tickets(project)
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
  src/koruapi/runtime_insights.py:
    e: _run_ps,_looks_project_related,_classify_process,_active_tools,_top_processes,collect_runtime_insights
    _run_ps()
    _looks_project_related(args;project)
    _classify_process(proc;project)
    _active_tools(processes;project)
    _top_processes(processes;project)
    collect_runtime_insights(project)
  src/koruapi/server.py:
    e: _json_response,_read_json_body,_parse_invoke_request,_handle_invoke_post,serve,KoruAPIHandler
    KoruAPIHandler: log_message(1),do_GET(0),do_POST(0)
    _json_response(handler;status;payload)
    _read_json_body(handler)
    _parse_invoke_request(body;default_project)
    _handle_invoke_post(handler)
    serve()
  src/koruapi/topology_post.py:
    e: apply_topology_post_update
    apply_topology_post_update(project;body)
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
    e: _daemon_package_version,_env_truthy,_prefer_keyboard_drive,_plugin_rejection_log_interval_seconds,_load_context_module,_default_handoff,_peer_uid,_Client,AutopilotDaemon
    _Client:  # In-memory state for one connected socket.
    AutopilotDaemon: __init__(0),start(0),serve_forever(0),stop(0),_shutdown(0),_accept(0),_on_readable(1),_dispatch(2),_send(2),_drop(1),_plugin_for(1),_handle_drive(2),_drive_via_plugin(6),_try_os_injector_drive(3),_drive_via_keyboard(5),_handle_hello(2),_log_rejected_plugin_connection(0),_handle_status(2),_plugin_ack_needs_os_fallback(0),_relay_os_fallback_ack(6),_relay_message_sent_ack(2),_handle_ack(2),_event_path(0),_append_event(2),_handle_plugin_event(2),_handle_shutdown(2),_handle_ping(2),_build_handler_table(0)  # Selector-based unix-socket broker.
    _daemon_package_version()
    _env_truthy(name)
    _prefer_keyboard_drive()
    _plugin_rejection_log_interval_seconds()
    _load_context_module()
    _default_handoff(project)
    _peer_uid(sock)
  src/koruide/drive_orchestrator.py:
    e: DriveOrchestrator
    DriveOrchestrator: plugin_required_message(1),should_try_os_fallback(0),build_message_sent_info(0),annotate_plugin_ack(0),strict_plugin_ack_required(0),expected_plugin_version(0),strict_plugin_version_required(0),plugin_version_info(0),should_block_plugin_version(1),plugin_version_block_message(1),should_fail_strict_plugin_ack(0),plugin_ack_summary(1)  # Pure helpers used by the autopilot daemon.
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
    e: normalize_ide_id,supported_autopilot_ide_ids,autopilot_ide_choices,vscode_extension_plugin_ide_ids,supports_vscode_extension_plugin,_iter_proc_pids,_read_comm,_read_cmdline,_read_exe,_matches,_score_comm_name,_score_windsurf_exe_path,_score_primary_exe_path,_score_exe_path,_score_cmdline_flags,_candidate_score,detect_running_ides,_active_window_pid_x11,_ide_id_from_process,detect_focused_ide_id,_vscode_family_env_present,_vscode_family_flavor_from_env,_cursor_terminal_env_hint,_windsurf_primary_terminal_env_hint,_vscode_family_terminal_hint,_known_terminal_ide_hint,_legacy_windsurf_terminal_env_hint,_terminal_ide_from_env,_terminal_ide_from_parent_chain,detect_terminal_host_ide_id,focused_ide,pick_target,is_linux,detect_running_ides_cached,clear_detect_cache,_has_os_injector_profile,_auto_profile_candidate_ids,_resolve_explicit_drive_target,_resolve_auto_drive_target,resolve_drive_target,RunningIDE
    RunningIDE: to_dict(0)  # A single IDE process discovered on the system.
    normalize_ide_id(raw)
    supported_autopilot_ide_ids()
    autopilot_ide_choices()
    vscode_extension_plugin_ide_ids()
    supports_vscode_extension_plugin(ide)
    _iter_proc_pids()
    _read_comm(pid)
    _read_cmdline(pid)
    _read_exe(pid)
    _matches(comm;cmdline;patterns)
    _score_comm_name(ide_id;comm)
    _score_windsurf_exe_path(exe_l)
    _score_primary_exe_path(ide_id;exe_l)
    _score_exe_path(ide_id;exe)
    _score_cmdline_flags(cmdline)
    _candidate_score(ide_id;pid;comm;cmdline;exe)
    detect_running_ides()
    _active_window_pid_x11()
    _ide_id_from_process(pid)
    detect_focused_ide_id()
    _vscode_family_env_present()
    _vscode_family_flavor_from_env()
    _cursor_terminal_env_hint(chrome_ide)
    _windsurf_primary_terminal_env_hint(chrome_ide)
    _vscode_family_terminal_hint(term_program)
    _known_terminal_ide_hint(term_ide;chrome_ide)
    _legacy_windsurf_terminal_env_hint(chrome)
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
    e: _valid_ide,_ide_from_terminal_env,_terminal_vscode_flavor,_repo_root,_plugin_package_version,_versioned_vsix_candidates,_running_vscode_flavor,_vscode_flavor,resolve_target_ide,resolve_extension_vsix,_resolve_ide_command,_settings_path_for_ide,_configure_socket_path,_run,_env_reassert_extension_install,_extension_is_installed,_parse_extension_version,installed_extension_version_for_ide,_reassert_extension_extra,_result_already_installed,_install_extension_vsix,install_plugin_for_ide,format_plugin_install_result,PluginInstallResult
    PluginInstallResult: to_dict(0)
    _valid_ide(raw)
    _ide_from_terminal_env()
    _terminal_vscode_flavor()
    _repo_root()
    _plugin_package_version(plugin_dir)
    _versioned_vsix_candidates(plugin_dir)
    _running_vscode_flavor()
    _vscode_flavor()
    resolve_target_ide(requested)
    resolve_extension_vsix()
    _resolve_ide_command(ide)
    _settings_path_for_ide(ide)
    _configure_socket_path(ide;socket_path)
    _run(cmd)
    _env_reassert_extension_install()
    _extension_is_installed(command;runner)
    _parse_extension_version(output)
    installed_extension_version_for_ide(ide)
    _reassert_extension_extra(command)
    _result_already_installed(target;command)
    _install_extension_vsix(target;command;vsix)
    install_plugin_for_ide()
    format_plugin_install_result(result)
  src/koruide/plugin_router.py:
    e: PluginClient,PluginStatusRow,PluginRouter
    PluginClient:
    PluginStatusRow: to_dict(0)
    PluginRouter: __init__(1),plugin_for(1),drop_stale_plugins(2),status_rows(0)  # Select, enumerate and deduplicate connected plugin sessions.
  src/koruide/plugin_version.py:
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
  tests/test_autoloop_cli.py:
    e: test_packaged_autoloop_script_matches_repo_script,test_autoloop_print_script,test_autoloop_runs_packaged_script_with_env_assignments
    test_packaged_autoloop_script_matches_repo_script()
    test_autoloop_print_script(capsys)
    test_autoloop_runs_packaged_script_with_env_assignments(tmp_path)
  tests/test_autonomous.py:
    e: test_effective_flags_matrix,test_scan_after_idle_queue_runs_scan_when_queue_idle,test_scan_after_idle_min_interval_skips_second_scan,test_idle_streak_skip_increments_telemetry,test_ticket_sources_env_overrides_cli_queue_to_scan,test_ticket_sources_env_invalid_keeps_cli_queue,test_autonomous_environ_doctor_probe_invalid_ticket_sources,test_autonomous_environ_doctor_probe_pass_summary,test_looks_like_autonomous_matches_koru_cli_auto,test_looks_like_autonomous_matches_koru_autonomous_regex,test_auto_main_argv_injects_replace_existing,test_auto_invocation_uses_full_autonomous_defaults,test_auto_invocation_can_enable_adaptive_pipeline,test_auto_pipeline_profiles_escalate_when_queue_stays_idle,test_effective_cycle_autopilot_skips_required_plugin_when_missing,test_effective_cycle_autopilot_allows_non_plugin_required_ide,test_effective_cycle_scan_skips_after_waiting_input,test_effective_cycle_scan_waiting_override,test_build_queue_command_omits_unsupported_all_queues_flag,test_stop_prior_autonomous_for_auto_start_terminates,test_guard_existing_autonomous_noninteractive_blocks_duplicate,test_guard_existing_autonomous_replace_existing_terminates,test_guard_existing_autonomous_replace_existing_terminates_stale_wup,test_guard_existing_autonomous_interactive_decline_blocks_duplicate,test_autonomous_jsonl_keyboard_interrupt_emits_reason,test_queue_loop_result_summary_includes_waiting_ticket,test_queue_loop_waiting_ticket_label_helper,test_resolve_autopilot_ide_env_overrides_cli,test_resolve_autopilot_ide_ignores_bad_env,test_resolve_autopilot_ide_auto_env_does_not_override_cli,test_resolve_autopilot_ide_headless_forces_auto,test_resolve_autopilot_ide_headless_allow_autopilot_honors_env,test_resolve_autopilot_ide_koru_ide_mode_headless,test_resolve_autopilot_ide_ssh_without_display_headless,test_resolve_autopilot_ide_ssh_with_display_uses_cli,test_resolve_autopilot_ide_os_environ_autopilot_ide,test_resolve_autopilot_ide_headless_allow_yes,_isolate_integrated_terminal_env,test_apply_agent_lane_environ_auto_cursor,test_apply_agent_lane_environ_auto_prefers_vscode_terminal,test_apply_agent_lane_environ_auto_prefers_vscodium_terminal,test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env,test_apply_agent_lane_environ_none_is_noop,test_autonomous_main_prepends_up_for_flags,test_up_single_cycle_queue_only_no_autopilot,test_safe_up_uses_queue_diagnostics_without_autopilot,test_up_single_cycle_all_sources_runs_scan,test_up_auto_installs_plugin_before_autopilot_loop,test_setup_autopilot_plugin_unsupported_skips_wait,test_status_has_autopilot_plugin_matches_specific_ide,test_status_has_autopilot_plugin_rejects_stale_plugin_when_strict,test_autonomous_defaults_to_strict_plugin_policy,test_autonomous_respects_explicit_plugin_version_policy,test_wait_for_autopilot_plugin_polls_until_connected,test_start_or_reuse_daemon_reuses_current_version,test_start_or_reuse_daemon_restarts_daemon_without_version,test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message,test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list,test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping,test_run_cycle_drives_llm_ready_waiting_ticket_without_stagnation_skip,test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure,test_run_cycle_plugin_required_failure_skips_os_injector_fallback,test_run_cycle_autopilot_focus_error_retry_loop_retries_and_warns,test_run_cycle_does_not_retry_missing_plugin_as_focus_error,test_run_cycle_skips_drive_when_required_plugin_missing,test_run_cycle_visible_typing_does_not_require_plugin,test_run_cycle_jetbrains_does_not_require_plugin_by_default,_fast_autonomous_up,test_up_keeps_running_on_waiting_input_by_default,test_up_stops_on_waiting_input_when_flag_set,test_up_restarts_autopilot_when_socket_disappears_between_cycles,test_compute_backoff_sleep_caps_stagnation,test_env_apply_autoloop_defaults_enables_full_diagnostics,test_run_idle_diagnostics_profile_off_message,test_run_idle_diagnostics_creates_deduped_ticket,test_wup_watch_command_uses_testql_mode,test_wup_watch_command_prefers_project_venv_wrapper,test_wup_watch_command_keeps_explicit_testql_bin,test_wup_watch_command_normalizes_percent_cpu_throttle,test_wup_subprocess_env_loads_project_wup_env,test_start_wup_watch_passes_playwright_env,test_wup_profiled_compose_services_start_before_watch,test_wup_compose_ps_accepts_json_lines,test_wup_topology_gate_uses_pipeline_for_gate_wup,test_read_wup_health_creates_high_priority_planfile_ticket,test_read_wup_health_ignores_degraded_fleet_and_clears_marker
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
    test_auto_invocation_uses_full_autonomous_defaults(tmp_path;monkeypatch)
    test_auto_invocation_can_enable_adaptive_pipeline(tmp_path;monkeypatch)
    test_auto_pipeline_profiles_escalate_when_queue_stays_idle()
    test_effective_cycle_autopilot_skips_required_plugin_when_missing(monkeypatch)
    test_effective_cycle_autopilot_allows_non_plugin_required_ide()
    test_effective_cycle_scan_skips_after_waiting_input(monkeypatch)
    test_effective_cycle_scan_waiting_override(monkeypatch)
    test_build_queue_command_omits_unsupported_all_queues_flag()
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
    test_apply_agent_lane_environ_auto_prefers_vscodium_terminal(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env(tmp_path;monkeypatch)
    test_apply_agent_lane_environ_none_is_noop(tmp_path;monkeypatch)
    test_autonomous_main_prepends_up_for_flags(tmp_path;monkeypatch)
    test_up_single_cycle_queue_only_no_autopilot(tmp_path;monkeypatch)
    test_safe_up_uses_queue_diagnostics_without_autopilot(tmp_path;monkeypatch)
    test_up_single_cycle_all_sources_runs_scan(tmp_path;monkeypatch)
    test_up_auto_installs_plugin_before_autopilot_loop(tmp_path;monkeypatch)
    test_setup_autopilot_plugin_unsupported_skips_wait(tmp_path;monkeypatch)
    test_status_has_autopilot_plugin_matches_specific_ide(monkeypatch)
    test_status_has_autopilot_plugin_rejects_stale_plugin_when_strict(monkeypatch)
    test_autonomous_defaults_to_strict_plugin_policy(monkeypatch)
    test_autonomous_respects_explicit_plugin_version_policy(monkeypatch)
    test_wait_for_autopilot_plugin_polls_until_connected(monkeypatch)
    test_start_or_reuse_daemon_reuses_current_version(tmp_path;monkeypatch)
    test_start_or_reuse_daemon_restarts_daemon_without_version(tmp_path;monkeypatch)
    test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message(tmp_path;monkeypatch)
    test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list(tmp_path;monkeypatch;capsys)
    test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping(tmp_path;monkeypatch)
    test_run_cycle_drives_llm_ready_waiting_ticket_without_stagnation_skip(tmp_path;monkeypatch)
    test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure(tmp_path;monkeypatch)
    test_run_cycle_plugin_required_failure_skips_os_injector_fallback(tmp_path;monkeypatch)
    test_run_cycle_autopilot_focus_error_retry_loop_retries_and_warns(tmp_path;monkeypatch;capsys)
    test_run_cycle_does_not_retry_missing_plugin_as_focus_error(tmp_path;monkeypatch;capsys)
    test_run_cycle_skips_drive_when_required_plugin_missing(tmp_path;monkeypatch;capsys)
    test_run_cycle_visible_typing_does_not_require_plugin(tmp_path;monkeypatch)
    test_run_cycle_jetbrains_does_not_require_plugin_by_default(tmp_path;monkeypatch)
    _fast_autonomous_up(monkeypatch)
    test_up_keeps_running_on_waiting_input_by_default(tmp_path;monkeypatch)
    test_up_stops_on_waiting_input_when_flag_set(tmp_path;monkeypatch)
    test_up_restarts_autopilot_when_socket_disappears_between_cycles(tmp_path;monkeypatch)
    test_compute_backoff_sleep_caps_stagnation()
    test_env_apply_autoloop_defaults_enables_full_diagnostics(monkeypatch)
    test_run_idle_diagnostics_profile_off_message(tmp_path;capsys)
    test_run_idle_diagnostics_creates_deduped_ticket(tmp_path;monkeypatch)
    test_wup_watch_command_uses_testql_mode(tmp_path)
    test_wup_watch_command_prefers_project_venv_wrapper(tmp_path)
    test_wup_watch_command_keeps_explicit_testql_bin(tmp_path)
    test_wup_watch_command_normalizes_percent_cpu_throttle(tmp_path)
    test_wup_subprocess_env_loads_project_wup_env(tmp_path;monkeypatch)
    test_start_wup_watch_passes_playwright_env(tmp_path;monkeypatch)
    test_wup_profiled_compose_services_start_before_watch(tmp_path;monkeypatch)
    test_wup_compose_ps_accepts_json_lines()
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
    e: test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker,test_resolve_autopilot_ide_for_autonomous_returns_string_lane,test_resolve_agent_lane_respects_terminal_jetbrains_hint,test_resolve_autopilot_ide_keeps_jetbrains_lane_when_plugin_ide_running,test_resolve_autopilot_ide_keeps_jetbrains_when_no_plugin_ide_running,test_format_post_startup_operator_hints_mentions_socket,test_format_post_startup_operator_hints_for_jetbrains_skips_plugin_steps,test_format_startup_banner_includes_version,test_build_startup_probe_reports_per_ide_socket_for_explicit_ide,test_apply_agent_lane_environ_uses_running_ide
    test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker(tmp_path)
    test_resolve_autopilot_ide_for_autonomous_returns_string_lane()
    test_resolve_agent_lane_respects_terminal_jetbrains_hint(tmp_path)
    test_resolve_autopilot_ide_keeps_jetbrains_lane_when_plugin_ide_running()
    test_resolve_autopilot_ide_keeps_jetbrains_when_no_plugin_ide_running()
    test_format_post_startup_operator_hints_mentions_socket(tmp_path)
    test_format_post_startup_operator_hints_for_jetbrains_skips_plugin_steps()
    test_format_startup_banner_includes_version(tmp_path)
    test_build_startup_probe_reports_per_ide_socket_for_explicit_ide(tmp_path;monkeypatch)
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
    e: test_autopilot_parser_requires_action,test_drive_without_daemon_errors,test_drive_missing_text_errors,test_drive_prompt_flag,test_drive_auto_fallbacks_to_direct_when_daemon_cannot_focus,test_drive_auto_fallback_can_be_disabled_by_env,test_drive_dry_run_direct,test_drive_direct_prefers_os_injector_profile,test_drive_direct_honors_os_profile_override,test_drive_direct_os_profile_requires_os_injector_when_not_available,test_drive_direct_os_profile_os_injector_error_no_fallback,test_drive_direct_falls_back_when_os_injector_fails,test_calibrate_auto_ide_resolves_from_running_processes,test_calibrate_writes_profile_from_mouse,test_session_start_explicit_ides,test_session_start_keeps_profile_when_smoke_fails,test_session_start_warns_on_duplicate_coordinates,test_ide_list_empty,test_ide_list_marks_focused_ide,test_doctor_json_output,test_doctor_fix_text_output,test_doctor_fix_json_output,test_install_plugin_dry_run_auto_detect_from_term_program,test_install_plugin_vsix_resolver_prefers_package_version,test_install_plugin_auto_detect_ambiguous_running_ides_errors,test_install_plugin_exec_success_json_payload,test_install_plugin_vscodium_dry_run_uses_codium_cli,test_install_plugin_zed_reports_vsix_plugin_unsupported,test_install_plugin_pycharm_alias_maps_to_jetbrains,test_install_plugin_jetbrains_dry_run_json,test_install_plugin_jetbrains_success_json_payload,test_install_plugin_auto_detects_pycharm_hosted_as_jetbrains,test_status_when_no_daemon,test_status_accepts_legacy_json_flag,test_shutdown_when_no_daemon,test_handoff_dry_run_prints_brief_and_skips_daemon,test_handoff_requires_running_daemon,test_handoff_drives_brief_through_client,_write_audit_log,test_tail_text_format_renders_entries,test_tail_json_format_returns_array,test_tail_n_limits_output,test_tail_missing_log_errors_cleanly,test_tail_skips_malformed_lines,test_install_unit_print_renders_execstart,test_install_unit_writes_to_xdg_default_path,test_install_unit_refuses_overwrite_without_force,test_resolve_koru_bin_falls_back_to_sys_executable_sibling
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
    test_install_plugin_vsix_resolver_prefers_package_version(monkeypatch;tmp_path)
    test_install_plugin_auto_detect_ambiguous_running_ides_errors(capsys;monkeypatch)
    test_install_plugin_exec_success_json_payload(capsys;monkeypatch;tmp_path)
    test_install_plugin_vscodium_dry_run_uses_codium_cli(capsys;monkeypatch;tmp_path)
    test_install_plugin_zed_reports_vsix_plugin_unsupported(capsys)
    test_install_plugin_pycharm_alias_maps_to_jetbrains(capsys)
    test_install_plugin_jetbrains_dry_run_json(capsys;monkeypatch;tmp_path)
    test_install_plugin_jetbrains_success_json_payload(capsys;monkeypatch;tmp_path)
    test_install_plugin_auto_detects_pycharm_hosted_as_jetbrains(capsys;monkeypatch)
    test_status_when_no_daemon(capsys;tmp_path)
    test_status_accepts_legacy_json_flag(capsys;tmp_path)
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
    e: _patch_no_running_ides,_daemon,_connect_plugin,_assert_no_more_data,running_daemon,test_ping_round_trip,test_is_running_true_when_daemon_alive,test_drive_falls_back_to_injector_when_no_plugin,test_drive_require_plugin_blocks_keyboard_fallback,test_drive_reports_injector_failure,test_drive_uses_os_injector_when_profile_available,test_drive_os_injector_skipped_when_env_disabled,test_drive_os_injector_forced_without_profile_falls_back_to_keyboard,test_drive_os_injector_failure_falls_back_to_keyboard,test_drive_empty_text_returns_error,test_drive_unknown_type_returns_error,test_status_reports_socket_and_plugins,test_accept_rejects_foreign_peer_uid,test_plugin_hello_then_drive_forwards,test_drive_strict_plugin_version_blocks_stale_plugin,test_strict_plugin_hello_rejects_stale_without_evicting_current,test_repeated_stale_plugin_hello_rejections_are_log_throttled,test_rejected_plugin_log_default_interval_is_quiet,test_status_reports_rejected_plugin_versions,test_message_sent_event_completes_pending_drive_without_plugin_ack,test_message_sent_event_does_not_complete_strict_ack_drive,test_newer_plugin_connection_replaces_stale_same_ide_client,test_visible_typing_prefers_keyboard_even_when_plugin_connected,test_plugin_ack_with_shutdown_info_is_relayed,test_plugin_ack_submit_failure_uses_os_fallback,test_plugin_ack_failure_skips_os_fallback_if_require_plugin,test_default_handoff_builds_brief_for_uninitialised_project,test_session_ended_triggers_handoff_chat_send,test_session_ended_no_handoff_when_disabled,test_session_ended_skipped_during_cooldown,test_session_started_event_just_acks,test_shutdown_stops_daemon,_StubInjector,_LineReader,_DaemonHarness
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
    test_drive_os_injector_failure_falls_back_to_keyboard(tmp_path;monkeypatch)
    test_drive_empty_text_returns_error(running_daemon)
    test_drive_unknown_type_returns_error(running_daemon)
    test_status_reports_socket_and_plugins(running_daemon)
    test_accept_rejects_foreign_peer_uid(tmp_path;monkeypatch)
    test_plugin_hello_then_drive_forwards(tmp_path;monkeypatch)
    test_drive_strict_plugin_version_blocks_stale_plugin(tmp_path;monkeypatch)
    test_strict_plugin_hello_rejects_stale_without_evicting_current(tmp_path;monkeypatch)
    test_repeated_stale_plugin_hello_rejections_are_log_throttled(tmp_path;monkeypatch)
    test_rejected_plugin_log_default_interval_is_quiet(tmp_path;monkeypatch)
    test_status_reports_rejected_plugin_versions(tmp_path;monkeypatch)
    test_message_sent_event_completes_pending_drive_without_plugin_ack(tmp_path;monkeypatch)
    test_message_sent_event_does_not_complete_strict_ack_drive(tmp_path;monkeypatch)
    test_newer_plugin_connection_replaces_stale_same_ide_client(tmp_path;monkeypatch)
    test_visible_typing_prefers_keyboard_even_when_plugin_connected(tmp_path;monkeypatch)
    test_plugin_ack_with_shutdown_info_is_relayed(tmp_path;monkeypatch)
    test_plugin_ack_submit_failure_uses_os_fallback(tmp_path;monkeypatch)
    test_plugin_ack_failure_skips_os_fallback_if_require_plugin(tmp_path;monkeypatch)
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
    e: fake_proc,test_detect_running_ides_finds_windsurf_and_jetbrains,test_detect_running_ides_deduplicates_same_ide,test_detect_running_ides_prefers_primary_windsurf_over_devin_helper,test_detect_running_ides_skips_unknown_processes,test_detect_running_ides_separates_vscode_and_vscodium,test_pick_target_prefers_user_choice,test_pick_target_returns_none_when_pref_not_running,test_pick_target_defaults_to_first,test_pick_target_prefers_koru_autopilot_ide_env,test_pick_target_ignores_koru_autopilot_ide_env_when_not_running,test_pick_target_empty_list_returns_none,test_detect_focused_ide_id_from_active_pid,test_detect_focused_ide_id_returns_none_for_unknown_pid,test_focused_ide_returns_matching_instance,test_pick_target_prefers_focused_when_no_explicit_prefer,test_pick_target_explicit_prefer_beats_focus,test_resolve_drive_target_auto_picks_first_ide_with_profile,test_detect_terminal_host_ide_id_cursor_env,test_detect_terminal_host_ide_id_cursor_beats_windsurf_token,test_detect_terminal_host_ide_id_vscode_nls_without_pid,test_detect_terminal_host_ide_id_vscodium_from_vscode_family_env,test_detect_terminal_host_ide_id_zed_term_program,test_normalize_ide_id_aliases,test_pick_target_prefers_terminal_host_over_signature_order,test_resolve_drive_target_terminal_without_profile_skips_other_profiles,test_resolve_drive_target_auto_prefers_focused_when_it_has_profile,test_resolve_drive_target_explicit_zed_without_running_process,test_detect_cached_uses_cache_within_ttl,test_detect_cached_ttl_zero_always_refreshes,test_clear_detect_cache_forces_refresh
    fake_proc(tmp_path;monkeypatch)
    test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc)
    test_detect_running_ides_deduplicates_same_ide(fake_proc)
    test_detect_running_ides_prefers_primary_windsurf_over_devin_helper(tmp_path;monkeypatch)
    test_detect_running_ides_skips_unknown_processes(fake_proc)
    test_detect_running_ides_separates_vscode_and_vscodium(tmp_path;monkeypatch)
    test_pick_target_prefers_user_choice(fake_proc)
    test_pick_target_returns_none_when_pref_not_running(fake_proc)
    test_pick_target_defaults_to_first(fake_proc;monkeypatch)
    test_pick_target_prefers_koru_autopilot_ide_env(fake_proc;monkeypatch)
    test_pick_target_ignores_koru_autopilot_ide_env_when_not_running(fake_proc;monkeypatch)
    test_pick_target_empty_list_returns_none()
    test_detect_focused_ide_id_from_active_pid(fake_proc)
    test_detect_focused_ide_id_returns_none_for_unknown_pid(fake_proc)
    test_focused_ide_returns_matching_instance(fake_proc)
    test_pick_target_prefers_focused_when_no_explicit_prefer(fake_proc;monkeypatch)
    test_pick_target_explicit_prefer_beats_focus(fake_proc)
    test_resolve_drive_target_auto_picks_first_ide_with_profile(fake_proc;monkeypatch)
    test_detect_terminal_host_ide_id_cursor_env(monkeypatch)
    test_detect_terminal_host_ide_id_cursor_beats_windsurf_token(monkeypatch)
    test_detect_terminal_host_ide_id_vscode_nls_without_pid(monkeypatch)
    test_detect_terminal_host_ide_id_vscodium_from_vscode_family_env(monkeypatch)
    test_detect_terminal_host_ide_id_zed_term_program(monkeypatch)
    test_normalize_ide_id_aliases(raw;expected)
    test_pick_target_prefers_terminal_host_over_signature_order(fake_proc;monkeypatch)
    test_resolve_drive_target_terminal_without_profile_skips_other_profiles(fake_proc;monkeypatch)
    test_resolve_drive_target_auto_prefers_focused_when_it_has_profile(fake_proc;monkeypatch)
    test_resolve_drive_target_explicit_zed_without_running_process(monkeypatch)
    test_detect_cached_uses_cache_within_ttl(monkeypatch)
    test_detect_cached_ttl_zero_always_refreshes(monkeypatch)
    test_clear_detect_cache_forces_refresh(monkeypatch)
  tests/test_autopilot_injector.py:
    e: _fake_runner,_which_factory,test_select_backend_x11_prefers_xdotool,test_select_backend_wayland_prefers_wtype_over_ydotool,test_select_backend_wayland_falls_back_to_ydotool,test_select_backend_unknown_session_without_display_prefers_wayland_tools,test_select_backend_no_tools_returns_none,test_type_text_dry_run_does_not_call_runner,test_type_text_xdotool_types_and_submits,test_type_text_xdotool_supports_extra_enter,test_type_text_ydotool_uses_configurable_enter_key,test_type_text_ydotool_submit_newline_mode,test_type_text_ydotool_submit_ctrl_enter_mode,test_type_text_wtype_uses_modifiers_for_jetbrains,test_type_text_no_submit_only_types,test_type_text_propagates_runner_error,test_type_text_empty_raises,test_type_text_no_backend_raises,test_probe_marks_unavailable_when_missing_tool,test_probe_marks_unavailable_on_wrong_session,test_wtype_rejects_multi_modifier_submit_key,test_type_text_wayland_falls_back_when_wtype_fails,test_injector_forced_backend,test_wtype_single_modifier_still_works
    _fake_runner(commands)
    _which_factory(present)
    test_select_backend_x11_prefers_xdotool()
    test_select_backend_wayland_prefers_wtype_over_ydotool()
    test_select_backend_wayland_falls_back_to_ydotool()
    test_select_backend_unknown_session_without_display_prefers_wayland_tools(monkeypatch)
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
    e: test_save_and_load_profile,test_load_profile_accepts_legacy_window_id,test_profile_from_mouse_builds_profile,test_capture_from_xdotool_parses_shell_output,test_inject_with_profile_paste_path_uses_clipboard_then_ctrl_v,test_inject_with_profile_type_fallback_when_no_clip_tools,test_load_profile_missing_raises,test_inject_with_profile_paste_timeout_is_reported,test_try_load_profile_prefers_project_over_cwd,test_iter_config_paths_dedupes_project_and_cwd,test_try_drive_with_profile_skips_saved_profile_on_wayland_unless_forced,test_try_drive_with_profile_forced_works_on_wayland,test_try_drive_with_profile_skips_when_env_disabled,test_try_drive_with_profile_uses_config,test_inject_post_focus_delay_env_controls_sleep,test_inject_post_focus_delay_zero_skips_sleep
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
    test_try_drive_with_profile_skips_saved_profile_on_wayland_unless_forced(tmp_path;monkeypatch)
    test_try_drive_with_profile_forced_works_on_wayland(tmp_path;monkeypatch)
    test_try_drive_with_profile_skips_when_env_disabled(monkeypatch)
    test_try_drive_with_profile_uses_config(tmp_path;monkeypatch)
    test_inject_post_focus_delay_env_controls_sleep(monkeypatch)
    test_inject_post_focus_delay_zero_skips_sleep(monkeypatch)
  tests/test_autopilot_plugin_installer.py:
    e: test_resolve_target_ide_prefers_autopilot_env,test_resolve_target_ide_uses_running_supported_ide,test_resolve_target_ide_uses_integrated_terminal_hint,test_install_plugin_dry_run_builds_editor_command,test_resolve_extension_vsix_finds_repo_plugin_package,test_resolve_extension_vsix_prefers_package_version,test_install_plugin_configures_socket_path,test_install_plugin_targets_vscodium_from_integrated_terminal,test_install_plugin_explicit_vscode_does_not_use_codium_hint,test_install_plugin_prefers_running_vscode_over_stale_codium_terminal_hint,test_install_plugin_skips_when_extension_already_installed,test_installed_extension_version_for_ide_reads_editor_cli
    test_resolve_target_ide_prefers_autopilot_env(monkeypatch)
    test_resolve_target_ide_uses_running_supported_ide(monkeypatch)
    test_resolve_target_ide_uses_integrated_terminal_hint(monkeypatch)
    test_install_plugin_dry_run_builds_editor_command(tmp_path;monkeypatch)
    test_resolve_extension_vsix_finds_repo_plugin_package(tmp_path;monkeypatch)
    test_resolve_extension_vsix_prefers_package_version(tmp_path;monkeypatch)
    test_install_plugin_configures_socket_path(tmp_path;monkeypatch)
    test_install_plugin_targets_vscodium_from_integrated_terminal(tmp_path;monkeypatch)
    test_install_plugin_explicit_vscode_does_not_use_codium_hint(tmp_path;monkeypatch)
    test_install_plugin_prefers_running_vscode_over_stale_codium_terminal_hint(tmp_path;monkeypatch)
    test_install_plugin_skips_when_extension_already_installed(monkeypatch)
    test_installed_extension_version_for_ide_reads_editor_cli(monkeypatch)
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
    e: test_explicit_socket_env_overrides_all,test_instance_env_changes_basename,test_default_basename_legacy_when_no_instance,test_auto_instance_uses_default_basename
    test_explicit_socket_env_overrides_all(monkeypatch;tmp_path)
    test_instance_env_changes_basename(monkeypatch)
    test_default_basename_legacy_when_no_instance(monkeypatch)
    test_auto_instance_uses_default_basename(monkeypatch)
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
    TestAutoMain: test_auto_main_stops_prior_and_injects_replace_existing(0),test_auto_main_allow_duplicate_skips_stop_and_replace_flag(0),test_subcommand_auto_routes_to_auto_main(0),test_auto_main_help_does_not_stop_existing_loop(0)  # ``koru auto`` stops prior loops and forwards ``--replace-exi
    TestSubcommandDispatch: test_table_contains_all_documented_subcommands(0),test_table_values_are_callables(0),test_each_subcommand_routes_to_its_handler(0),test_unknown_first_arg_falls_through_to_argparse(0),test_empty_argv_does_not_call_any_handler(0)  # R6: routing through ``_SUBCOMMANDS`` dispatch table.
    _tmp_git_project(prefix)
    _run_main()
  tests/test_context.py:
    e: _ok,_fail,_no_git,_init_planfile,TestBuildContext,TestMarkdownHandoff,TestProjectPipelineInHandoff,TestSetupRequired
    TestBuildContext: test_brief_with_runnable_ticket(0),test_autonomy_loop_brief_reads_telemetry_file(0),test_brief_when_queue_idle(0),test_no_active_ticket_brief_compacts_traceback_error(0),test_brief_when_queue_idle_ticket_next_json_null(0),test_brief_when_planfile_errors(0),test_specific_ticket_uses_show(0),test_instructions_include_no_commit_rule(0),test_instructions_include_ci_command_when_set(0),test_self_service_includes_concrete_ticket_commands(0),test_brief_is_json_serialisable(0),test_files_in_scope_appear_in_instructions(0),test_fixture_tickets_are_skipped_by_default(0),test_real_ticket_picked_over_fixture_in_mixed_queue(0),test_include_fixtures_flag_brings_them_back(0),test_single_object_fixture_is_filtered(0),test_explicit_ticket_id_bypasses_fixture_filter(0),test_all_tickets_are_populated_from_list(0)
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
  tests/test_dev_sync.py:
    e: test_sync_developer_packages_installs_existing_repos,test_sync_developer_packages_skips_dirty_pull
    test_sync_developer_packages_installs_existing_repos(tmp_path)
    test_sync_developer_packages_skips_dirty_pull(tmp_path)
  tests/test_docker_e2e.py:
    e: TestDockerE2E,TestDockerComposeIntegration
    TestDockerE2E: docker_image(0),test_project(1),test_docker_image_builds_successfully(1),test_koru_help_in_docker(1),test_koru_doctor_in_docker(1),test_koru_init_in_docker(1),test_task_creation_with_priority_in_docker(2),test_autonomous_mode_single_cycle_in_docker(2),test_priority_ordering_in_docker(2),test_external_tool_detection_in_docker(1),test_agent_detection_in_docker(1),test_full_workflow_in_docker(2)  # Test Koru functionality in Docker containers.
    TestDockerComposeIntegration: test_docker_compose_build(0),test_docker_compose_test_profile(0),test_docker_compose_deps_profile(0)  # Test Docker Compose integration.
  tests/test_docker_ide_matrix.py:
    e: test_headless_bridge_route_honors_each_matrix_ide,test_autopilot_plugin_requirement_matrix,test_every_matrix_ide_has_submit_key_default,test_every_matrix_ide_has_isolated_default_socket,test_container_matrix_env_matches_supported_ide
    test_headless_bridge_route_honors_each_matrix_ide(ide)
    test_autopilot_plugin_requirement_matrix(monkeypatch;ide)
    test_every_matrix_ide_has_submit_key_default(ide)
    test_every_matrix_ide_has_isolated_default_socket(monkeypatch;ide)
    test_container_matrix_env_matches_supported_ide()
  tests/test_docker_ide_matrix_config.py:
    e: test_docker_ide_matrix_script_covers_supported_systems_and_ides,test_docker_ide_matrix_dockerfile_installs_fake_cli_surface,test_docker_ide_matrix_workflow_exposes_full_matrix,test_docker_ide_matrix_entrypoint_manages_plugin_ides,test_native_ide_matrix_workflow_exposes_windows_and_macos,test_readme_documents_current_ide_matrix_state,test_ide_router_docs_document_current_matrix_state
    test_docker_ide_matrix_script_covers_supported_systems_and_ides()
    test_docker_ide_matrix_dockerfile_installs_fake_cli_surface()
    test_docker_ide_matrix_workflow_exposes_full_matrix()
    test_docker_ide_matrix_entrypoint_manages_plugin_ides()
    test_native_ide_matrix_workflow_exposes_windows_and_macos()
    test_readme_documents_current_ide_matrix_state()
    test_ide_router_docs_document_current_matrix_state()
  tests/test_docs_ide_control_surfaces.py:
    e: test_ide_control_surfaces_doc_exists_with_key_sections,test_ide_router_doc_links_to_ide_control_surfaces,test_ide_router_doc_links_mcp_and_autopilot,test_mcp_ide_flow_doc_links_to_ide_control_surfaces,test_autopilot_design_doc_links_to_ide_control_surfaces,test_agent_guide_links_to_ide_control_surfaces,test_readme_links_ide_control_surfaces,test_ide_protocol_doc_exists_with_key_protocol_terms,test_ide_protocol_doc_has_no_stale_payload_placeholder,test_readme_links_formal_ide_protocol,test_docs_index_links_formal_ide_protocol
    test_ide_control_surfaces_doc_exists_with_key_sections()
    test_ide_router_doc_links_to_ide_control_surfaces()
    test_ide_router_doc_links_mcp_and_autopilot()
    test_mcp_ide_flow_doc_links_to_ide_control_surfaces()
    test_autopilot_design_doc_links_to_ide_control_surfaces()
    test_agent_guide_links_to_ide_control_surfaces()
    test_readme_links_ide_control_surfaces()
    test_ide_protocol_doc_exists_with_key_protocol_terms()
    test_ide_protocol_doc_has_no_stale_payload_placeholder()
    test_readme_links_formal_ide_protocol()
    test_docs_index_links_formal_ide_protocol()
  tests/test_doctor.py:
    e: _scaffold,_run,_named,TestHappyPath,TestKoruProjectPipelineProbe,TestPlanfileCliVersionProbe,TestAutonomousEnvironDoctorIntegration,TestPlanfileBinary,TestPlanfileConfigCheck,TestSprintsCheck,TestPolicyYamlCheck,TestGitignoreCheck,TestCiCommandCheck,TestPytestCollectProbe,TestReportShape,TestWupAndInotifyProbes
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
    TestWupAndInotifyProbes: test_inotify_watches_non_linux_skipped(0),test_inotify_watches_linux_low_limit_fails(0),test_inotify_watches_linux_high_limit_passes(0),test_wup_binary_missing_warns(0),test_wup_binary_present_passes(0)
    _scaffold(project)
    _run(project)
    _named(report;name)
  tests/test_dotenv_loader.py:
    e: TestParseDotenv,TestLoadDotenv
    TestParseDotenv: test_simple_pairs(0),test_export_prefix_supported(0),test_double_quoted_with_escapes(0),test_single_quoted_literal(0),test_inline_comments_stripped(0),test_skips_blank_and_comment_lines(0),test_invalid_lines_silently_skipped(0),test_openrouter_realworld_line(0)
    TestLoadDotenv: setUp(0),tearDown(0),test_no_dotenv_returns_empty(0),test_loads_keys_into_environ(0),test_does_not_override_existing_env(0),test_override_flag_replaces_existing(0),test_env_local_overrides_env(0),test_openrouter_key_propagated(0)
  tests/test_drive_orchestrator.py:
    e: test_plugin_required_message_mentions_ide_and_connect_command,test_should_try_os_fallback_false_when_plugin_required,test_should_try_os_fallback_true_for_submit_failure,test_build_message_sent_info_keeps_chat_and_backend,test_annotate_plugin_ack_marks_strict_when_winning_commands_exist,test_annotate_plugin_ack_marks_plugin_ack_without_winning_commands,test_plugin_version_info_marks_mismatch,test_plugin_version_policy_can_block,test_bundled_expected_plugin_version_matches_vscode_package_json,test_strict_plugin_version_blocks_when_expected_version_missing
    test_plugin_required_message_mentions_ide_and_connect_command()
    test_should_try_os_fallback_false_when_plugin_required()
    test_should_try_os_fallback_true_for_submit_failure()
    test_build_message_sent_info_keeps_chat_and_backend()
    test_annotate_plugin_ack_marks_strict_when_winning_commands_exist()
    test_annotate_plugin_ack_marks_plugin_ack_without_winning_commands()
    test_plugin_version_info_marks_mismatch(monkeypatch)
    test_plugin_version_policy_can_block(monkeypatch)
    test_bundled_expected_plugin_version_matches_vscode_package_json()
    test_strict_plugin_version_blocks_when_expected_version_missing(monkeypatch)
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
    e: test_is_headless_false_minimal_env,test_is_headless_koru_headless_yes,test_is_headless_koru_headless_on,test_is_headless_koru_headless_false_explicit,test_is_headless_ide_mode_whitespace_case_insensitive,test_is_headless_ssh_empty_display_still_headless,test_resolve_ide_route_env_ide_case_insensitive,test_resolve_ide_route_normalizes_vscode_family_alias,test_resolve_ide_route_normalizes_zed_alias,test_resolve_ide_route_headless_sets_primary_surface,test_resolve_ide_route_ide_shell_surface,test_ide_router_main_help_exits_zero,test_ide_router_main_unknown_flag_exits_nonzero,test_ide_router_main_bad_format_exits_nonzero,test_is_headless_ssh_without_display,test_is_headless_ssh_with_display_not_headless,test_is_headless_windows_ignores_ssh_without_display,test_resolve_ide_route_bad_env_uses_cli,test_resolve_ide_route_whitespace_env_treated_as_missing,test_resolve_ide_route_cli_invalid_env_empty_uses_auto,test_resolve_ide_route_cli_auto_env_empty,test_resolve_ide_route_headless_notes_mention_escape_hatch,test_resolve_ide_route_ide_shell_notes_mention_mcp,test_ide_router_main_json,test_ide_router_main_text,test_resolve_ide_route_env_overrides_cli,test_resolve_ide_route_auto_env_does_not_override_cli,test_resolve_ide_route_headless_forces_auto,test_resolve_ide_route_headless_allow_autopilot_honors_env,test_is_headless_via_ide_mode,test_resolve_ide_route_cli_ide_whitespace_normalized,test_resolve_ide_route_headless_allow_autopilot_yes_string,test_resolve_ide_route_environ_none_uses_os_environ,test_resolve_ide_route_headless_all_recommend_flags_false,test_ide_router_main_json_when_headless,test_resolve_ide_route_vscode_explicit_env
    test_is_headless_false_minimal_env()
    test_is_headless_koru_headless_yes()
    test_is_headless_koru_headless_on()
    test_is_headless_koru_headless_false_explicit()
    test_is_headless_ide_mode_whitespace_case_insensitive()
    test_is_headless_ssh_empty_display_still_headless()
    test_resolve_ide_route_env_ide_case_insensitive()
    test_resolve_ide_route_normalizes_vscode_family_alias()
    test_resolve_ide_route_normalizes_zed_alias()
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
  tests/test_install_manager.py:
    e: test_collect_report_flags_path_mismatch_and_plugin_version_missing,test_collect_report_uses_explicit_ide_socket_when_env_is_unset,test_collect_report_flags_connected_plugin_version_mismatch,test_collect_report_flags_installed_plugin_version_mismatch,test_collect_report_marks_installed_ok_but_not_connected_as_info,test_collect_report_flags_stale_live_extension_host,test_collect_report_warns_for_pyenv_shim,test_collect_report_warns_when_daemon_not_running,test_repair_installation_records_plugin_action,test_collect_report_for_zed_does_not_require_vsix_plugin,test_collect_report_auto_still_checks_plugin_connection
    test_collect_report_flags_path_mismatch_and_plugin_version_missing(monkeypatch;tmp_path)
    test_collect_report_uses_explicit_ide_socket_when_env_is_unset(monkeypatch;tmp_path)
    test_collect_report_flags_connected_plugin_version_mismatch(monkeypatch;tmp_path)
    test_collect_report_flags_installed_plugin_version_mismatch(monkeypatch;tmp_path)
    test_collect_report_marks_installed_ok_but_not_connected_as_info(monkeypatch;tmp_path)
    test_collect_report_flags_stale_live_extension_host(monkeypatch;tmp_path)
    test_collect_report_warns_for_pyenv_shim(monkeypatch;tmp_path)
    test_collect_report_warns_when_daemon_not_running(monkeypatch;tmp_path)
    test_repair_installation_records_plugin_action(monkeypatch;tmp_path)
    test_collect_report_for_zed_does_not_require_vsix_plugin(monkeypatch;tmp_path)
    test_collect_report_auto_still_checks_plugin_connection(monkeypatch;tmp_path)
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
    e: _urlopen_json,_urlopen_bytes,local_service_server,test_health_returns_ok_and_version,test_post_event_roundtrip_and_ndjson_events,test_post_enqueue_alias,test_enqueue_adds_single_queue_item,test_queue_claim_and_complete_with_lease,test_queue_claim_filters_action_types,test_worker_lifecycle_prefers_new_healthy_version,test_worker_registration_keeps_manager_metadata,test_worker_with_bad_health_is_quarantined,test_lifecycle_decision_registers_unknown_worker,test_post_empty_body_is_400,test_unknown_path_404
    _urlopen_json(url)
    _urlopen_bytes(url)
    local_service_server()
    test_health_returns_ok_and_version(local_service_server)
    test_post_event_roundtrip_and_ndjson_events(local_service_server)
    test_post_enqueue_alias(local_service_server)
    test_enqueue_adds_single_queue_item(local_service_server)
    test_queue_claim_and_complete_with_lease(local_service_server)
    test_queue_claim_filters_action_types(local_service_server)
    test_worker_lifecycle_prefers_new_healthy_version(local_service_server)
    test_worker_registration_keeps_manager_metadata(local_service_server)
    test_worker_with_bad_health_is_quarantined(local_service_server)
    test_lifecycle_decision_registers_unknown_worker(local_service_server)
    test_post_empty_body_is_400(local_service_server)
    test_unknown_path_404(local_service_server)
  tests/test_loop.py:
    e: TestKoruLoop
    TestKoruLoop: test_search_root_for_include_uses_literal_prefix(0),test_discover_repositories_with_pattern(0),test_run_closed_loop_retries_failed_repositories(0),test_run_closed_loop_single_round_when_all_succeed(0),test_command_value_rejects_blank_value(0)
  tests/test_mcp_provision.py:
    e: test_detect_ides_uses_runtime_bridge,test_provision_cursor_dry_run_does_not_write,test_provision_cursor_writes_file_and_then_is_idempotent,test_provision_zed_writes_context_servers,test_provision_vscodium_uses_vscode_workspace_mcp_file,test_provision_upgrades_bare_koru_command_to_absolute,test_remove_from_config_removes_koru_entry,test_remove_from_config_removes_zed_context_server,test_init_ide_main_json_output_for_cursor_dry_run,test_init_ide_main_json_output_for_zed_dry_run,test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command,test_ensure_koru_mcp_not_disabled_includes_global_windsurf,test_ensure_koru_mcp_not_disabled_handles_zed_context_servers
    test_detect_ides_uses_runtime_bridge(monkeypatch)
    test_provision_cursor_dry_run_does_not_write(tmp_path)
    test_provision_cursor_writes_file_and_then_is_idempotent(tmp_path)
    test_provision_zed_writes_context_servers(tmp_path)
    test_provision_vscodium_uses_vscode_workspace_mcp_file(tmp_path)
    test_provision_upgrades_bare_koru_command_to_absolute(tmp_path;monkeypatch)
    test_remove_from_config_removes_koru_entry(tmp_path)
    test_remove_from_config_removes_zed_context_server(tmp_path)
    test_init_ide_main_json_output_for_cursor_dry_run(capsys;tmp_path)
    test_init_ide_main_json_output_for_zed_dry_run(capsys;tmp_path)
    test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command(tmp_path;monkeypatch)
    test_ensure_koru_mcp_not_disabled_includes_global_windsurf(tmp_path;monkeypatch)
    test_ensure_koru_mcp_not_disabled_handles_zed_context_servers(tmp_path;monkeypatch)
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
    e: probe,test_build_operator_steps_mcp_pending_without_config,test_build_operator_steps_mcp_ok_when_configured,test_build_operator_steps_skips_plugin_for_jetbrains,test_build_operator_steps_plugin_probe_uses_resolved_ide,test_run_startup_operator_pipeline_creates_tickets,test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing,test_candidate_planfile_health_urls_use_serve_endpoint,test_run_startup_operator_pipeline_dedup_markers,test_run_startup_operator_pipeline_recovers_missing_marker_from_open_ticket,test_run_startup_operator_pipeline_replaces_stale_ide_marker,test_run_startup_operator_pipeline_closes_resolved_marker_ticket,test_run_startup_operator_pipeline_keeps_marker_when_close_times_out,test_run_startup_operator_pipeline_closes_marker_when_plugin_step_skipped
    probe(tmp_path)
    test_build_operator_steps_mcp_pending_without_config(tmp_path;probe)
    test_build_operator_steps_mcp_ok_when_configured(tmp_path;probe)
    test_build_operator_steps_skips_plugin_for_jetbrains(tmp_path;probe)
    test_build_operator_steps_plugin_probe_uses_resolved_ide(tmp_path;probe)
    test_run_startup_operator_pipeline_creates_tickets(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing(tmp_path;probe;monkeypatch)
    test_candidate_planfile_health_urls_use_serve_endpoint(tmp_path)
    test_run_startup_operator_pipeline_dedup_markers(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_recovers_missing_marker_from_open_ticket(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_replaces_stale_ide_marker(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_closes_resolved_marker_ticket(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_keeps_marker_when_close_times_out(tmp_path;probe;monkeypatch)
    test_run_startup_operator_pipeline_closes_marker_when_plugin_step_skipped(tmp_path;probe;monkeypatch)
  tests/test_planfile_queue.py:
    e: _ok,_ticket_args,TestPlanfileCommand,TestPlanfileQueue,TestPlanfileQueueLlm,TestPlanfileQueueLoop,TestAppendShellEvidenceNote
    TestPlanfileCommand: test_falls_back_to_path_cli_when_module_cli_missing(0),test_module_cli_probe_treats_missing_parent_as_missing(0)
    TestPlanfileQueue: test_shell_ticket_runs_lifecycle_commands(0),test_ticket_claim_failure_returns_claim_failed(0),test_human_ticket_returns_waiting_input(0),test_shell_failure_marks_ticket_failed(0),test_api_ticket_runs_lifecycle_commands(0),test_api_failure_marks_ticket_failed(0),test_idle_when_planfile_returns_no_ticket(0),test_planfile_error_propagates(0),test_dry_run_returns_command_without_executing(0),test_unsupported_executor_kind(0),test_shell_ticket_without_command_auto_completes(0),test_scan_ticket_without_executor_waits_for_ide_prompt(0),test_api_ticket_without_endpoint_requests_input(0),test_interactive_human_ticket_completes_with_answer(0),test_interactive_human_ticket_cancellation_leaves_ticket(0),test_interactive_with_dry_run_does_not_prompt(0)
    TestPlanfileQueueLlm: _llm_ticket(0),test_llm_ticket_runs_lifecycle_commands(0),test_llm_ticket_failure_marks_failed(0),test_llm_ticket_without_prompt_requests_input(0),test_llm_dry_run_returns_request_without_calling(0),test_llm_default_runner_without_api_key_returns_clear_error(0)  # Tests for the executor.kind=llm path.
    TestPlanfileQueueLoop: _make_runner(1),test_loop_drains_three_shell_tickets_to_idle(0),test_loop_breaks_on_waiting_input_without_interactive(0),test_loop_continues_past_failed_ticket(0),test_loop_respects_max_iterations_cap(0),test_loop_stop_callback_drains_after_current_iteration(0),test_loop_with_interactive_drains_human_tickets(0),test_loop_validates_max_iterations(0)  # Tests for run_planfile_queue_loop — the queue-draining drive
    TestAppendShellEvidenceNote: test_short_flag_when_long_option_unsupported(0),test_artifact_when_both_note_flags_missing(0)  # Regression: planfile CLIs without ``--note`` still persist s
    _ok(stdout)
    _ticket_args(command)
  tests/test_plugin_router.py:
    e: test_plugin_for_prefers_newest_matching_client,test_drop_stale_plugins_removes_older_same_ide,test_status_rows_include_only_plugin_clients,_Sock,_Client
    _Sock: fileno(0)
    _Client: __post_init__(0)
    test_plugin_for_prefers_newest_matching_client()
    test_drop_stale_plugins_removes_older_same_ide()
    test_status_rows_include_only_plugin_clients()
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
  tests/test_pyproject_metadata.py:
    e: _pyproject,_uv_lock_koru_package,test_base_runtime_dependencies_stay_small,test_all_extra_matches_union_of_other_extras,test_readme_documents_each_installation_extra,test_uv_lock_koru_metadata_matches_pyproject
    _pyproject()
    _uv_lock_koru_package()
    test_base_runtime_dependencies_stay_small()
    test_all_extra_matches_union_of_other_extras()
    test_readme_documents_each_installation_extra()
    test_uv_lock_koru_metadata_matches_pyproject()
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
    e: test_queue_status_marker_known_status,test_queue_loop_exit_code_success,test_single_task_ticket_lists,test_emit_queue_run_started_does_not_raise,test_run_queue_loop_mode_stops_after_local_manager_drain,FakeLocalManagerClient
    FakeLocalManagerClient: __init__(0),register_worker(0),claim_action(0),heartbeat_worker(0),complete_action(0)
    test_queue_status_marker_known_status()
    test_queue_loop_exit_code_success()
    test_single_task_ticket_lists()
    test_emit_queue_run_started_does_not_raise()
    test_run_queue_loop_mode_stops_after_local_manager_drain(monkeypatch)
  tests/test_redup_integration.py:
    e: test_changed_scan_command_uses_current_python_module,test_scan_and_check_commands_use_current_python_module,test_changed_scan_runner_uses_current_python,test_run_changed_scan_skips_full_fallback_by_default,test_run_changed_scan_full_fallback_is_opt_in
    test_changed_scan_command_uses_current_python_module()
    test_scan_and_check_commands_use_current_python_module(tmp_path)
    test_changed_scan_runner_uses_current_python()
    test_run_changed_scan_skips_full_fallback_by_default(monkeypatch;tmp_path)
    test_run_changed_scan_full_fallback_is_opt_in(monkeypatch;tmp_path)
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
  tests/test_runtime_insights.py:
    e: test_collect_runtime_insights_summarizes_processes,test_collect_runtime_insights_includes_detected_ides
    test_collect_runtime_insights_summarizes_processes(monkeypatch)
    test_collect_runtime_insights_includes_detected_ides(monkeypatch)
  tests/test_scan.py:
    e: _ok,_marker_fixture,TestScanCLI,TestScanPytestCollect,TestScanTodoMarkers,TestScanMissingGates,TestScanMissingTools,TestScanGitignoreDrift,TestRunScan,TestScanSemcodArtifacts
    TestScanCLI: test_json_output_uses_scan_result_dict_and_semcod_flag(0)
    TestScanPytestCollect: test_returns_empty_when_no_tests_and_no_pyproject(0),test_empty_on_clean_collect(0),test_parses_per_file_collection_errors(0),test_falls_back_to_umbrella_import_ticket(0),test_collection_timeout_emits_diagnostic_ticket(0),test_timeout_value_is_reflected_in_ticket(0),test_pytest_not_installed_stays_silent(0)
    TestScanTodoMarkers: test_filters_files_below_threshold(0),test_groups_markers_per_file(0),test_respects_koruignore_file_glob(0),test_respects_koruignore_directory_prefix(0),test_ignores_common_virtualenv_dirs_by_default(0)
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

### `project/logic.pl`

```prolog markpact:analysis path=project/logic.pl
% ── Project Metadata ─────────────────────────────────────
project_metadata('koru', '0.1.177', 'python').

% ── Project Files ────────────────────────────────────────
project_file('app.doql.less', 681, 'less').
project_file('docs/llm-tools/aider/install.sh', 56, 'shell').
project_file('docs/llm-tools/claude-code/install.sh', 61, 'shell').
project_file('docs/llm-tools/costs/install.sh', 50, 'shell').
project_file('docs/llm-tools/cursor/install.sh', 89, 'shell').
project_file('docs/llm-tools/doql/install.sh', 53, 'shell').
project_file('docs/llm-tools/goal/install.sh', 54, 'shell').
project_file('docs/llm-tools/llx/install.sh', 54, 'shell').
project_file('docs/llm-tools/mdflow/install.sh', 39, 'shell').
project_file('docs/llm-tools/metrun/install.sh', 39, 'shell').
project_file('docs/llm-tools/op3/install.sh', 54, 'shell').
project_file('docs/llm-tools/pfix/install.sh', 53, 'shell').
project_file('docs/llm-tools/planfile/install.sh', 42, 'shell').
project_file('docs/llm-tools/prefact/install.sh', 50, 'shell').
project_file('docs/llm-tools/protogate/install.sh', 39, 'shell').
project_file('docs/llm-tools/rebuild/install.sh', 39, 'shell').
project_file('docs/llm-tools/redeploy/install.sh', 88, 'shell').
project_file('docs/llm-tools/redsl/install.sh', 54, 'shell').
project_file('docs/llm-tools/redup/install.sh', 42, 'shell').
project_file('docs/llm-tools/regix/install.sh', 53, 'shell').
project_file('docs/llm-tools/sumd/install.sh', 81, 'shell').
project_file('docs/llm-tools/testql/install.sh', 50, 'shell').
project_file('docs/llm-tools/toonic/install.sh', 50, 'shell').
project_file('docs/llm-tools/vallm/install.sh', 56, 'shell').
project_file('examples/ci/headless-autonomous-jsonl/e2e.sh', 27, 'shell').
project_file('examples/ci/headless-autonomous-jsonl/run-docker.sh', 8, 'shell').
project_file('examples/planfile/http-api-curl/e2e.sh', 20, 'shell').
project_file('examples/planfile/http-api-curl/run-docker.sh', 8, 'shell').
project_file('examples/planfile/queue-cli-dryrun/e2e.sh', 16, 'shell').
project_file('examples/planfile/queue-cli-dryrun/run-docker.sh', 8, 'shell').
project_file('examples/protocol/autopilot-socket-smoke/e2e.sh', 27, 'shell').
project_file('examples/protocol/autopilot-socket-smoke/run-docker.sh', 8, 'shell').
project_file('examples/run-e2e.sh', 44, 'shell').
project_file('examples/runtime/koru-serve-health/e2e.sh', 22, 'shell').
project_file('examples/runtime/koru-serve-health/run-docker.sh', 8, 'shell').
project_file('plugins/koru-autopilot-vscode/out/dispatch-plan.js', 19, 'javascript').
project_file('plugins/koru-autopilot-vscode/out/dispatch-plan.test.js', 117, 'javascript').
project_file('plugins/koru-autopilot-vscode/out/extension.js', 702, 'javascript').
project_file('plugins/koru-autopilot-vscode/out/probe-ladder.js', 220, 'javascript').
project_file('plugins/koru-autopilot-vscode/out/probe-ladder.test.js', 48, 'javascript').
project_file('plugins/koru-autopilot-vscode/out/socketPath.js', 100, 'javascript').
project_file('plugins/koru-autopilot-vscode/src/dispatch-plan.test.ts', 123, 'typescript').
project_file('plugins/koru-autopilot-vscode/src/dispatch-plan.ts', 27, 'typescript').
project_file('plugins/koru-autopilot-vscode/src/extension.ts', 754, 'typescript').
project_file('plugins/koru-autopilot-vscode/src/probe-ladder.test.ts', 79, 'typescript').
project_file('plugins/koru-autopilot-vscode/src/probe-ladder.ts', 261, 'typescript').
project_file('plugins/koru-autopilot-vscode/src/socketPath.ts', 67, 'typescript').
project_file('project.sh', 54, 'shell').
project_file('scripts/_koru_autodiag_filter_tickets.py', 56, 'python').
project_file('scripts/autopilot-ide-autodetect-smoke.sh', 183, 'shell').
project_file('scripts/docker-ide-matrix-entrypoint.sh', 32, 'shell').
project_file('scripts/docker-ide-matrix.sh', 93, 'shell').
project_file('scripts/koru-autoloop-reset-diag-markers.sh', 97, 'shell').
project_file('scripts/koru-autoloop.sh', 677, 'shell').
project_file('scripts/koru-gate-capture.py', 315, 'python').
project_file('scripts/koru-queue-diagnose.sh', 125, 'shell').
project_file('scripts/koru-semcod-gates.sh', 100, 'shell').
project_file('scripts/koru-soak-monitor.sh', 129, 'shell').
project_file('scripts/koru-soak-start.sh', 40, 'shell').
project_file('scripts/koru-soak-status.sh', 100, 'shell').
project_file('scripts/koru-soak-stop.sh', 124, 'shell').
project_file('scripts/planfile-export-prompt.sh', 82, 'shell').
project_file('scripts/planfile-sync-todo.py', 261, 'python').
project_file('services/healing-webhook/app.py', 703, 'python').
project_file('services/healing-webhook/ticket_builder.py', 224, 'python').
project_file('src/koru/__init__.py', 70, 'python').
project_file('src/koru/__main__.py', 9, 'python').
project_file('src/koru/activity_log.py', 68, 'python').
project_file('src/koru/agent_backend_runtime.py', 181, 'python').
project_file('src/koru/agent_backends.py', 215, 'python').
project_file('src/koru/agent_cli_helpers.py', 88, 'python').
project_file('src/koru/agents.py', 323, 'python').
project_file('src/koru/api/__init__.py', 10, 'python').
project_file('src/koru/autoloop_cli.py', 91, 'python').
project_file('src/koru/autonomous.py', 2236, 'python').
project_file('src/koru/autonomous_cycle.py', 1390, 'python').
project_file('src/koru/autonomous_diagnostics.py', 259, 'python').
project_file('src/koru/autonomous_env.py', 26, 'python').
project_file('src/koru/autonomous_parser.py', 399, 'python').
project_file('src/koru/autonomous_process_guard.py', 207, 'python').
project_file('src/koru/autonomous_startup.py', 313, 'python').
project_file('src/koru/autonomous_wup.py', 539, 'python').
project_file('src/koru/autonomy/__init__.py', 25, 'python').
project_file('src/koru/autonomy/config.py', 124, 'python').
project_file('src/koru/autonomy/env.py', 305, 'python').
project_file('src/koru/autonomy/environment.py', 246, 'python').
project_file('src/koru/autonomy/heal.py', 117, 'python').
project_file('src/koru/autonomy/ide_work.py', 302, 'python').
project_file('src/koru/autonomy/operator_pipeline.py', 840, 'python').
project_file('src/koru/autonomy/post_run_verify.py', 382, 'python').
project_file('src/koru/autonomy/prompts.py', 102, 'python').
project_file('src/koru/autonomy/telemetry_snapshot.py', 80, 'python').
project_file('src/koru/autopilot/__init__.py', 19, 'python').
project_file('src/koru/autopilot/audit.py', 10, 'python').
project_file('src/koru/autopilot/calibrate_cli.py', 211, 'python').
project_file('src/koru/autopilot/cli_command.py', 849, 'python').
project_file('src/koru/autopilot/client.py', 11, 'python').
project_file('src/koru/autopilot/config.py', 10, 'python').
project_file('src/koru/autopilot/daemon.py', 17, 'python').
project_file('src/koru/autopilot/daemon_cli.py', 110, 'python').
project_file('src/koru/autopilot/doctor_cli.py', 153, 'python').
project_file('src/koru/autopilot/host_setup.py', 10, 'python').
project_file('src/koru/autopilot/ide.py', 10, 'python').
project_file('src/koru/autopilot/injector.py', 10, 'python').
project_file('src/koru/autopilot/install_manager.py', 585, 'python').
project_file('src/koru/autopilot/install_plugin_cli.py', 427, 'python').
project_file('src/koru/autopilot/local_manager.py', 67, 'python').
project_file('src/koru/autopilot/os_injector.py', 10, 'python').
project_file('src/koru/autopilot/plugin_installer.py', 10, 'python').
project_file('src/koru/autopilot/protocol.py', 49, 'python').
project_file('src/koru/autopilot/systemd_cli.py', 104, 'python').
project_file('src/koru/autopilot/tail_cli.py', 74, 'python').
project_file('src/koru/autopilot/utils/__init__.py', 6, 'python').
project_file('src/koru/autopilot/utils/client_helpers.py', 58, 'python').
project_file('src/koru/bootstrap.py', 453, 'python').
project_file('src/koru/cli/__init__.py', 56, 'python').
project_file('src/koru/cli/__main__.py', 8, 'python').
project_file('src/koru/cli/commands.py', 1, 'python').
project_file('src/koru/cli/parsers.py', 1, 'python').
project_file('src/koru/cli.py', 1744, 'python').
project_file('src/koru/cli_doctor.py', 87, 'python').
project_file('src/koru/cli_gate.py', 117, 'python').
project_file('src/koru/cli_gc.py', 88, 'python').
project_file('src/koru/cli_init.py', 103, 'python').
project_file('src/koru/cli_queue.py', 164, 'python').
project_file('src/koru/cli_scan.py', 130, 'python').
project_file('src/koru/cli_topology.py', 123, 'python').
project_file('src/koru/cli_watch.py', 42, 'python').
project_file('src/koru/context.py', 1254, 'python').
project_file('src/koru/context_render.py', 472, 'python').
project_file('src/koru/dev_sync.py', 134, 'python').
project_file('src/koru/doctor.py', 546, 'python').
project_file('src/koru/dotenv_loader.py', 105, 'python').
project_file('src/koru/dsl/__init__.py', 10, 'python').
project_file('src/koru/events.py', 91, 'python').
project_file('src/koru/gate.py', 203, 'python').
project_file('src/koru/gc.py', 372, 'python').
project_file('src/koru/gc_cli_helpers.py', 82, 'python').
project_file('src/koru/ide_client.py', 153, 'python').
project_file('src/koru/ide_router.py', 99, 'python').
project_file('src/koru/ide_runtime.py', 45, 'python').
project_file('src/koru/init.py', 611, 'python').
project_file('src/koru/init_host_environment.py', 315, 'python').
project_file('src/koru/local_manager_client.py', 252, 'python').
project_file('src/koru/local_manager_state.py', 292, 'python').
project_file('src/koru/local_service.py', 313, 'python').
project_file('src/koru/loop.py', 132, 'python').
project_file('src/koru/mcp_provision.py', 450, 'python').
project_file('src/koru/mcp_server.py', 10, 'python').
project_file('src/koru/planfile_queue.py', 37, 'python').
project_file('src/koru/policy.py', 263, 'python').
project_file('src/koru/project_pipeline.py', 151, 'python').
project_file('src/koru/queue/__init__.py', 39, 'python').
project_file('src/koru/queue/human.py', 32, 'python').
project_file('src/koru/queue/koru_queue_argv.py', 45, 'python').
project_file('src/koru/queue/local_manager.py', 136, 'python').
project_file('src/koru/queue/locking.py', 87, 'python').
project_file('src/koru/queue/loop.py', 116, 'python').
project_file('src/koru/queue/planfile_ticket_note.py', 56, 'python').
project_file('src/koru/queue/runner.py', 394, 'python').
project_file('src/koru/queue/runners.py', 250, 'python').
project_file('src/koru/queue/shell_evidence.py', 73, 'python').
project_file('src/koru/queue/ticket.py', 148, 'python').
project_file('src/koru/queue/types.py', 89, 'python').
project_file('src/koru/queue_clean.py', 392, 'python').
project_file('src/koru/queue_cli_helpers.py', 291, 'python').
project_file('src/koru/redup_integration.py', 190, 'python').
project_file('src/koru/refactor_planfile_handoff.py', 47, 'python').
project_file('src/koru/run_log.py', 124, 'python').
project_file('src/koru/runtime.py', 105, 'python').
project_file('src/koru/scan.py', 933, 'python').
project_file('src/koru/scripts/koru-autoloop.sh', 677, 'shell').
project_file('src/koru/semcod_tools.py', 149, 'python').
project_file('src/koru/serve.py', 10, 'python').
project_file('src/koru/stdio_events.py', 50, 'python').
project_file('src/koru/tasks.py', 228, 'python').
project_file('src/koru/tools.py', 319, 'python').
project_file('src/koru/topology.py', 415, 'python').
project_file('src/koru/topology_cli.py', 76, 'python').
project_file('src/koru/utils/__init__.py', 6, 'python').
project_file('src/koru/utils/subprocess_runner.py', 41, 'python').
project_file('src/koru/watch.py', 94, 'python').
project_file('src/koru/wup_testql_compat.py', 65, 'python').
project_file('src/koruapi/__init__.py', 26, 'python').
project_file('src/koruapi/cli.py', 129, 'python').
project_file('src/koruapi/dashboard.py', 91, 'python').
project_file('src/koruapi/dashboard_serve.py', 1401, 'python').
project_file('src/koruapi/integrations.py', 199, 'python').
project_file('src/koruapi/invoke.py', 32, 'python').
project_file('src/koruapi/invoke_handlers.py', 200, 'python').
project_file('src/koruapi/local.py', 37, 'python').
project_file('src/koruapi/mcp.py', 16, 'python').
project_file('src/koruapi/mcp_server.py', 1041, 'python').
project_file('src/koruapi/openapi.py', 156, 'python').
project_file('src/koruapi/runtime_insights.py', 190, 'python').
project_file('src/koruapi/server.py', 176, 'python').
project_file('src/koruapi/topology_post.py', 69, 'python').
project_file('src/korudsl/__init__.py', 26, 'python').
project_file('src/korudsl/cli.py', 82, 'python').
project_file('src/korudsl/library.py', 208, 'python').
project_file('src/korudsl/transform.py', 71, 'python').
project_file('src/koruide/__init__.py', 68, 'python').
project_file('src/koruide/audit.py', 155, 'python').
project_file('src/koruide/client.py', 129, 'python').
project_file('src/koruide/config.py', 122, 'python').
project_file('src/koruide/daemon.py', 897, 'python').
project_file('src/koruide/drive_orchestrator.py', 201, 'python').
project_file('src/koruide/host_setup.py', 227, 'python').
project_file('src/koruide/ide.py', 680, 'python').
project_file('src/koruide/injector.py', 407, 'python').
project_file('src/koruide/os_injector.py', 401, 'python').
project_file('src/koruide/plugin_installer.py', 495, 'python').
project_file('src/koruide/plugin_router.py', 75, 'python').
project_file('src/koruide/plugin_version.py', 9, 'python').
project_file('src/koruide/protocol.py', 232, 'python').
project_file('src/koruide/socket.py', 45, 'python').
project_file('src/koruide/utils.py', 22, 'python').
project_file('tests/e2e/bootstrap.sh', 94, 'shell').
project_file('tests/e2e/init.sh', 29, 'shell').
project_file('tests/e2e/smoke.sh', 112, 'shell').
project_file('tests/test_activity_log.py', 25, 'python').
project_file('tests/test_agent_backend_runtime.py', 156, 'python').
project_file('tests/test_agent_backends.py', 88, 'python').
project_file('tests/test_agent_backends_cli.py', 34, 'python').
project_file('tests/test_agent_cli.py', 108, 'python').
project_file('tests/test_agents.py', 208, 'python').
project_file('tests/test_autoloop_cli.py', 52, 'python').
project_file('tests/test_autonomous.py', 2588, 'python').
project_file('tests/test_autonomous_diagnostics.py', 71, 'python').
project_file('tests/test_autonomous_parser_detection.py', 16, 'python').
project_file('tests/test_autonomous_process_detection.py', 37, 'python').
project_file('tests/test_autonomous_scenarios.py', 305, 'python').
project_file('tests/test_autonomous_startup.py', 204, 'python').
project_file('tests/test_autonomy_config.py', 141, 'python').
project_file('tests/test_autonomy_env.py', 83, 'python').
project_file('tests/test_autonomy_environment.py', 219, 'python').
project_file('tests/test_autonomy_prompts.py', 162, 'python').
project_file('tests/test_autopilot_audit.py', 125, 'python').
project_file('tests/test_autopilot_cli.py', 1128, 'python').
project_file('tests/test_autopilot_client_drive_errors.py', 16, 'python').
project_file('tests/test_autopilot_config.py', 148, 'python').
project_file('tests/test_autopilot_daemon.py', 1187, 'python').
project_file('tests/test_autopilot_host_setup.py', 125, 'python').
project_file('tests/test_autopilot_ide.py', 460, 'python').
project_file('tests/test_autopilot_injector.py', 287, 'python').
project_file('tests/test_autopilot_jetbrains_scaffold.py', 45, 'python').
project_file('tests/test_autopilot_os_injector.py', 318, 'python').
project_file('tests/test_autopilot_plugin_installer.py', 326, 'python').
project_file('tests/test_autopilot_protocol.py', 154, 'python').
project_file('tests/test_autopilot_socket_path.py', 36, 'python').
project_file('tests/test_bootstrap.py', 298, 'python').
project_file('tests/test_cli.py', 465, 'python').
project_file('tests/test_context.py', 586, 'python').
project_file('tests/test_dashboard_topology_post.py', 36, 'python').
project_file('tests/test_dev_sync.py', 43, 'python').
project_file('tests/test_docker_e2e.py', 582, 'python').
project_file('tests/test_docker_ide_matrix.py', 63, 'python').
project_file('tests/test_docker_ide_matrix_config.py', 116, 'python').
project_file('tests/test_docs_ide_control_surfaces.py', 85, 'python').
project_file('tests/test_doctor.py', 512, 'python').
project_file('tests/test_dotenv_loader.py', 117, 'python').
project_file('tests/test_drive_orchestrator.py', 115, 'python').
project_file('tests/test_e2e.py', 1138, 'python').
project_file('tests/test_events.py', 67, 'python').
project_file('tests/test_gate.py', 167, 'python').
project_file('tests/test_gc.py', 323, 'python').
project_file('tests/test_gc_cli_helpers.py', 29, 'python').
project_file('tests/test_ide_client.py', 115, 'python').
project_file('tests/test_ide_client_contract.py', 106, 'python').
project_file('tests/test_ide_router.py', 268, 'python').
project_file('tests/test_ide_runtime.py', 39, 'python').
project_file('tests/test_ide_work.py', 140, 'python').
project_file('tests/test_init.py', 337, 'python').
project_file('tests/test_install_manager.py', 382, 'python').
project_file('tests/test_koru_gate_capture.py', 34, 'python').
project_file('tests/test_koru_queue_argv.py', 24, 'python').
project_file('tests/test_koruapi.py', 80, 'python').
project_file('tests/test_koruapi_transports.py', 21, 'python').
project_file('tests/test_korudsl.py', 31, 'python').
project_file('tests/test_koruide_bridges.py', 78, 'python').
project_file('tests/test_koruide_client.py', 83, 'python').
project_file('tests/test_local_service.py', 265, 'python').
project_file('tests/test_loop.py', 95, 'python').
project_file('tests/test_mcp_provision.py', 277, 'python').
project_file('tests/test_mcp_server.py', 245, 'python').
project_file('tests/test_operator_pipeline.py', 446, 'python').
project_file('tests/test_planfile_queue.py', 1222, 'python').
project_file('tests/test_plugin_router.py', 67, 'python').
project_file('tests/test_policy.py', 194, 'python').
project_file('tests/test_post_run_verify.py', 156, 'python').
project_file('tests/test_pyproject_metadata.py', 51, 'python').
project_file('tests/test_queue_clean.py', 341, 'python').
project_file('tests/test_queue_cli_helpers.py', 120, 'python').
project_file('tests/test_redup_integration.py', 97, 'python').
project_file('tests/test_refactor_planfile_handoff.py', 21, 'python').
project_file('tests/test_regix_taskfile.py', 22, 'python').
project_file('tests/test_run_log.py', 144, 'python').
project_file('tests/test_runtime.py', 133, 'python').
project_file('tests/test_runtime_insights.py', 60, 'python').
project_file('tests/test_scan.py', 651, 'python').
project_file('tests/test_semcod_tools.py', 51, 'python').
project_file('tests/test_serve.py', 371, 'python').
project_file('tests/test_shell_evidence.py', 51, 'python').
project_file('tests/test_stdio_autonomous_jsonl.py', 99, 'python').
project_file('tests/test_tasks.py', 77, 'python').
project_file('tests/test_tools.py', 119, 'python').
project_file('tests/test_topology.py', 55, 'python').
project_file('tests/test_topology_cli.py', 28, 'python').
project_file('tests/test_watch.py', 101, 'python').
project_file('tests/test_wup_taskfile.py', 40, 'python').
project_file('tree.sh', 2, 'shell').

% ── Python Functions ─────────────────────────────────────
python_function('scripts/_koru_autodiag_filter_tickets.py', 'main', 0, 12, 11).
python_function('scripts/koru-gate-capture.py', '_normalize_line', 1, 1, 3).
python_function('scripts/koru-gate-capture.py', '_first_nonempty_line', 1, 3, 2).
python_function('scripts/koru-gate-capture.py', '_is_noise_line', 1, 4, 4).
python_function('scripts/koru-gate-capture.py', '_first_meaningful_line', 1, 3, 4).
python_function('scripts/koru-gate-capture.py', '_run_planfile', 2, 1, 1).
python_function('scripts/koru-gate-capture.py', '_parse_args', 1, 1, 3).
python_function('scripts/koru-gate-capture.py', '_run_gate_command', 2, 3, 2).
python_function('scripts/koru-gate-capture.py', '_matched_failure_line', 2, 4, 4).
python_function('scripts/koru-gate-capture.py', '_extract_finding_keys_from_item', 2, 5, 4).
python_function('scripts/koru-gate-capture.py', '_existing_finding_tickets', 1, 9, 6).
python_function('scripts/koru-gate-capture.py', '_append_existing_note', 0, 8, 5).
python_function('scripts/koru-gate-capture.py', '_create_ticket', 0, 3, 3).
python_function('scripts/koru-gate-capture.py', '_handle_existing_finding', 0, 4, 2).
python_function('scripts/koru-gate-capture.py', 'main', 0, 7, 16).
python_function('scripts/planfile-sync-todo.py', '_find_scripts_dir_with_settings', 0, 3, 5).
python_function('scripts/planfile-sync-todo.py', 'run_planfile', 0, 2, 4).
python_function('scripts/planfile-sync-todo.py', 'load_tickets', 0, 6, 5).
python_function('scripts/planfile-sync-todo.py', 'build_auto_section', 1, 1, 2).
python_function('scripts/planfile-sync-todo.py', 'replace_auto_section', 2, 4, 4).
python_function('scripts/planfile-sync-todo.py', 'do_from_planfile', 1, 14, 15).
python_function('scripts/planfile-sync-todo.py', '_extract_todo_items', 2, 2, 5).
python_function('scripts/planfile-sync-todo.py', '_resolve_import_labels', 1, 5, 5).
python_function('scripts/planfile-sync-todo.py', '_create_ticket', 6, 7, 6).
python_function('scripts/planfile-sync-todo.py', 'do_from_todo', 2, 10, 10).
python_function('scripts/planfile-sync-todo.py', '_llm_stub', 3, 1, 0).
python_function('scripts/planfile-sync-todo.py', 'main', 0, 2, 7).
python_function('services/healing-webhook/app.py', '_rate_limit_ok', 0, 3, 3).
python_function('services/healing-webhook/app.py', '_record_action', 4, 1, 5).
python_function('services/healing-webhook/app.py', '_enrich_ticket_with_vallm', 2, 8, 10).
python_function('services/healing-webhook/app.py', '_build_planfile_command', 1, 2, 1).
python_function('services/healing-webhook/app.py', '_extract_ticket_id_from_stdout', 1, 6, 4).
python_function('services/healing-webhook/app.py', '_execute_planfile_create', 2, 8, 7).
python_function('services/healing-webhook/app.py', 'create_planfile_ticket', 1, 5, 10).
python_function('services/healing-webhook/app.py', '_run_docker', 3, 1, 3).
python_function('services/healing-webhook/app.py', 'heal_redsl_gate', 2, 2, 2).
python_function('services/healing-webhook/app.py', 'heal_redsl_improve', 2, 5, 5).
python_function('services/healing-webhook/app.py', 'heal_rebuild_restore', 2, 6, 6).
python_function('services/healing-webhook/app.py', 'heal_annotate', 2, 1, 1).
python_function('services/healing-webhook/app.py', '_run_vallm_check', 2, 10, 8).
python_function('services/healing-webhook/app.py', '_run_vallm_validate', 3, 11, 9).
python_function('services/healing-webhook/app.py', '_resolve_affected_files', 3, 11, 11).
python_function('services/healing-webhook/app.py', 'heal_vallm_validate', 2, 9, 10).
python_function('services/healing-webhook/app.py', '_parse_redup_summary', 1, 9, 4).
python_function('services/healing-webhook/app.py', '_update_redup_metrics', 2, 2, 1).
python_function('services/healing-webhook/app.py', '_run_redup_check', 1, 6, 7).
python_function('services/healing-webhook/app.py', 'heal_redup_check', 2, 3, 4).
python_function('services/healing-webhook/app.py', '_resolve_strategy', 1, 3, 1).
python_function('services/healing-webhook/app.py', 'healthz', 0, 1, 2).
python_function('services/healing-webhook/app.py', 'metrics', 0, 1, 3).
python_function('services/healing-webhook/app.py', 'get_history', 0, 1, 2).
python_function('services/healing-webhook/app.py', 'alertmanager_webhook', 1, 5, 11).
python_function('services/healing-webhook/app.py', 'probe_failure', 1, 7, 13).
python_function('services/healing-webhook/app.py', 'get_tickets', 0, 7, 5).
python_function('services/healing-webhook/ticket_builder.py', '_git_commit', 1, 2, 3).
python_function('services/healing-webhook/ticket_builder.py', '_infer_paths', 2, 7, 1).
python_function('services/healing-webhook/ticket_builder.py', '_format_paths', 1, 2, 1).
python_function('services/healing-webhook/ticket_builder.py', '_default_acceptance', 1, 2, 1).
python_function('services/healing-webhook/ticket_builder.py', '_format_acceptance', 1, 2, 1).
python_function('services/healing-webhook/ticket_builder.py', '_reproduction_for', 2, 5, 3).
python_function('services/healing-webhook/ticket_builder.py', 'build_ticket_payload', 1, 11, 11).
python_function('src/koru/activity_log.py', 'activity_enabled', 0, 1, 3).
python_function('src/koru/activity_log.py', 'preview_text', 1, 2, 3).
python_function('src/koru/activity_log.py', '_out_stream', 1, 2, 0).
python_function('src/koru/activity_log.py', 'activity', 2, 4, 7).
python_function('src/koru/activity_log.py', 'activity_info', 1, 5, 10).
python_function('src/koru/agent_backend_runtime.py', 'build_agent_backend', 0, 9, 11).
python_function('src/koru/agent_backends.py', 'normalize_agent_backend_id', 1, 4, 3).
python_function('src/koru/agent_backends.py', 'list_agent_backend_ids', 0, 2, 1).
python_function('src/koru/agent_backends.py', 'iter_agent_backend_profiles', 0, 1, 0).
python_function('src/koru/agent_backends.py', 'get_agent_backend_profile', 1, 3, 1).
python_function('src/koru/agent_backends.py', '_parse_lane', 1, 8, 5).
python_function('src/koru/agent_backends.py', 'load_agent_integration_config', 1, 11, 9).
python_function('src/koru/agent_backends.py', 'validate_agent_integration_config', 1, 5, 3).
python_function('src/koru/agent_cli_helpers.py', 'try_agent_env_exports', 1, 7, 5).
python_function('src/koru/agent_cli_helpers.py', 'print_agent_list', 2, 10, 5).
python_function('src/koru/agent_cli_helpers.py', 'run_agent_handoff', 2, 3, 8).
python_function('src/koru/agents.py', 'normalize_agent_lane_id', 1, 6, 6).
python_function('src/koru/agents.py', 'autopilot_backend_for_agent_id', 1, 3, 1).
python_function('src/koru/agents.py', '_which', 1, 1, 1).
python_function('src/koru/agents.py', '_marker', 1, 1, 2).
python_function('src/koru/agents.py', '_detect_agent_commands', 0, 2, 1).
python_function('src/koru/agents.py', '_build_cli_agent_option', 5, 7, 4).
python_function('src/koru/agents.py', 'detect_agent_options', 1, 4, 9).
python_function('src/koru/agents.py', 'detect_project_environment', 1, 4, 7).
python_function('src/koru/agents.py', 'detect_agent_environment', 1, 6, 5).
python_function('src/koru/agents.py', 'select_agent', 1, 14, 7).
python_function('src/koru/agents.py', 'save_agent_prompt', 2, 1, 3).
python_function('src/koru/agents.py', 'agent_lane_environment', 1, 1, 3).
python_function('src/koru/agents.py', 'format_agent_lane_exports', 1, 2, 6).
python_function('src/koru/agents.py', 'launch_agent', 3, 4, 3).
python_function('src/koru/autoloop_cli.py', '_packaged_script_path', 0, 1, 3).
python_function('src/koru/autoloop_cli.py', '_build_parser', 0, 1, 2).
python_function('src/koru/autoloop_cli.py', '_env_from_assignments', 1, 3, 4).
python_function('src/koru/autoloop_cli.py', 'autoloop_main', 1, 8, 11).
python_function('src/koru/autonomous.py', '_try_os_injector_fallback', 1, 4, 8).
python_function('src/koru/autonomous.py', '_stdio_info', 1, 1, 1).
python_function('src/koru/autonomous.py', '_daemon_activity_log', 1, 2, 2).
python_function('src/koru/autonomous.py', '_allow_keyboard_autopilot_fallback', 0, 1, 3).
python_function('src/koru/autonomous.py', '_effective_cycle_autopilot_enabled', 1, 7, 6).
python_function('src/koru/autonomous.py', '_scan_while_waiting_input_enabled', 0, 1, 3).
python_function('src/koru/autonomous.py', '_effective_cycle_scan_enabled', 1, 6, 6).
python_function('src/koru/autonomous.py', '_resolve_autopilot_ide', 1, 1, 1).
python_function('src/koru/autonomous.py', '_apply_agent_lane_environ', 2, 3, 3).
python_function('src/koru/autonomous.py', '_command_project', 1, 5, 7).
python_function('src/koru/autonomous.py', '_process_cwd', 1, 2, 3).
python_function('src/koru/autonomous.py', '_ancestor_pids', 1, 7, 8).
python_function('src/koru/autonomous.py', '_looks_like_autonomous_up_command', 1, 1, 1).
python_function('src/koru/autonomous.py', '_find_existing_autonomous_processes', 1, 11, 13).
python_function('src/koru/autonomous.py', 'stop_prior_autonomous_for_auto_start', 1, 3, 7).
python_function('src/koru/autonomous.py', '_find_existing_wup_processes', 1, 11, 12).
python_function('src/koru/autonomous.py', '_as_managed', 1, 1, 1).
python_function('src/koru/autonomous.py', '_terminate_existing_processes', 1, 10, 5).
python_function('src/koru/autonomous.py', '_confirm_replace_existing', 1, 3, 4).
python_function('src/koru/autonomous.py', '_guard_existing_autonomous_processes', 2, 11, 8).
python_function('src/koru/autonomous.py', '_build_parser', 0, 1, 7).
python_function('src/koru/autonomous.py', '_ensure_init', 1, 4, 3).
python_function('src/koru/autonomous.py', '_current_koru_version', 0, 2, 1).
python_function('src/koru/autonomous.py', '_daemon_status_version', 1, 7, 2).
python_function('src/koru/autonomous.py', '_daemon_status_compatible', 1, 4, 2).
python_function('src/koru/autonomous.py', '_stop_reused_daemon', 2, 4, 6).
python_function('src/koru/autonomous.py', '_start_or_reuse_daemon', 0, 5, 11).
python_function('src/koru/autonomous.py', '_status_has_autopilot_plugin', 2, 9, 5).
python_function('src/koru/autonomous.py', '_wait_for_autopilot_plugin', 2, 6, 4).
python_function('src/koru/autonomous.py', '_queue_loop_waiting_ticket_label', 1, 3, 1).
python_function('src/koru/autonomous.py', '_is_topology_enabled', 2, 4, 2).
python_function('src/koru/autonomous.py', '_current_head', 1, 2, 3).
python_function('src/koru/autonomous.py', '_compute_backoff_sleep', 4, 4, 1).
python_function('src/koru/autonomous.py', '_load_loop_checkpoint', 1, 11, 8).
python_function('src/koru/autonomous.py', '_save_loop_checkpoint', 1, 1, 7).
python_function('src/koru/autonomous.py', '_status_in_skip_list', 2, 3, 3).
python_function('src/koru/autonomous.py', '_run_command_check', 3, 2, 3).
python_function('src/koru/autonomous.py', '_create_diagnostic_ticket', 0, 2, 6).
python_function('src/koru/autonomous.py', '_clear_diagnostic_marker', 2, 1, 1).
python_function('src/koru/autonomous.py', '_read_wup_health', 0, 1, 1).
python_function('src/koru/autonomous.py', '_run_idle_diagnostics', 0, 1, 3).
python_function('src/koru/autonomous.py', '_run_cycle', 0, 1, 1).
python_function('src/koru/autonomous.py', '_setup_autonomous_session', 1, 2, 8).
python_function('src/koru/autonomous.py', '_setup_autopilot_daemon', 2, 6, 5).
python_function('src/koru/autonomous.py', '_enable_autonomous_strict_plugin_policy', 1, 9, 4).
python_function('src/koru/autonomous.py', '_configure_loop_state', 2, 2, 6).
python_function('src/koru/autonomous.py', '_run_mcp_provision', 2, 3, 2).
python_function('src/koru/autonomous.py', '_setup_autopilot_plugin', 4, 7, 6).
python_function('src/koru/autonomous.py', '_run_operator_pipeline', 6, 3, 3).
python_function('src/koru/autonomous.py', '_unblock_queue_if_needed', 2, 3, 5).
python_function('src/koru/autonomous.py', '_restart_daemon_if_needed', 7, 10, 6).
python_function('src/koru/autonomous.py', '_handle_cycle_exit_conditions', 4, 7, 2).
python_function('src/koru/autonomous.py', '_cleanup_autonomous_session', 6, 4, 5).
python_function('src/koru/autonomous.py', '_run_autonomous_cycle', 0, 21, 15).
python_function('src/koru/autonomous.py', '_action_up', 1, 17, 26).
python_function('src/koru/autonomous.py', '_argv_has_option', 2, 5, 2).
python_function('src/koru/autonomous.py', '_expand_auto_up_defaults', 1, 3, 3).
python_function('src/koru/autonomous.py', '_collect_argv_options', 1, 3, 2).
python_function('src/koru/autonomous.py', '_user_option', 2, 2, 1).
python_function('src/koru/autonomous.py', '_auto_value', 4, 2, 3).
python_function('src/koru/autonomous.py', '_auto_pipeline_has_pressure', 2, 9, 0).
python_function('src/koru/autonomous.py', '_auto_pipeline_stage', 2, 5, 1).
python_function('src/koru/autonomous.py', '_select_auto_pipeline_profile', 2, 7, 8).
python_function('src/koru/autonomous.py', '_update_auto_pipeline_state', 4, 3, 1).
python_function('src/koru/autonomous.py', 'autonomous_main', 1, 15, 10).
python_function('src/koru/autonomous_cycle.py', '_stdio_info', 1, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_queue_loop_waiting_ticket_label', 1, 3, 1).
python_function('src/koru/autonomous_cycle.py', '_is_topology_enabled', 2, 4, 2).
python_function('src/koru/autonomous_cycle.py', '_current_head', 1, 2, 3).
python_function('src/koru/autonomous_cycle.py', '_status_in_skip_list', 2, 3, 3).
python_function('src/koru/autonomous_cycle.py', '_allow_keyboard_autopilot_fallback', 0, 1, 3).
python_function('src/koru/autonomous_cycle.py', '_prefer_keyboard_autopilot', 0, 3, 3).
python_function('src/koru/autonomous_cycle.py', '_plugin_required_for_ide', 1, 5, 4).
python_function('src/koru/autonomous_cycle.py', '_client_plugin_rows', 1, 5, 5).
python_function('src/koru/autonomous_cycle.py', '_wanted_plugin_ide', 1, 2, 2).
python_function('src/koru/autonomous_cycle.py', '_plugin_row_matches_ide', 2, 3, 4).
python_function('src/koru/autonomous_cycle.py', '_plugin_row_version_block_reason', 2, 5, 8).
python_function('src/koru/autonomous_cycle.py', '_missing_plugin_label', 1, 2, 0).
python_function('src/koru/autonomous_cycle.py', '_client_has_usable_plugin', 2, 7, 6).
python_function('src/koru/autonomous_cycle.py', '_try_os_injector_fallback', 1, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_run_command_check', 3, 2, 3).
python_function('src/koru/autonomous_cycle.py', '_create_diagnostic_ticket', 0, 2, 5).
python_function('src/koru/autonomous_cycle.py', '_clear_diagnostic_marker', 2, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_read_wup_health', 0, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_run_idle_diagnostics', 0, 1, 3).
python_function('src/koru/autonomous_cycle.py', '_autopilot_event_path', 0, 1, 2).
python_function('src/koru/autonomous_cycle.py', '_drain_autopilot_events', 1, 6, 8).
python_function('src/koru/autonomous_cycle.py', '_initialize_cycle_telemetry', 0, 1, 0).
python_function('src/koru/autonomous_cycle.py', '_heal_stale_socket', 0, 4, 4).
python_function('src/koru/autonomous_cycle.py', '_handle_autopilot_events', 2, 5, 5).
python_function('src/koru/autonomous_cycle.py', '_handle_queue_hygiene', 4, 3, 4).
python_function('src/koru/autonomous_cycle.py', '_handle_post_run_verify_ide', 5, 5, 7).
python_function('src/koru/autonomous_cycle.py', '_handle_scan_phase', 10, 9, 7).
python_function('src/koru/autonomous_cycle.py', '_build_queue_command', 2, 2, 0).
python_function('src/koru/autonomous_cycle.py', '_run_queue_loop', 4, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_emit_queue_iteration_event', 6, 7, 7).
python_function('src/koru/autonomous_cycle.py', '_handle_post_run_verify', 7, 11, 11).
python_function('src/koru/autonomous_cycle.py', '_handle_queue_loop_phase', 10, 2, 8).
python_function('src/koru/autonomous_cycle.py', '_handle_scan_after_idle', 11, 8, 7).
python_function('src/koru/autonomous_cycle.py', '_update_stagnation_state', 2, 3, 1).
python_function('src/koru/autonomous_cycle.py', '_waiting_ticket_has_label', 3, 14, 8).
python_function('src/koru/autonomous_cycle.py', '_handle_diagnostics', 15, 10, 8).
python_function('src/koru/autonomous_cycle.py', '_check_autopilot_skip_conditions', 12, 13, 4).
python_function('src/koru/autonomous_cycle.py', '_resolve_autopilot_drive_decision', 3, 4, 4).
python_function('src/koru/autonomous_cycle.py', '_drive_autopilot_once', 1, 4, 4).
python_function('src/koru/autonomous_cycle.py', '_reply_missing_autopilot_plugin', 1, 2, 3).
python_function('src/koru/autonomous_cycle.py', '_reply_needs_focus_retry', 1, 8, 3).
python_function('src/koru/autonomous_cycle.py', '_warn_autopilot_focus_retry', 2, 1, 1).
python_function('src/koru/autonomous_cycle.py', '_execute_autopilot_drive', 9, 6, 8).
python_function('src/koru/autonomous_cycle.py', '_update_autopilot_state', 5, 6, 1).
python_function('src/koru/autonomous_cycle.py', '_log_autopilot_result', 6, 9, 3).
python_function('src/koru/autonomous_cycle.py', '_handle_autopilot_phase', 19, 9, 9).
python_function('src/koru/autonomous_cycle.py', '_emit_cycle_completion_events', 16, 1, 3).
python_function('src/koru/autonomous_cycle.py', 'run_cycle', 0, 5, 23).
python_function('src/koru/autonomous_diagnostics.py', '_has_redup_module', 0, 2, 2).
python_function('src/koru/autonomous_diagnostics.py', 'build_idle_checks', 2, 11, 9).
python_function('src/koru/autonomous_diagnostics.py', 'run_idle_check_loop', 0, 6, 8).
python_function('src/koru/autonomous_diagnostics.py', 'create_diagnostic_ticket', 0, 2, 5).
python_function('src/koru/autonomous_diagnostics.py', 'clear_diagnostic_marker', 2, 1, 1).
python_function('src/koru/autonomous_diagnostics.py', 'run_command_check', 0, 2, 3).
python_function('src/koru/autonomous_diagnostics.py', 'read_wup_health', 0, 1, 1).
python_function('src/koru/autonomous_diagnostics.py', 'run_idle_diagnostics', 0, 3, 6).
python_function('src/koru/autonomous_env.py', 'apply_autonomous_env_overrides', 1, 1, 1).
python_function('src/koru/autonomous_parser.py', 'build_parser', 0, 1, 6).
python_function('src/koru/autonomous_parser.py', '_match_koru_auto_parts', 1, 14, 3).
python_function('src/koru/autonomous_parser.py', 'looks_like_autonomous_up_command', 1, 2, 3).
python_function('src/koru/autonomous_process_guard.py', 'command_project', 1, 5, 7).
python_function('src/koru/autonomous_process_guard.py', 'process_cwd', 1, 2, 3).
python_function('src/koru/autonomous_process_guard.py', 'ancestor_pids', 1, 7, 8).
python_function('src/koru/autonomous_process_guard.py', 'find_existing_autonomous_processes', 1, 11, 13).
python_function('src/koru/autonomous_process_guard.py', 'find_existing_wup_processes', 1, 11, 12).
python_function('src/koru/autonomous_process_guard.py', 'as_managed', 1, 1, 1).
python_function('src/koru/autonomous_process_guard.py', 'terminate_existing_processes', 1, 10, 5).
python_function('src/koru/autonomous_process_guard.py', 'confirm_replace_existing', 1, 3, 4).
python_function('src/koru/autonomous_startup.py', 'supports_autopilot_plugin_ide', 1, 1, 1).
python_function('src/koru/autonomous_startup.py', 'koru_distribution_version', 0, 2, 1).
python_function('src/koru/autonomous_startup.py', '_session_label', 0, 5, 2).
python_function('src/koru/autonomous_startup.py', '_terminal_agent_lane_from_env', 0, 4, 3).
python_function('src/koru/autonomous_startup.py', 'resolve_agent_lane_id', 2, 11, 6).
python_function('src/koru/autonomous_startup.py', 'resolve_autopilot_ide_for_autonomous', 2, 4, 2).
python_function('src/koru/autonomous_startup.py', 'build_startup_probe', 1, 15, 17).
python_function('src/koru/autonomous_startup.py', 'format_startup_banner', 1, 5, 2).
python_function('src/koru/autonomous_startup.py', 'format_post_startup_operator_hints', 1, 13, 3).
python_function('src/koru/autonomous_wup.py', '_wup_stdio_info', 1, 2, 1).
python_function('src/koru/autonomous_wup.py', '_wup_topology_gate', 2, 4, 2).
python_function('src/koru/autonomous_wup.py', '_build_wup_watch_config', 2, 1, 1).
python_function('src/koru/autonomous_wup.py', '_resolve_wup_testql_bin', 1, 5, 3).
python_function('src/koru/autonomous_wup.py', '_wup_cpu_throttle_arg', 1, 2, 1).
python_function('src/koru/autonomous_wup.py', '_wup_watch_command', 1, 3, 4).
python_function('src/koru/autonomous_wup.py', '_wup_autodetect', 1, 3, 2).
python_function('src/koru/autonomous_wup.py', '_wup_config_path', 1, 2, 0).
python_function('src/koru/autonomous_wup.py', '_load_project_env', 1, 10, 7).
python_function('src/koru/autonomous_wup.py', '_wup_subprocess_env', 1, 3, 5).
python_function('src/koru/autonomous_wup.py', '_parse_wup_services', 1, 4, 5).
python_function('src/koru/autonomous_wup.py', '_extract_docker_items', 1, 12, 6).
python_function('src/koru/autonomous_wup.py', '_profiled_compose_services', 1, 6, 7).
python_function('src/koru/autonomous_wup.py', '_compose_ps_command', 3, 2, 1).
python_function('src/koru/autonomous_wup.py', '_parse_compose_ps_json', 1, 10, 5).
python_function('src/koru/autonomous_wup.py', '_compose_service_ready', 1, 15, 3).
python_function('src/koru/autonomous_wup.py', '_wait_for_compose_service_ready', 4, 12, 12).
python_function('src/koru/autonomous_wup.py', '_ensure_wup_profiled_compose_services', 1, 10, 11).
python_function('src/koru/autonomous_wup.py', '_start_wup_watch', 1, 9, 9).
python_function('src/koru/autonomous_wup.py', '_stop_process', 2, 4, 5).
python_function('src/koru/autonomous_wup.py', '_load_wup_health', 1, 6, 6).
python_function('src/koru/autonomous_wup.py', '_identify_failing_services', 1, 3, 5).
python_function('src/koru/autonomous_wup.py', '_create_wup_diagnostic_tickets', 6, 6, 6).
python_function('src/koru/autonomous_wup.py', '_count_wup_events', 2, 5, 5).
python_function('src/koru/autonomous_wup.py', '_read_wup_health', 0, 7, 7).
python_function('src/koru/autonomy/env.py', 'env_truthy', 2, 3, 3).
python_function('src/koru/autonomy/env.py', 'effective_ticket_source_flags', 1, 3, 0).
python_function('src/koru/autonomy/env.py', '_env_ticket_sources', 2, 5, 5).
python_function('src/koru/autonomy/env.py', '_env_get', 3, 4, 3).
python_function('src/koru/autonomy/env.py', '_apply_ticket_and_diagnostics_env', 2, 6, 3).
python_function('src/koru/autonomy/env.py', '_apply_autopilot_env', 2, 6, 8).
python_function('src/koru/autonomy/env.py', '_apply_scan_env', 2, 3, 7).
python_function('src/koru/autonomy/env.py', '_apply_wup_env', 2, 11, 6).
python_function('src/koru/autonomy/env.py', '_apply_operator_env', 2, 7, 3).
python_function('src/koru/autonomy/env.py', 'apply_autoloop_env_to_args', 1, 1, 5).
python_function('src/koru/autonomy/env.py', 'autonomous_environ_doctor_probe', 1, 12, 7).
python_function('src/koru/autonomy/environment.py', 'probe_ide_presence', 1, 14, 12).
python_function('src/koru/autonomy/environment.py', 'probe_socket_health', 1, 4, 8).
python_function('src/koru/autonomy/environment.py', '_check_socket_health', 1, 2, 1).
python_function('src/koru/autonomy/environment.py', '_build_fixable_issues', 2, 9, 2).
python_function('src/koru/autonomy/environment.py', '_build_notes', 2, 5, 1).
python_function('src/koru/autonomy/environment.py', 'probe_environment', 1, 4, 8).
python_function('src/koru/autonomy/heal.py', 'remove_stale_socket', 1, 5, 2).
python_function('src/koru/autonomy/heal.py', 'heal_environment', 1, 3, 2).
python_function('src/koru/autonomy/heal.py', 'summarise', 1, 4, 4).
python_function('src/koru/autonomy/ide_work.py', 'extract_ticket_id_from_text', 1, 3, 3).
python_function('src/koru/autonomy/ide_work.py', '_parse_open_tickets', 1, 11, 8).
python_function('src/koru/autonomy/ide_work.py', 'fetch_next_open_ticket', 1, 5, 2).
python_function('src/koru/autonomy/ide_work.py', 'build_ide_work_prompt', 1, 12, 7).
python_function('src/koru/autonomy/ide_work.py', 'resolve_idle_drive_prompt', 1, 2, 2).
python_function('src/koru/autonomy/ide_work.py', '_parse_iso_datetime', 1, 5, 5).
python_function('src/koru/autonomy/ide_work.py', '_ticket_in_progress_started_at', 1, 3, 3).
python_function('src/koru/autonomy/ide_work.py', '_list_in_progress_tickets', 1, 9, 4).
python_function('src/koru/autonomy/ide_work.py', 'release_stale_in_progress_tickets', 1, 8, 9).
python_function('src/koru/autonomy/ide_work.py', 'resolve_in_progress_stale_minutes', 1, 10, 5).
python_function('src/koru/autonomy/ide_work.py', 'release_in_progress_tickets', 1, 6, 4).
python_function('src/koru/autonomy/operator_pipeline.py', '_operator_state_dir', 1, 1, 1).
python_function('src/koru/autonomy/operator_pipeline.py', '_marker_path', 2, 1, 0).
python_function('src/koru/autonomy/operator_pipeline.py', '_read_marker', 2, 3, 4).
python_function('src/koru/autonomy/operator_pipeline.py', '_write_marker', 3, 1, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_clear_marker', 2, 1, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_ticket_matches_step', 1, 11, 5).
python_function('src/koru/autonomy/operator_pipeline.py', '_ticket_text', 1, 10, 5).
python_function('src/koru/autonomy/operator_pipeline.py', '_ticket_matches_current_step', 2, 11, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_find_ticket_by_id', 2, 8, 7).
python_function('src/koru/autonomy/operator_pipeline.py', '_find_existing_step_ticket', 1, 11, 10).
python_function('src/koru/autonomy/operator_pipeline.py', '_close_resolved_step_ticket', 1, 5, 5).
python_function('src/koru/autonomy/operator_pipeline.py', '_mcp_koru_configured', 1, 7, 5).
python_function('src/koru/autonomy/operator_pipeline.py', '_candidate_planfile_health_urls', 1, 7, 10).
python_function('src/koru/autonomy/operator_pipeline.py', '_planfile_api_ok', 1, 5, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_operator_autostart_server_enabled', 0, 1, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_try_start_planfile_api', 1, 7, 7).
python_function('src/koru/autonomy/operator_pipeline.py', '_os_profile_ok', 2, 3, 2).
python_function('src/koru/autonomy/operator_pipeline.py', '_host_injectors_ok', 0, 8, 5).
python_function('src/koru/autonomy/operator_pipeline.py', 'build_operator_steps', 0, 14, 7).
python_function('src/koru/autonomy/operator_pipeline.py', '_emit_step', 1, 4, 3).
python_function('src/koru/autonomy/operator_pipeline.py', '_create_step_ticket', 2, 6, 4).
python_function('src/koru/autonomy/operator_pipeline.py', '_ensure_planfile_api', 3, 2, 2).
python_function('src/koru/autonomy/operator_pipeline.py', '_discard_stale_pending_marker', 2, 7, 4).
python_function('src/koru/autonomy/operator_pipeline.py', '_close_finished_step_marker', 2, 5, 1).
python_function('src/koru/autonomy/operator_pipeline.py', '_recover_matching_step_ticket', 2, 7, 4).
python_function('src/koru/autonomy/operator_pipeline.py', '_create_pending_step_ticket', 2, 5, 2).
python_function('src/koru/autonomy/operator_pipeline.py', '_process_operator_step', 10, 1, 6).
python_function('src/koru/autonomy/operator_pipeline.py', '_emit_operator_step_event', 6, 3, 1).
python_function('src/koru/autonomy/operator_pipeline.py', 'run_startup_operator_pipeline', 0, 4, 14).
python_function('src/koru/autonomy/operator_pipeline.py', 'sys_stdout_for_format', 1, 2, 0).
python_function('src/koru/autonomy/post_run_verify.py', '_truthy_env', 1, 2, 3).
python_function('src/koru/autonomy/post_run_verify.py', '_extract_post_run_verify_block', 1, 3, 2).
python_function('src/koru/autonomy/post_run_verify.py', '_parse_verify_commands', 1, 6, 4).
python_function('src/koru/autonomy/post_run_verify.py', '_parse_verify_on_failure', 1, 3, 4).
python_function('src/koru/autonomy/post_run_verify.py', '_parse_verify_max_output', 1, 2, 3).
python_function('src/koru/autonomy/post_run_verify.py', '_parse_verify_ide_settings', 1, 3, 3).
python_function('src/koru/autonomy/post_run_verify.py', 'load_post_run_verify_config', 1, 7, 12).
python_function('src/koru/autonomy/post_run_verify.py', '_parse_iso_datetime', 1, 5, 5).
python_function('src/koru/autonomy/post_run_verify.py', 'fetch_ticket_status', 2, 9, 7).
python_function('src/koru/autonomy/post_run_verify.py', 'fetch_recently_done_ticket_ids', 1, 14, 10).
python_function('src/koru/autonomy/post_run_verify.py', '_record_verify_outcomes', 2, 5, 4).
python_function('src/koru/autonomy/post_run_verify.py', 'verify_after_ide_work', 2, 13, 6).
python_function('src/koru/autonomy/post_run_verify.py', 'run_verify_commands', 2, 8, 4).
python_function('src/koru/autonomy/post_run_verify.py', '_truncate', 2, 2, 3).
python_function('src/koru/autonomy/post_run_verify.py', 'apply_verify_failure', 2, 2, 2).
python_function('src/koru/autonomy/post_run_verify.py', 'verify_completed_tickets', 2, 8, 3).
python_function('src/koru/autonomy/prompts.py', 'build_prompt', 0, 10, 2).
python_function('src/koru/autonomy/telemetry_snapshot.py', 'autonomy_telemetry_path', 1, 1, 1).
python_function('src/koru/autonomy/telemetry_snapshot.py', 'write_autonomy_cycle_telemetry', 1, 2, 7).
python_function('src/koru/autonomy/telemetry_snapshot.py', 'build_autonomy_loop_brief', 1, 5, 8).
python_function('src/koru/autopilot/calibrate_cli.py', 'resolve_session_ides', 1, 9, 6).
python_function('src/koru/autopilot/calibrate_cli.py', 'action_calibrate', 1, 5, 13).
python_function('src/koru/autopilot/calibrate_cli.py', 'capture_ide_profile', 4, 4, 9).
python_function('src/koru/autopilot/calibrate_cli.py', 'detect_duplicate_coordinates', 1, 3, 4).
python_function('src/koru/autopilot/calibrate_cli.py', 'action_session_start', 1, 13, 12).
python_function('src/koru/autopilot/cli_command.py', '_action_calibrate', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_session_start', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_build_parser', 0, 1, 7).
python_function('src/koru/autopilot/cli_command.py', '_client', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_auto_direct_fallback_enabled', 0, 2, 3).
python_function('src/koru/autopilot/cli_command.py', '_should_fallback_to_direct', 2, 7, 5).
python_function('src/koru/autopilot/cli_command.py', '_print_drive_delay_message', 1, 1, 2).
python_function('src/koru/autopilot/cli_command.py', '_handle_os_injector_fallback', 3, 3, 1).
python_function('src/koru/autopilot/cli_command.py', '_run_direct_drive', 2, 14, 12).
python_function('src/koru/autopilot/cli_command.py', '_action_drive', 1, 10, 13).
python_function('src/koru/autopilot/cli_command.py', '_action_status', 1, 1, 2).
python_function('src/koru/autopilot/cli_command.py', '_action_shutdown', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_doctor', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_setup_host', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_manage', 1, 4, 6).
python_function('src/koru/autopilot/cli_command.py', '_action_install_plugin', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_install_plugin_jetbrains', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_build_brief', 1, 1, 2).
python_function('src/koru/autopilot/cli_command.py', '_action_handoff', 1, 9, 10).
python_function('src/koru/autopilot/cli_command.py', '_action_tail', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', '_action_install_unit', 1, 1, 1).
python_function('src/koru/autopilot/cli_command.py', 'autopilot_main', 1, 1, 3).
python_function('src/koru/autopilot/daemon_cli.py', 'action_daemon', 1, 15, 18).
python_function('src/koru/autopilot/daemon_cli.py', 'action_shutdown', 1, 1, 2).
python_function('src/koru/autopilot/daemon_cli.py', 'action_ide_list', 1, 5, 3).
python_function('src/koru/autopilot/doctor_cli.py', 'doctor_fix_payload', 0, 2, 2).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_session_info', 2, 3, 1).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_backends', 1, 3, 1).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_ides', 0, 4, 4).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_fix_steps', 1, 8, 3).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_text', 4, 1, 4).
python_function('src/koru/autopilot/doctor_cli.py', 'render_doctor_json', 4, 4, 5).
python_function('src/koru/autopilot/doctor_cli.py', 'action_doctor', 1, 4, 6).
python_function('src/koru/autopilot/doctor_cli.py', 'action_setup_host', 1, 1, 1).
python_function('src/koru/autopilot/install_manager.py', '_source_root', 0, 1, 2).
python_function('src/koru/autopilot/install_manager.py', '_source_version', 1, 3, 5).
python_function('src/koru/autopilot/install_manager.py', '_package_version', 0, 2, 1).
python_function('src/koru/autopilot/install_manager.py', '_repo_koru_bin', 1, 3, 2).
python_function('src/koru/autopilot/install_manager.py', '_path_koru_bin', 0, 2, 3).
python_function('src/koru/autopilot/install_manager.py', '_is_pyenv_shim', 1, 3, 1).
python_function('src/koru/autopilot/install_manager.py', '_expected_plugin_version', 1, 3, 4).
python_function('src/koru/autopilot/install_manager.py', '_resolve_ide', 1, 6, 4).
python_function('src/koru/autopilot/install_manager.py', '_manager_socket_path', 2, 8, 4).
python_function('src/koru/autopilot/install_manager.py', '_daemon_status', 1, 3, 6).
python_function('src/koru/autopilot/install_manager.py', '_plugin_for_ide', 2, 6, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_koru_path_issues', 2, 4, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_pyenv_shim_issue', 1, 2, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_version_mismatch_issue', 2, 4, 1).
python_function('src/koru/autopilot/install_manager.py', '_check_daemon_issues', 1, 2, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_version_missing_issue', 3, 4, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_installed_version_mismatch_issue', 2, 4, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_installed_ok_but_not_connected_issue', 3, 6, 3).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_live_host_stale_issue', 3, 12, 6).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_version_mismatch_issue', 3, 6, 2).
python_function('src/koru/autopilot/install_manager.py', '_check_plugin_not_connected_issue', 3, 3, 2).
python_function('src/koru/autopilot/install_manager.py', '_issue_list', 0, 3, 12).
python_function('src/koru/autopilot/install_manager.py', 'collect_install_manager_report', 0, 11, 19).
python_function('src/koru/autopilot/install_manager.py', 'repair_installation', 0, 6, 9).
python_function('src/koru/autopilot/install_manager.py', 'format_install_manager_report', 1, 13, 6).
python_function('src/koru/autopilot/install_plugin_cli.py', 'plugin_repo_dir', 0, 1, 2).
python_function('src/koru/autopilot/install_plugin_cli.py', '_plugin_package_version', 1, 4, 5).
python_function('src/koru/autopilot/install_plugin_cli.py', '_versioned_plugin_vsix_candidates', 1, 2, 1).
python_function('src/koru/autopilot/install_plugin_cli.py', 'jetbrains_plugin_repo_dir', 0, 1, 2).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_plugin_vsix_path', 1, 6, 9).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_jetbrains_plugin_dir', 1, 4, 6).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_gradle_bin', 1, 6, 9).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_jetbrains_plugin_artifact', 1, 2, 4).
python_function('src/koru/autopilot/install_plugin_cli.py', 'ide_from_terminal_env', 0, 5, 5).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_plugin_target_ide', 1, 10, 9).
python_function('src/koru/autopilot/install_plugin_cli.py', 'resolve_plugin_editor_bin', 1, 6, 3).
python_function('src/koru/autopilot/install_plugin_cli.py', 'render_install_plugin_dry_run', 5, 2, 4).
python_function('src/koru/autopilot/install_plugin_cli.py', 'render_install_plugin_result', 7, 6, 2).
python_function('src/koru/autopilot/install_plugin_cli.py', 'action_install_plugin', 1, 6, 10).
python_function('src/koru/autopilot/install_plugin_cli.py', '_render_jetbrains_failure', 0, 4, 3).
python_function('src/koru/autopilot/install_plugin_cli.py', '_render_jetbrains_success', 0, 4, 3).
python_function('src/koru/autopilot/install_plugin_cli.py', 'action_install_plugin_jetbrains', 1, 10, 11).
python_function('src/koru/autopilot/local_manager.py', 'autopilot_local_manager_session', 0, 2, 3).
python_function('src/koru/autopilot/local_manager.py', 'start_autopilot_manager_heartbeat', 2, 2, 10).
python_function('src/koru/autopilot/systemd_cli.py', 'systemd_user_dir', 0, 1, 1).
python_function('src/koru/autopilot/systemd_cli.py', 'resolve_koru_bin', 0, 6, 6).
python_function('src/koru/autopilot/systemd_cli.py', 'render_unit', 1, 5, 7).
python_function('src/koru/autopilot/systemd_cli.py', 'action_install_unit', 1, 6, 8).
python_function('src/koru/autopilot/tail_cli.py', 'format_tail_entry', 1, 5, 4).
python_function('src/koru/autopilot/tail_cli.py', 'render_tail_json', 1, 3, 4).
python_function('src/koru/autopilot/tail_cli.py', 'render_tail_text', 1, 3, 3).
python_function('src/koru/autopilot/tail_cli.py', 'action_tail', 1, 6, 7).
python_function('src/koru/autopilot/utils/client_helpers.py', 'call_daemon_method', 4, 4, 5).
python_function('src/koru/autopilot/utils/client_helpers.py', 'resolve_xdg_path', 1, 2, 3).
python_function('src/koru/bootstrap.py', 'load_flat_pipeline', 1, 9, 9).
python_function('src/koru/bootstrap.py', '_validate_id', 2, 4, 4).
python_function('src/koru/bootstrap.py', '_validate_name', 1, 4, 3).
python_function('src/koru/bootstrap.py', '_validate_status', 1, 3, 4).
python_function('src/koru/bootstrap.py', '_validate_priority', 1, 4, 5).
python_function('src/koru/bootstrap.py', '_validate_executor', 1, 5, 6).
python_function('src/koru/bootstrap.py', '_validate_execution_state', 1, 4, 4).
python_function('src/koru/bootstrap.py', '_validate_blocked_by', 1, 6, 5).
python_function('src/koru/bootstrap.py', '_validate_task', 2, 3, 9).
python_function('src/koru/bootstrap.py', '_validate_cross_task_dependencies', 1, 10, 7).
python_function('src/koru/bootstrap.py', 'validate_flat_pipeline', 1, 3, 7).
python_function('src/koru/bootstrap.py', '_detect_cycle', 1, 10, 7).
python_function('src/koru/bootstrap.py', 'materialize_to_planfile', 2, 6, 12).
python_function('src/koru/bootstrap.py', '_normalise_task', 1, 8, 5).
python_function('src/koru/bootstrap.py', '_next_id_after', 2, 5, 7).
python_function('src/koru/bootstrap.py', 'import_flat_pipeline', 2, 9, 10).
python_function('src/koru/bootstrap.py', '_infer_prefix', 1, 4, 3).
python_function('src/koru/cli/__init__.py', '_load_legacy_cli_module', 0, 4, 7).
python_function('src/koru/cli/__init__.py', '__getattr__', 1, 1, 1).
python_function('src/koru/cli.py', '_env_truthy', 1, 1, 3).
python_function('src/koru/cli.py', '_command_value', 1, 2, 2).
python_function('src/koru/cli.py', '_cli_version', 0, 2, 1).
python_function('src/koru/cli.py', '_build_parser', 0, 1, 4).
python_function('src/koru/cli.py', '_build_tools_parser', 0, 1, 5).
python_function('src/koru/cli.py', '_tools_main', 1, 7, 13).
python_function('src/koru/cli.py', '_build_task_parser', 0, 1, 3).
python_function('src/koru/cli.py', '_build_serve_parser', 0, 1, 4).
python_function('src/koru/cli.py', '_build_local_serve_parser', 0, 1, 2).
python_function('src/koru/cli.py', '_build_gate_parser', 0, 1, 6).
python_function('src/koru/cli.py', '_gate_main', 1, 5, 7).
python_function('src/koru/cli.py', '_build_gc_parser', 0, 1, 5).
python_function('src/koru/cli.py', '_gc_main', 1, 1, 7).
python_function('src/koru/cli.py', '_build_queue_parser', 0, 1, 5).
python_function('src/koru/cli.py', '_render_clean_report_text', 1, 12, 3).
python_function('src/koru/cli.py', '_queue_main', 1, 9, 9).
python_function('src/koru/cli.py', '_build_agent_parser', 0, 1, 3).
python_function('src/koru/cli.py', '_task_main', 1, 11, 14).
python_function('src/koru/cli.py', '_serve_main', 1, 1, 1).
python_function('src/koru/cli.py', '_local_serve_main', 1, 1, 1).
python_function('src/koru/cli.py', '_agent_main', 1, 3, 7).
python_function('src/koru/cli.py', '_is_bare_invocation', 1, 8, 0).
python_function('src/koru/cli.py', '_build_topology_parser', 0, 1, 3).
python_function('src/koru/cli.py', '_render_topology_text', 1, 1, 1).
python_function('src/koru/cli.py', '_topology_main', 1, 12, 15).
python_function('src/koru/cli.py', '_build_runtime_context_parser', 0, 1, 3).
python_function('src/koru/cli.py', '_render_runtime_context_text', 1, 14, 3).
python_function('src/koru/cli.py', '_runtime_context_main', 1, 3, 7).
python_function('src/koru/cli.py', '_init_ci_main', 1, 1, 1).
python_function('src/koru/cli.py', '_mcp_serve_main', 1, 1, 1).
python_function('src/koru/cli.py', '_agent_backends_main', 1, 8, 9).
python_function('src/koru/cli.py', '_init_ide_main', 1, 1, 1).
python_function('src/koru/cli.py', '_refactor_planfile_handoff_main', 1, 1, 6).
python_function('src/koru/cli.py', 'ide_router_main', 1, 3, 7).
python_function('src/koru/cli.py', '_dsl_main', 1, 1, 1).
python_function('src/koru/cli.py', '_api_main', 1, 1, 1).
python_function('src/koru/cli.py', '_peek_project_from_argv', 1, 5, 8).
python_function('src/koru/cli.py', '_auto_main', 1, 6, 5).
python_function('src/koru/cli.py', '_doctor_main', 2, 12, 12).
python_function('src/koru/cli.py', '_doctor_fix_payload', 1, 5, 2).
python_function('src/koru/cli.py', '_render_doctor_with_fix', 2, 6, 5).
python_function('src/koru/cli.py', '_init_main', 1, 7, 8).
python_function('src/koru/cli.py', '_init_agent_lane_main', 1, 8, 7).
python_function('src/koru/cli.py', '_context_main', 1, 2, 5).
python_function('src/koru/cli.py', '_bootstrap_main', 1, 5, 7).
python_function('src/koru/cli.py', '_watch_main', 1, 2, 5).
python_function('src/koru/cli.py', '_queue_run_main', 1, 2, 4).
python_function('src/koru/cli.py', '_command_loop_main', 1, 7, 7).
python_function('src/koru/cli.py', 'main', 0, 12, 12).
python_function('src/koru/cli_doctor.py', 'doctor_fix_payload', 1, 5, 2).
python_function('src/koru/cli_doctor.py', 'render_doctor_with_fix', 2, 6, 5).
python_function('src/koru/cli_doctor.py', 'doctor_main', 2, 12, 12).
python_function('src/koru/cli_gate.py', 'build_gate_parser', 0, 1, 6).
python_function('src/koru/cli_gate.py', 'gate_main', 1, 5, 7).
python_function('src/koru/cli_gc.py', 'build_gc_parser', 0, 1, 5).
python_function('src/koru/cli_gc.py', 'gc_main', 1, 1, 7).
python_function('src/koru/cli_init.py', 'init_main', 1, 7, 8).
python_function('src/koru/cli_init.py', 'init_agent_lane_main', 1, 3, 5).
python_function('src/koru/cli_queue.py', 'build_queue_parser', 0, 1, 5).
python_function('src/koru/cli_queue.py', 'render_clean_report_text', 1, 12, 3).
python_function('src/koru/cli_queue.py', 'queue_main', 1, 9, 9).
python_function('src/koru/cli_scan.py', 'build_scan_parser', 0, 1, 3).
python_function('src/koru/cli_scan.py', 'render_scan_text', 1, 7, 4).
python_function('src/koru/cli_scan.py', 'render_scan_markdown', 1, 7, 3).
python_function('src/koru/cli_scan.py', 'scan_main', 1, 3, 9).
python_function('src/koru/cli_topology.py', 'build_topology_parser', 0, 1, 3).
python_function('src/koru/cli_topology.py', 'render_topology_text', 1, 1, 1).
python_function('src/koru/cli_topology.py', 'topology_main', 1, 12, 15).
python_function('src/koru/cli_watch.py', 'watch_main', 1, 2, 5).
python_function('src/koru/context.py', '_is_fixture_ticket', 1, 4, 6).
python_function('src/koru/context.py', '_resolve_include_fixtures', 1, 2, 3).
python_function('src/koru/context.py', '_load_project_dotenv', 1, 2, 3).
python_function('src/koru/context.py', '_planfile_command_base', 0, 3, 3).
python_function('src/koru/context.py', '_planfile_env', 0, 1, 0).
python_function('src/koru/context.py', '_fetch_all_tickets', 1, 9, 4).
python_function('src/koru/context.py', '_run_planfile', 3, 2, 4).
python_function('src/koru/context.py', '_safe_json', 1, 3, 1).
python_function('src/koru/context.py', '_git_probe', 1, 4, 4).
python_function('src/koru/context.py', '_build_ticket_args', 2, 3, 1).
python_function('src/koru/context.py', '_try_fallback_ticket_list', 2, 1, 1).
python_function('src/koru/context.py', '_process_list_payload', 2, 12, 5).
python_function('src/koru/context.py', '_process_dict_payload', 3, 4, 2).
python_function('src/koru/context.py', '_extract_error_from_stderr', 1, 7, 3).
python_function('src/koru/context.py', '_execute_ticket_query', 4, 5, 3).
python_function('src/koru/context.py', '_handle_idle_queue', 3, 1, 2).
python_function('src/koru/context.py', '_parse_ticket_response', 5, 10, 10).
python_function('src/koru/context.py', '_fetch_ticket_data', 6, 4, 3).
python_function('src/koru/context.py', 'build_context', 0, 6, 16).
python_function('src/koru/context.py', '_load_sprint_data', 1, 6, 4).
python_function('src/koru/context.py', '_find_blocking_tickets', 1, 6, 6).
python_function('src/koru/context.py', '_promote_blocking_to_critical', 2, 5, 3).
python_function('src/koru/context.py', '_promote_bug_priority', 1, 10, 4).
python_function('src/koru/context.py', '_write_sprint_data', 2, 2, 4).
python_function('src/koru/context.py', '_auto_promote_blocking_tickets', 2, 4, 5).
python_function('src/koru/context.py', '_build_instructions', 2, 2, 3).
python_function('src/koru/context.py', '_build_setup_instructions', 0, 1, 0).
python_function('src/koru/context.py', '_build_policy_rules', 1, 8, 1).
python_function('src/koru/context.py', '_build_ticket_rules', 1, 8, 6).
python_function('src/koru/context.py', '_build_shared_rules', 2, 1, 3).
python_function('src/koru/context.py', '_build_self_service', 2, 5, 2).
python_function('src/koru/context.py', '_render_header', 1, 1, 0).
python_function('src/koru/context.py', '_render_environment', 2, 11, 5).
python_function('src/koru/context.py', '_render_agent_lanes', 1, 3, 2).
python_function('src/koru/context.py', '_render_autonomous_mode', 0, 2, 1).
python_function('src/koru/context.py', '_render_ai_tool_support_2026', 0, 1, 0).
python_function('src/koru/context.py', '_render_semcod_tools', 1, 11, 3).
python_function('src/koru/context.py', '_render_setup_required', 1, 1, 0).
python_function('src/koru/context.py', '_render_active_ticket', 1, 7, 5).
python_function('src/koru/context.py', '_compact_ticket_error', 1, 5, 5).
python_function('src/koru/context.py', '_render_no_active_ticket', 1, 1, 1).
python_function('src/koru/context.py', '_render_gates', 1, 6, 6).
python_function('src/koru/context.py', '_render_project_pipeline', 1, 9, 3).
python_function('src/koru/context.py', '_render_policy', 1, 3, 2).
python_function('src/koru/context.py', '_render_rules', 1, 2, 1).
python_function('src/koru/context.py', '_render_self_service', 1, 2, 2).
python_function('src/koru/context.py', '_render_dashboard', 0, 1, 0).
python_function('src/koru/context.py', '_render_autonomy_loop_brief', 1, 8, 5).
python_function('src/koru/context.py', 'render_markdown_handoff', 1, 10, 20).
python_function('src/koru/context_render.py', 'render_header', 1, 1, 0).
python_function('src/koru/context_render.py', 'render_environment', 2, 11, 5).
python_function('src/koru/context_render.py', 'render_agent_lanes', 1, 3, 2).
python_function('src/koru/context_render.py', 'render_autonomous_mode', 0, 2, 1).
python_function('src/koru/context_render.py', 'render_ai_tool_support_2026', 0, 1, 0).
python_function('src/koru/context_render.py', 'render_semcod_tools', 1, 11, 3).
python_function('src/koru/context_render.py', 'render_setup_required', 1, 1, 0).
python_function('src/koru/context_render.py', 'render_active_ticket', 1, 7, 5).
python_function('src/koru/context_render.py', '_compact_ticket_error', 1, 5, 5).
python_function('src/koru/context_render.py', 'render_no_active_ticket', 1, 1, 1).
python_function('src/koru/context_render.py', 'render_gates', 1, 6, 6).
python_function('src/koru/context_render.py', 'render_project_pipeline', 1, 9, 3).
python_function('src/koru/context_render.py', 'render_policy', 1, 3, 2).
python_function('src/koru/context_render.py', 'render_rules', 1, 2, 1).
python_function('src/koru/context_render.py', 'render_self_service', 1, 2, 2).
python_function('src/koru/context_render.py', 'render_dashboard', 0, 1, 0).
python_function('src/koru/context_render.py', 'render_autonomy_loop_brief', 1, 8, 5).
python_function('src/koru/context_render.py', 'render_markdown_handoff', 1, 10, 20).
python_function('src/koru/dev_sync.py', '_default_semcod_root', 0, 1, 1).
python_function('src/koru/dev_sync.py', '_run', 2, 1, 2).
python_function('src/koru/dev_sync.py', '_is_dirty', 2, 2, 3).
python_function('src/koru/dev_sync.py', '_pull_repo', 2, 7, 3).
python_function('src/koru/dev_sync.py', 'sync_developer_packages', 0, 9, 10).
python_function('src/koru/dev_sync.py', 'dev_main', 1, 7, 14).
python_function('src/koru/doctor.py', 'run_diagnostics', 1, 6, 6).
python_function('src/koru/doctor.py', '_check_agent_backends_registry', 1, 1, 3).
python_function('src/koru/doctor.py', '_check_git_repo', 1, 3, 2).
python_function('src/koru/doctor.py', '_check_planfile_binary', 1, 8, 6).
python_function('src/koru/doctor.py', '_planfile_version_argv', 0, 3, 4).
python_function('src/koru/doctor.py', '_check_koru_package_version', 1, 2, 1).
python_function('src/koru/doctor.py', '_check_planfile_cli_version', 1, 9, 9).
python_function('src/koru/doctor.py', '_check_planfile_config', 1, 4, 6).
python_function('src/koru/doctor.py', '_check_planfile_sprints', 1, 10, 11).
python_function('src/koru/doctor.py', '_check_planfile_sprints_yaml', 1, 6, 8).
python_function('src/koru/doctor.py', '_check_runtime_dir', 1, 6, 4).
python_function('src/koru/doctor.py', '_check_koru_project_pipeline', 1, 7, 8).
python_function('src/koru/doctor.py', '_check_policy_yaml', 1, 11, 9).
python_function('src/koru/doctor.py', '_check_gitignore', 1, 4, 5).
python_function('src/koru/doctor.py', '_resolve_pytest_collect_timeout', 0, 4, 3).
python_function('src/koru/doctor.py', '_check_pytest_collect', 1, 8, 5).
python_function('src/koru/doctor.py', '_check_inotify_watches', 1, 5, 5).
python_function('src/koru/doctor.py', '_check_wup_binary', 1, 2, 1).
python_function('src/koru/doctor.py', '_check_ci_command', 1, 5, 6).
python_function('src/koru/doctor.py', 'render_text', 1, 6, 10).
python_function('src/koru/dotenv_loader.py', '_parse_value', 1, 5, 3).
python_function('src/koru/dotenv_loader.py', 'parse_dotenv', 1, 5, 6).
python_function('src/koru/dotenv_loader.py', 'load_dotenv', 1, 7, 5).
python_function('src/koru/events.py', 'emit_management_event', 0, 8, 6).
python_function('src/koru/events.py', 'main', 0, 4, 7).
python_function('src/koru/gate.py', 'parse_authorizations', 1, 12, 9).
python_function('src/koru/gate.py', '_resolve_actor', 1, 4, 1).
python_function('src/koru/gate.py', '_planfile_base', 0, 4, 3).
python_function('src/koru/gate.py', 'authorize_gate', 1, 9, 12).
python_function('src/koru/gc.py', '_now_utc', 0, 1, 1).
python_function('src/koru/gc.py', '_parse_ts', 1, 3, 2).
python_function('src/koru/gc.py', '_planfile_env', 0, 1, 0).
python_function('src/koru/gc.py', '_run_planfile', 3, 6, 6).
python_function('src/koru/gc.py', '_load_tickets_from_sprint', 2, 7, 6).
python_function('src/koru/gc.py', '_archive_tickets', 2, 2, 6).
python_function('src/koru/gc.py', 'collect_gc_candidates', 1, 9, 12).
python_function('src/koru/gc.py', '_apply_keep_last', 3, 7, 6).
python_function('src/koru/gc.py', '_archive_tickets_before_delete', 3, 5, 3).
python_function('src/koru/gc.py', '_delete_tickets', 3, 6, 3).
python_function('src/koru/gc.py', 'run_gc', 1, 11, 8).
python_function('src/koru/gc_cli_helpers.py', 'gc_statuses_from_args', 1, 3, 3).
python_function('src/koru/gc_cli_helpers.py', 'gc_result_to_json', 1, 3, 1).
python_function('src/koru/gc_cli_helpers.py', 'print_gc_text_report', 1, 12, 4).
python_function('src/koru/gc_cli_helpers.py', 'emit_gc_management_event', 2, 2, 3).
python_function('src/koru/gc_cli_helpers.py', 'print_gc_report', 2, 2, 4).
python_function('src/koru/ide_client.py', 'adapt_legacy_autopilot_client', 1, 1, 1).
python_function('src/koru/ide_client.py', 'build_legacy_ide_client', 0, 1, 2).
python_function('src/koru/ide_client.py', 'build_koruide_client', 0, 1, 1).
python_function('src/koru/ide_client.py', 'build_ide_client', 0, 3, 5).
python_function('src/koru/ide_router.py', 'is_headless_environment', 1, 8, 4).
python_function('src/koru/ide_router.py', 'resolve_ide_route', 0, 7, 5).
python_function('src/koru/ide_runtime.py', 'build_host_setup_report', 0, 1, 1).
python_function('src/koru/ide_runtime.py', 'detect_running_ides', 0, 5, 8).
python_function('src/koru/init.py', 'init_project', 1, 7, 21).
python_function('src/koru/init.py', 'refresh_init_agent_lane', 1, 4, 11).
python_function('src/koru/init.py', '_init_auto_agent_lane', 1, 6, 5).
python_function('src/koru/init.py', '_read_persisted_agent_lane', 1, 12, 14).
python_function('src/koru/init.py', '_resolve_init_agent_lane', 2, 4, 4).
python_function('src/koru/init.py', 'resolve_project_agent_lane', 2, 1, 2).
python_function('src/koru/init.py', '_write_autopilot_host_setup_script', 1, 1, 5).
python_function('src/koru/init.py', '_write_agent_lane_artifacts', 2, 2, 9).
python_function('src/koru/init.py', '_remove_agent_lane_artifacts', 1, 4, 4).
python_function('src/koru/init.py', '_write_policy_stub_if_absent', 1, 3, 6).
python_function('src/koru/init.py', '_ensure_gitignore_entry', 1, 8, 9).
python_function('src/koru/init_host_environment.py', '_read_os_release', 0, 6, 7).
python_function('src/koru/init_host_environment.py', '_id_group_names', 0, 4, 3).
python_function('src/koru/init_host_environment.py', '_uinput_snapshot', 0, 4, 6).
python_function('src/koru/init_host_environment.py', 'build_host_environment_report', 0, 2, 11).
python_function('src/koru/init_host_environment.py', '_build_backend_steps', 3, 9, 2).
python_function('src/koru/init_host_environment.py', '_build_pm_steps', 2, 5, 2).
python_function('src/koru/init_host_environment.py', '_recommended_next_steps', 2, 3, 6).
python_function('src/koru/init_host_environment.py', '_render_session_section', 1, 1, 1).
python_function('src/koru/init_host_environment.py', '_render_os_section', 1, 3, 1).
python_function('src/koru/init_host_environment.py', '_render_injector_section', 1, 5, 2).
python_function('src/koru/init_host_environment.py', '_render_clipboard_section', 1, 2, 1).
python_function('src/koru/init_host_environment.py', '_render_uinput_section', 1, 3, 1).
python_function('src/koru/init_host_environment.py', '_render_next_steps_section', 1, 3, 2).
python_function('src/koru/init_host_environment.py', '_render_human_actions_section', 1, 3, 2).
python_function('src/koru/init_host_environment.py', '_render_apt_suggestion_section', 1, 2, 1).
python_function('src/koru/init_host_environment.py', '_render_host_environment_md', 1, 1, 10).
python_function('src/koru/init_host_environment.py', 'write_host_environment_bundle', 1, 2, 8).
python_function('src/koru/local_manager_client.py', '_truthy', 1, 2, 2).
python_function('src/koru/local_manager_client.py', '_koru_version', 0, 2, 1).
python_function('src/koru/local_manager_client.py', 'default_local_manager_url', 0, 7, 4).
python_function('src/koru/local_manager_client.py', 'lifecycle_decision_action', 1, 4, 3).
python_function('src/koru/local_manager_client.py', 'lifecycle_should_stop', 1, 1, 1).
python_function('src/koru/local_manager_state.py', 'utc_now', 0, 1, 3).
python_function('src/koru/local_manager_state.py', 'koru_version', 0, 2, 1).
python_function('src/koru/local_manager_state.py', 'normalize_capabilities', 1, 6, 5).
python_function('src/koru/local_manager_state.py', '_action_type', 1, 3, 2).
python_function('src/koru/local_manager_state.py', '_required_capabilities', 1, 3, 2).
python_function('src/koru/local_manager_state.py', '_version_key', 1, 4, 4).
python_function('src/koru/local_service.py', '_env_int', 2, 3, 3).
python_function('src/koru/local_service.py', '_read_bounded_json_object', 1, 7, 6).
python_function('src/koru/local_service.py', 'default_local_service_config', 0, 2, 6).
python_function('src/koru/local_service.py', '_build_handler', 2, 1, 28).
python_function('src/koru/local_service.py', 'build_local_service_server', 1, 1, 4).
python_function('src/koru/local_service.py', 'run_local_service', 1, 3, 6).
python_function('src/koru/local_service.py', 'start_local_service_background', 1, 1, 4).
python_function('src/koru/loop.py', '_search_root_for_include', 2, 6, 6).
python_function('src/koru/loop.py', 'discover_repositories', 2, 5, 10).
python_function('src/koru/loop.py', '_default_runner', 2, 1, 1).
python_function('src/koru/loop.py', 'run_closed_loop', 0, 12, 12).
python_function('src/koru/mcp_provision.py', '_windsurf_global_config', 0, 1, 1).
python_function('src/koru/mcp_provision.py', '_cursor_project_config', 1, 1, 0).
python_function('src/koru/mcp_provision.py', '_vscode_project_config', 1, 1, 0).
python_function('src/koru/mcp_provision.py', '_windsurf_project_config', 1, 1, 0).
python_function('src/koru/mcp_provision.py', '_zed_project_settings', 1, 1, 0).
python_function('src/koru/mcp_provision.py', '_resolved_koru_command', 0, 2, 1).
python_function('src/koru/mcp_provision.py', '_koru_mcp_entry', 0, 1, 1).
python_function('src/koru/mcp_provision.py', '_koru_mcp_entry_cursor', 0, 1, 1).
python_function('src/koru/mcp_provision.py', '_maybe_upgrade_koru_command', 1, 5, 3).
python_function('src/koru/mcp_provision.py', 'detect_ides', 0, 10, 8).
python_function('src/koru/mcp_provision.py', '_read_json', 1, 3, 3).
python_function('src/koru/mcp_provision.py', '_write_json', 2, 2, 4).
python_function('src/koru/mcp_provision.py', 'provision_windsurf', 1, 4, 9).
python_function('src/koru/mcp_provision.py', 'provision_cursor', 1, 3, 7).
python_function('src/koru/mcp_provision.py', 'provision_vscode', 1, 3, 7).
python_function('src/koru/mcp_provision.py', 'provision_vscodium', 1, 1, 1).
python_function('src/koru/mcp_provision.py', 'provision_zed', 1, 3, 7).
python_function('src/koru/mcp_provision.py', 'remove_from_config', 1, 3, 4).
python_function('src/koru/mcp_provision.py', 'ensure_koru_mcp_not_disabled', 1, 10, 15).
python_function('src/koru/mcp_provision.py', '_resolve_targets', 1, 5, 5).
python_function('src/koru/mcp_provision.py', '_removal_paths_for_ide', 2, 6, 5).
python_function('src/koru/mcp_provision.py', '_apply_target', 2, 5, 5).
python_function('src/koru/mcp_provision.py', '_render_results', 2, 5, 3).
python_function('src/koru/mcp_provision.py', 'init_ide_main', 1, 2, 9).
python_function('src/koru/policy.py', 'policy_path', 1, 1, 1).
python_function('src/koru/policy.py', 'load_policy', 1, 9, 13).
python_function('src/koru/policy.py', '_check_git_commit_policy', 3, 3, 1).
python_function('src/koru/policy.py', '_check_git_push_policy', 3, 3, 1).
python_function('src/koru/policy.py', '_check_git_branch_create_policy', 3, 5, 1).
python_function('src/koru/policy.py', '_check_git_branch_switch_policy', 3, 6, 1).
python_function('src/koru/policy.py', '_check_git_tag_policy', 3, 3, 1).
python_function('src/koru/policy.py', '_check_destructive_shell_policy', 3, 5, 1).
python_function('src/koru/policy.py', 'policy_violations', 2, 3, 8).
python_function('src/koru/project_pipeline.py', 'project_pipeline_path', 1, 1, 1).
python_function('src/koru/project_pipeline.py', 'default_koru_project_pipeline_text', 0, 1, 0).
python_function('src/koru/project_pipeline.py', 'write_koru_project_pipeline_if_absent', 1, 2, 5).
python_function('src/koru/project_pipeline.py', 'load_koru_project_pipeline', 1, 4, 5).
python_function('src/koru/project_pipeline.py', 'build_project_pipeline_brief', 1, 9, 6).
python_function('src/koru/queue/human.py', 'default_human_prompt', 2, 5, 5).
python_function('src/koru/queue/koru_queue_argv.py', 'build_koru_queue_argv', 1, 5, 4).
python_function('src/koru/queue/local_manager.py', 'queue_local_manager_session', 1, 3, 5).
python_function('src/koru/queue/local_manager.py', 'queue_manager_start', 2, 5, 4).
python_function('src/koru/queue/local_manager.py', 'queue_manager_health', 1, 2, 0).
python_function('src/koru/queue/local_manager.py', 'queue_manager_decision_action', 1, 1, 1).
python_function('src/koru/queue/local_manager.py', 'queue_manager_stop_callback', 1, 2, 5).
python_function('src/koru/queue/local_manager.py', 'queue_manager_complete', 1, 3, 1).
python_function('src/koru/queue/locking.py', 'queue_lock_wanted', 0, 1, 3).
python_function('src/koru/queue/locking.py', 'queue_runner_lock', 1, 3, 5).
python_function('src/koru/queue/locking.py', 'claim_lease_seconds_str', 0, 2, 6).
python_function('src/koru/queue/locking.py', 'ticket_claim_or_error', 3, 4, 4).
python_function('src/koru/queue/loop.py', 'run_planfile_queue_loop', 0, 14, 7).
python_function('src/koru/queue/planfile_ticket_note.py', '_stderr_unknown_option', 2, 3, 0).
python_function('src/koru/queue/planfile_ticket_note.py', 'append_shell_evidence_note', 3, 5, 7).
python_function('src/koru/queue/runner.py', '_source_tool', 1, 4, 3).
python_function('src/koru/queue/runner.py', '_resolve_executor_kind', 3, 8, 3).
python_function('src/koru/queue/runner.py', '_handle_human_ticket', 8, 9, 6).
python_function('src/koru/queue/runner.py', '_resolve_ticket_action', 2, 4, 3).
python_function('src/koru/queue/runner.py', '_handle_dry_run', 3, 2, 4).
python_function('src/koru/queue/runner.py', '_claim_and_start', 4, 2, 2).
python_function('src/koru/queue/runner.py', '_execute_action', 7, 5, 6).
python_function('src/koru/queue/runner.py', '_append_shell_evidence', 4, 5, 6).
python_function('src/koru/queue/runner.py', '_finalize_ticket', 6, 4, 4).
python_function('src/koru/queue/runner.py', 'run_next_planfile_task', 0, 14, 15).
python_function('src/koru/queue/runners.py', '_planfile_env', 0, 1, 0).
python_function('src/koru/queue/runners.py', 'run_process', 2, 1, 2).
python_function('src/koru/queue/runners.py', 'run_shell_command', 2, 1, 1).
python_function('src/koru/queue/runners.py', 'run_api_request', 2, 8, 15).
python_function('src/koru/queue/runners.py', '_resolve_llm_endpoint_and_key', 1, 5, 3).
python_function('src/koru/queue/runners.py', '_build_llm_messages', 1, 2, 3).
python_function('src/koru/queue/runners.py', '_build_llm_request_body', 3, 3, 3).
python_function('src/koru/queue/runners.py', '_build_llm_headers', 2, 3, 1).
python_function('src/koru/queue/runners.py', '_parse_llm_response', 2, 9, 8).
python_function('src/koru/queue/runners.py', '_handle_llm_error', 2, 2, 6).
python_function('src/koru/queue/runners.py', 'run_llm_request', 2, 5, 14).
python_function('src/koru/queue/shell_evidence.py', '_tail_stream', 2, 3, 2).
python_function('src/koru/queue/shell_evidence.py', 'format_shell_run_note', 0, 7, 4).
python_function('src/koru/queue/ticket.py', 'parse_next_ticket', 1, 10, 5).
python_function('src/koru/queue/ticket.py', 'ticket_command', 1, 4, 1).
python_function('src/koru/queue/ticket.py', 'ticket_llm_request', 1, 8, 2).
python_function('src/koru/queue/ticket.py', 'ticket_api_request', 1, 8, 1).
python_function('src/koru/queue/ticket.py', '_has_planfile_cli_module', 0, 2, 1).
python_function('src/koru/queue/ticket.py', 'planfile_command', 3, 4, 5).
python_function('src/koru/queue/ticket.py', 'result_json', 1, 4, 2).
python_function('src/koru/queue_clean.py', '_planfile_base', 0, 4, 3).
python_function('src/koru/queue_clean.py', '_parse_age_days', 1, 8, 9).
python_function('src/koru/queue_clean.py', '_matched_rules', 1, 14, 11).
python_function('src/koru/queue_clean.py', '_cleanable_statuses', 0, 2, 1).
python_function('src/koru/queue_clean.py', '_maybe_skip_active_ticket', 3, 3, 3).
python_function('src/koru/queue_clean.py', '_candidate_from_ticket', 3, 6, 7).
python_function('src/koru/queue_clean.py', 'find_candidates', 1, 8, 7).
python_function('src/koru/queue_clean.py', '_build_close_note', 2, 1, 4).
python_function('src/koru/queue_clean.py', '_list_tickets', 2, 11, 7).
python_function('src/koru/queue_clean.py', '_close_ticket', 4, 5, 6).
python_function('src/koru/queue_clean.py', 'clean_queue', 1, 5, 6).
python_function('src/koru/queue_cli_helpers.py', 'queue_status_marker', 1, 1, 1).
python_function('src/koru/queue_cli_helpers.py', 'queue_loop_exit_code', 1, 2, 0).
python_function('src/koru/queue_cli_helpers.py', 'single_task_ticket_lists', 1, 7, 0).
python_function('src/koru/queue_cli_helpers.py', 'emit_queue_run_started', 1, 2, 2).
python_function('src/koru/queue_cli_helpers.py', 'open_queue_run_log', 1, 4, 2).
python_function('src/koru/queue_cli_helpers.py', '_queue_progress_callback', 2, 1, 4).
python_function('src/koru/queue_cli_helpers.py', '_emit_queue_completed', 1, 3, 1).
python_function('src/koru/queue_cli_helpers.py', 'run_queue_loop_mode', 2, 6, 12).
python_function('src/koru/queue_cli_helpers.py', '_single_task_summary', 1, 2, 2).
python_function('src/koru/queue_cli_helpers.py', 'run_queue_single_mode', 2, 9, 14).
python_function('src/koru/redup_integration.py', '_redup_module_command', 0, 1, 0).
python_function('src/koru/redup_integration.py', 'redup_scan_command', 1, 1, 2).
python_function('src/koru/redup_integration.py', 'redup_check_command', 1, 1, 2).
python_function('src/koru/redup_integration.py', 'redup_changed_scan_command', 1, 1, 2).
python_function('src/koru/redup_integration.py', 'redup_changed_scan_runner_command', 0, 1, 1).
python_function('src/koru/redup_integration.py', '_redup_scan_supports', 1, 1, 2).
python_function('src/koru/redup_integration.py', '_redup_json_scan_command', 1, 1, 2).
python_function('src/koru/redup_integration.py', '_env_bool', 1, 1, 3).
python_function('src/koru/redup_integration.py', '_write_skipped_changed_report', 1, 1, 5).
python_function('src/koru/redup_integration.py', 'run_changed_scan', 0, 3, 9).
python_function('src/koru/redup_integration.py', 'main', 1, 2, 7).
python_function('src/koru/refactor_planfile_handoff.py', 'render_planfile_refactor_handoff', 1, 6, 3).
python_function('src/koru/run_log.py', 'open_run_log', 1, 1, 4).
python_function('src/koru/run_log.py', 'open_run_log_eagerly', 1, 1, 2).
python_function('src/koru/run_log.py', '_iso', 1, 1, 2).
python_function('src/koru/runtime.py', 'planfile_dir', 1, 1, 1).
python_function('src/koru/runtime.py', 'runtime_dir', 1, 1, 1).
python_function('src/koru/runtime.py', 'runs_dir', 1, 1, 1).
python_function('src/koru/runtime.py', 'new_run_id', 1, 1, 3).
python_function('src/koru/runtime.py', 'ensure_runs_dir', 1, 2, 5).
python_function('src/koru/scan.py', 'scan_pytest_collect', 1, 13, 13).
python_function('src/koru/scan.py', '_load_koruignore_patterns', 1, 8, 7).
python_function('src/koru/scan.py', '_is_koruignored', 2, 10, 5).
python_function('src/koru/scan.py', 'scan_todo_markers', 1, 9, 12).
python_function('src/koru/scan.py', 'scan_missing_gates', 1, 5, 6).
python_function('src/koru/scan.py', 'scan_missing_tools', 1, 13, 12).
python_function('src/koru/scan.py', 'scan_gitignore_drift', 1, 4, 3).
python_function('src/koru/scan.py', '_scan_jscpd_report', 1, 11, 9).
python_function('src/koru/scan.py', '_find_analysis_file', 1, 4, 4).
python_function('src/koru/scan.py', '_parse_dup_suggestions', 2, 2, 5).
python_function('src/koru/scan.py', '_parse_god_module_suggestions', 2, 2, 5).
python_function('src/koru/scan.py', '_parse_high_cc_suggestions', 2, 3, 8).
python_function('src/koru/scan.py', '_parse_refactor_suggestions', 2, 7, 7).
python_function('src/koru/scan.py', '_scan_code2llm_analysis', 1, 3, 7).
python_function('src/koru/scan.py', '_scan_testql_export', 1, 5, 7).
python_function('src/koru/scan.py', '_scan_redup_filtered', 1, 7, 9).
python_function('src/koru/scan.py', '_scan_redup_changed', 1, 7, 9).
python_function('src/koru/scan.py', 'scan_semcod_quality_artifacts', 1, 1, 7).
python_function('src/koru/scan.py', 'collect_suggestions', 1, 3, 8).
python_function('src/koru/scan.py', '_existing_scan_titles', 1, 3, 9).
python_function('src/koru/scan.py', '_create_ticket', 2, 7, 3).
python_function('src/koru/scan.py', 'run_scan', 1, 10, 11).
python_function('src/koru/semcod_tools.py', '_read_pyproject', 1, 3, 3).
python_function('src/koru/semcod_tools.py', '_config_present', 2, 3, 2).
python_function('src/koru/semcod_tools.py', 'detect_semcod_tools', 1, 7, 8).
python_function('src/koru/stdio_events.py', 'iso_ts', 0, 1, 3).
python_function('src/koru/stdio_events.py', 'write_stdio_event', 1, 2, 4).
python_function('src/koru/stdio_events.py', 'default_stdio_format_from_env', 0, 3, 3).
python_function('src/koru/tasks.py', '_generate_ticket_id', 2, 3, 5).
python_function('src/koru/tasks.py', '_build_ticket_labels', 1, 4, 6).
python_function('src/koru/tasks.py', '_build_ticket_source', 3, 3, 3).
python_function('src/koru/tasks.py', '_build_ticket_inputs', 2, 4, 4).
python_function('src/koru/tasks.py', '_build_ticket_dict', 13, 2, 0).
python_function('src/koru/tasks.py', 'create_nl_task', 2, 12, 19).
python_function('src/koru/tasks.py', '_title_from_text', 1, 2, 3).
python_function('src/koru/tasks.py', '_read_config', 1, 4, 5).
python_function('src/koru/tasks.py', '_read_sprint', 1, 4, 6).
python_function('src/koru/tasks.py', '_write_yaml', 2, 1, 3).
python_function('src/koru/tools.py', 'default_registry_path', 0, 1, 2).
python_function('src/koru/tools.py', 'resolve_registry_path', 1, 4, 6).
python_function('src/koru/tools.py', 'load_tool_registry', 1, 11, 8).
python_function('src/koru/tools.py', '_first_token', 1, 2, 1).
python_function('src/koru/tools.py', '_extract_detect_config', 1, 11, 2).
python_function('src/koru/tools.py', '_check_commands_exist', 1, 3, 3).
python_function('src/koru/tools.py', '_check_markers_exist', 2, 3, 1).
python_function('src/koru/tools.py', '_check_env_vars_exist', 1, 3, 1).
python_function('src/koru/tools.py', '_build_detection_result', 5, 7, 1).
python_function('src/koru/tools.py', 'detect_tools', 2, 4, 8).
python_function('src/koru/tools.py', 'find_tool_entry', 2, 4, 4).
python_function('src/koru/tools.py', 'infer_adapter_kind', 1, 5, 2).
python_function('src/koru/tools.py', '_extract_tool_metadata', 1, 7, 2).
python_function('src/koru/tools.py', '_validate_adapter_kind', 2, 3, 2).
python_function('src/koru/tools.py', '_build_scaffold_prompt_lines', 3, 5, 2).
python_function('src/koru/tools.py', '_build_scaffold_labels', 2, 2, 1).
python_function('src/koru/tools.py', '_build_scaffold_inputs', 3, 2, 1).
python_function('src/koru/tools.py', 'build_tool_task_scaffold', 1, 2, 6).
python_function('src/koru/tools.py', 'render_tools_detect_text', 1, 10, 6).
python_function('src/koru/topology.py', 'topology_path', 1, 1, 1).
python_function('src/koru/topology.py', '_read_yaml', 1, 5, 4).
python_function('src/koru/topology.py', '_merge_components', 2, 12, 10).
python_function('src/koru/topology.py', '_merge_pipelines', 1, 9, 6).
python_function('src/koru/topology.py', 'load_topology', 1, 1, 8).
python_function('src/koru/topology.py', '_strip_to_persisted', 1, 8, 5).
python_function('src/koru/topology.py', 'save_topology', 2, 1, 6).
python_function('src/koru/topology.py', '_toggle', 4, 2, 6).
python_function('src/koru/topology.py', 'set_component_enabled', 3, 1, 1).
python_function('src/koru/topology.py', 'set_pipeline_enabled', 3, 1, 1).
python_function('src/koru/topology.py', 'is_component_enabled', 2, 3, 4).
python_function('src/koru/topology.py', 'is_pipeline_enabled', 2, 3, 4).
python_function('src/koru/topology.py', 'enabled_components_for_pipeline', 2, 9, 4).
python_function('src/koru/topology.py', 'default_component_ids', 0, 1, 2).
python_function('src/koru/topology.py', 'default_pipeline_ids', 0, 1, 2).
python_function('src/koru/topology_cli.py', 'render_topology_text', 1, 2, 5).
python_function('src/koru/topology_cli.py', '_render_component_rows', 1, 7, 3).
python_function('src/koru/topology_cli.py', '_render_pipeline_rows', 1, 8, 4).
python_function('src/koru/topology_cli.py', 'apply_topology_mutations', 2, 4, 2).
python_function('src/koru/utils/subprocess_runner.py', 'default_subprocess_runner', 2, 1, 2).
python_function('src/koru/utils/subprocess_runner.py', 'resolve_planfile_subpath', 1, 1, 2).
python_function('src/koru/utils/subprocess_runner.py', 'get_python_cmd', 1, 3, 3).
python_function('src/koru/watch.py', '_format_connected_event', 1, 1, 0).
python_function('src/koru/watch.py', '_format_management_event', 1, 9, 4).
python_function('src/koru/watch.py', '_format_ticket_event', 2, 9, 5).
python_function('src/koru/watch.py', 'format_queue_event', 1, 5, 5).
python_function('src/koru/watch.py', '_default_connect', 1, 2, 2).
python_function('src/koru/watch.py', 'watch_planfile_events', 1, 7, 6).
python_function('src/koru/wup_testql_compat.py', '_normalize_timeout', 1, 4, 6).
python_function('src/koru/wup_testql_compat.py', '_normalize_args', 1, 5, 8).
python_function('src/koru/wup_testql_compat.py', '_real_testql', 0, 5, 7).
python_function('src/koru/wup_testql_compat.py', 'main', 1, 2, 4).
python_function('src/koruapi/cli.py', '_build_parser', 0, 2, 5).
python_function('src/koruapi/cli.py', '_parse_body', 1, 3, 4).
python_function('src/koruapi/cli.py', 'main', 1, 11, 15).
python_function('src/koruapi/dashboard.py', '_env_truthy', 1, 1, 3).
python_function('src/koruapi/dashboard.py', 'build_serve_parser', 0, 1, 4).
python_function('src/koruapi/dashboard.py', 'dashboard_main', 1, 5, 9).
python_function('src/koruapi/dashboard_serve.py', '_list_tickets', 1, 9, 4).
python_function('src/koruapi/dashboard_serve.py', '_bulk_waiting_input_action', 1, 13, 6).
python_function('src/koruapi/dashboard_serve.py', '_address_in_use', 1, 4, 3).
python_function('src/koruapi/dashboard_serve.py', '_listener_pids_for_tcp_port', 1, 7, 7).
python_function('src/koruapi/dashboard_serve.py', '_cmdline_suggests_koru_serve_from_bytes', 1, 3, 5).
python_function('src/koruapi/dashboard_serve.py', '_cmdline_suggests_koru_serve', 1, 3, 3).
python_function('src/koruapi/dashboard_serve.py', '_try_stop_prior_koru_serve_listener', 2, 12, 10).
python_function('src/koruapi/dashboard_serve.py', 'serve_endpoint_path', 1, 1, 1).
python_function('src/koruapi/dashboard_serve.py', 'read_serve_endpoint', 1, 4, 5).
python_function('src/koruapi/dashboard_serve.py', '_build_handler', 1, 1, 31).
python_function('src/koruapi/dashboard_serve.py', 'build_server', 1, 1, 2).
python_function('src/koruapi/dashboard_serve.py', 'write_serve_endpoint_file', 1, 1, 5).
python_function('src/koruapi/dashboard_serve.py', 'bind_serve_server', 1, 11, 7).
python_function('src/koruapi/dashboard_serve.py', 'serve', 1, 7, 11).
python_function('src/koruapi/dashboard_serve.py', 'start_serve_background', 1, 4, 11).
python_function('src/koruapi/integrations.py', 'list_integrations', 0, 4, 2).
python_function('src/koruapi/integrations.py', 'get_integration', 1, 1, 1).
python_function('src/koruapi/invoke.py', 'invoke_integration', 1, 4, 5).
python_function('src/koruapi/invoke_handlers.py', '_handle_context_build', 3, 1, 2).
python_function('src/koruapi/invoke_handlers.py', '_handle_doctor_run', 3, 1, 2).
python_function('src/koruapi/invoke_handlers.py', '_handle_scan_apply', 3, 1, 4).
python_function('src/koruapi/invoke_handlers.py', '_handle_queue_loop', 3, 2, 5).
python_function('src/koruapi/invoke_handlers.py', '_handle_autopilot_status', 3, 2, 3).
python_function('src/koruapi/invoke_handlers.py', '_handle_autopilot_drive', 3, 5, 8).
python_function('src/koruapi/invoke_handlers.py', '_handle_dsl_to_library', 3, 3, 3).
python_function('src/koruapi/invoke_handlers.py', '_handle_dsl_to_dsl', 3, 2, 3).
python_function('src/koruapi/invoke_handlers.py', '_handle_dsl_roundtrip', 3, 3, 4).
python_function('src/koruapi/invoke_handlers.py', '_handle_topology_read', 3, 1, 1).
python_function('src/koruapi/invoke_handlers.py', '_handle_gate_regix', 3, 3, 5).
python_function('src/koruapi/invoke_handlers.py', '_handle_planfile_tickets', 3, 5, 5).
python_function('src/koruapi/invoke_handlers.py', '_handle_mcp_list_tickets', 3, 1, 2).
python_function('src/koruapi/invoke_handlers.py', '_handle_mcp_run_ticket', 3, 1, 2).
python_function('src/koruapi/invoke_handlers.py', '_handle_mcp_quality_gates', 3, 1, 2).
python_function('src/koruapi/local.py', 'build_local_parser', 0, 1, 2).
python_function('src/koruapi/local.py', 'local_main', 1, 6, 9).
python_function('src/koruapi/mcp.py', 'mcp_main', 1, 2, 2).
python_function('src/koruapi/mcp_server.py', '_get_job_store_path', 1, 2, 1).
python_function('src/koruapi/mcp_server.py', '_load_jobs', 1, 3, 4).
python_function('src/koruapi/mcp_server.py', '_save_jobs', 2, 2, 4).
python_function('src/koruapi/mcp_server.py', '_get_process_memory_mb', 1, 3, 2).
python_function('src/koruapi/mcp_server.py', '_monitor_subprocess_oom', 4, 8, 5).
python_function('src/koruapi/mcp_server.py', '_get_python_cmd', 0, 1, 1).
python_function('src/koruapi/mcp_server.py', '_run_planfile_cli', 1, 1, 4).
python_function('src/koruapi/mcp_server.py', '_parse_tickets_json', 1, 8, 3).
python_function('src/koruapi/mcp_server.py', '_tickets_for_status_filter', 2, 11, 1).
python_function('src/koruapi/mcp_server.py', '_serialize_mcp_ticket', 1, 3, 1).
python_function('src/koruapi/mcp_server.py', 'tool_list_tickets', 1, 3, 7).
python_function('src/koruapi/mcp_server.py', '_create_job', 3, 1, 4).
python_function('src/koruapi/mcp_server.py', '_update_job', 2, 1, 2).
python_function('src/koruapi/mcp_server.py', '_collect_process_logs', 1, 3, 3).
python_function('src/koruapi/mcp_server.py', 'tool_run_ticket', 1, 14, 17).
python_function('src/koruapi/mcp_server.py', 'tool_job_status', 1, 3, 1).
python_function('src/koruapi/mcp_server.py', '_gate_commands', 1, 1, 2).
python_function('src/koruapi/mcp_server.py', '_detect_enabled_gates', 2, 5, 3).
python_function('src/koruapi/mcp_server.py', '_resolve_gates', 3, 4, 3).
python_function('src/koruapi/mcp_server.py', '_run_single_gate', 6, 12, 9).
python_function('src/koruapi/mcp_server.py', 'tool_run_quality_gates', 1, 6, 7).
python_function('src/koruapi/mcp_server.py', '_find_ticket', 2, 3, 1).
python_function('src/koruapi/mcp_server.py', '_build_edit_context', 2, 3, 4).
python_function('src/koruapi/mcp_server.py', 'tool_propose_edits', 1, 14, 8).
python_function('src/koruapi/mcp_server.py', '_jsonrpc_response', 2, 1, 0).
python_function('src/koruapi/mcp_server.py', '_jsonrpc_error', 4, 2, 0).
python_function('src/koruapi/mcp_server.py', '_handle_initialize', 1, 1, 0).
python_function('src/koruapi/mcp_server.py', '_handle_tools_list', 1, 1, 0).
python_function('src/koruapi/mcp_server.py', '_handle_tools_call', 1, 4, 4).
python_function('src/koruapi/mcp_server.py', 'handle_message', 1, 6, 5).
python_function('src/koruapi/mcp_server.py', 'run_stdio', 0, 5, 6).
python_function('src/koruapi/mcp_server.py', '_write', 1, 1, 3).
python_function('src/koruapi/mcp_server.py', '_log', 1, 1, 1).
python_function('src/koruapi/mcp_server.py', 'mcp_serve_main', 1, 2, 9).
python_function('src/koruapi/openapi.py', 'build_openapi_document', 0, 2, 1).
python_function('src/koruapi/runtime_insights.py', '_run_ps', 0, 9, 9).
python_function('src/koruapi/runtime_insights.py', '_looks_project_related', 2, 1, 2).
python_function('src/koruapi/runtime_insights.py', '_classify_process', 2, 5, 5).
python_function('src/koruapi/runtime_insights.py', '_active_tools', 2, 8, 10).
python_function('src/koruapi/runtime_insights.py', '_top_processes', 2, 2, 8).
python_function('src/koruapi/runtime_insights.py', 'collect_runtime_insights', 1, 4, 9).
python_function('src/koruapi/server.py', '_json_response', 3, 1, 8).
python_function('src/koruapi/server.py', '_read_json_body', 1, 5, 7).
python_function('src/koruapi/server.py', '_parse_invoke_request', 2, 9, 6).
python_function('src/koruapi/server.py', '_handle_invoke_post', 1, 5, 6).
python_function('src/koruapi/server.py', 'serve', 0, 2, 4).
python_function('src/koruapi/topology_post.py', 'apply_topology_post_update', 2, 14, 9).
python_function('src/korudsl/cli.py', '_build_parser', 0, 1, 4).
python_function('src/korudsl/cli.py', '_read_input', 1, 2, 2).
python_function('src/korudsl/cli.py', 'main', 1, 11, 11).
python_function('src/korudsl/library.py', 'ensure_library_structure', 1, 2, 2).
python_function('src/korudsl/library.py', '_start_goal', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_func', 3, 3, 1).
python_function('src/korudsl/library.py', '_handle_set', 2, 2, 1).
python_function('src/korudsl/library.py', '_handle_wait', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_get', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_save', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_if', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_error', 2, 2, 2).
python_function('src/korudsl/library.py', '_handle_correct', 2, 2, 2).
python_function('src/korudsl/library.py', '_apply_prefixed_line', 3, 4, 3).
python_function('src/korudsl/library.py', 'normalize_dsl_to_library', 2, 7, 6).
python_function('src/korudsl/library.py', 'convert_goals_json_to_library', 2, 9, 4).
python_function('src/korudsl/library.py', '_emit_step', 1, 8, 4).
python_function('src/korudsl/library.py', '_emit_objective', 1, 5, 3).
python_function('src/korudsl/library.py', '_emit_functions', 1, 4, 6).
python_function('src/korudsl/library.py', '_emit_goal', 1, 9, 7).
python_function('src/korudsl/library.py', '_emit_goals', 1, 3, 4).
python_function('src/korudsl/library.py', 'library_to_dsl', 1, 4, 6).
python_function('src/korudsl/transform.py', 'library_from_any', 1, 12, 9).
python_function('src/korudsl/transform.py', 'library_to_any', 1, 2, 3).
python_function('src/korudsl/transform.py', 'dsl_roundtrip_report', 1, 1, 4).
python_function('src/korudsl/transform.py', 'load_path', 1, 3, 2).
python_function('src/koruide/audit.py', 'default_log_path', 0, 2, 3).
python_function('src/koruide/audit.py', '_isoformat_utc', 1, 2, 4).
python_function('src/koruide/client.py', 'build_client', 0, 1, 1).
python_function('src/koruide/config.py', 'default_config_path', 0, 1, 1).
python_function('src/koruide/config.py', '_merge_submit_keys', 1, 7, 3).
python_function('src/koruide/config.py', 'load_config', 1, 4, 8).
python_function('src/koruide/config.py', 'cached_config', 0, 1, 2).
python_function('src/koruide/config.py', 'clear_config_cache', 0, 1, 1).
python_function('src/koruide/daemon.py', '_daemon_package_version', 0, 2, 1).
python_function('src/koruide/daemon.py', '_env_truthy', 1, 1, 3).
python_function('src/koruide/daemon.py', '_prefer_keyboard_drive', 0, 2, 1).
python_function('src/koruide/daemon.py', '_plugin_rejection_log_interval_seconds', 0, 3, 4).
python_function('src/koruide/daemon.py', '_load_context_module', 0, 1, 1).
python_function('src/koruide/daemon.py', '_default_handoff', 1, 1, 3).
python_function('src/koruide/daemon.py', '_peer_uid', 1, 3, 2).
python_function('src/koruide/host_setup.py', '_package_manager_hint', 0, 5, 1).
python_function('src/koruide/host_setup.py', '_human_followups', 2, 14, 2).
python_function('src/koruide/host_setup.py', 'build_setup_host_report', 0, 7, 10).
python_function('src/koruide/host_setup.py', '_try_apt_install', 1, 5, 4).
python_function('src/koruide/host_setup.py', 'run_host_setup', 0, 6, 7).
python_function('src/koruide/host_setup.py', '_print_setup_host_header', 1, 2, 2).
python_function('src/koruide/host_setup.py', '_print_setup_host_backends', 1, 3, 2).
python_function('src/koruide/host_setup.py', '_print_setup_host_ides', 1, 4, 3).
python_function('src/koruide/host_setup.py', '_print_setup_host_apt_section', 1, 2, 2).
python_function('src/koruide/host_setup.py', '_print_setup_host_human_followups', 1, 3, 2).
python_function('src/koruide/host_setup.py', '_print_setup_host_install_details', 1, 6, 2).
python_function('src/koruide/host_setup.py', '_print_text_report', 1, 2, 1).
python_function('src/koruide/ide.py', 'normalize_ide_id', 1, 6, 9).
python_function('src/koruide/ide.py', 'supported_autopilot_ide_ids', 0, 1, 0).
python_function('src/koruide/ide.py', 'autopilot_ide_choices', 0, 1, 0).
python_function('src/koruide/ide.py', 'vscode_extension_plugin_ide_ids', 0, 1, 0).
python_function('src/koruide/ide.py', 'supports_vscode_extension_plugin', 1, 2, 2).
python_function('src/koruide/ide.py', '_iter_proc_pids', 0, 4, 6).
python_function('src/koruide/ide.py', '_read_comm', 1, 2, 3).
python_function('src/koruide/ide.py', '_read_cmdline', 1, 2, 5).
python_function('src/koruide/ide.py', '_read_exe', 1, 2, 1).
python_function('src/koruide/ide.py', '_matches', 3, 7, 4).
python_function('src/koruide/ide.py', '_score_comm_name', 2, 2, 2).
python_function('src/koruide/ide.py', '_score_windsurf_exe_path', 1, 5, 1).
python_function('src/koruide/ide.py', '_score_primary_exe_path', 2, 2, 2).
python_function('src/koruide/ide.py', '_score_exe_path', 2, 3, 3).
python_function('src/koruide/ide.py', '_score_cmdline_flags', 1, 4, 1).
python_function('src/koruide/ide.py', '_candidate_score', 5, 1, 3).
python_function('src/koruide/ide.py', 'detect_running_ides', 0, 13, 10).
python_function('src/koruide/ide.py', '_active_window_pid_x11', 0, 7, 6).
python_function('src/koruide/ide.py', '_ide_id_from_process', 1, 5, 4).
python_function('src/koruide/ide.py', 'detect_focused_ide_id', 0, 3, 2).
python_function('src/koruide/ide.py', '_vscode_family_env_present', 0, 3, 3).
python_function('src/koruide/ide.py', '_vscode_family_flavor_from_env', 0, 9, 4).
python_function('src/koruide/ide.py', '_cursor_terminal_env_hint', 1, 3, 2).
python_function('src/koruide/ide.py', '_windsurf_primary_terminal_env_hint', 1, 4, 4).
python_function('src/koruide/ide.py', '_vscode_family_terminal_hint', 1, 3, 2).
python_function('src/koruide/ide.py', '_known_terminal_ide_hint', 2, 3, 0).
python_function('src/koruide/ide.py', '_legacy_windsurf_terminal_env_hint', 1, 3, 2).
python_function('src/koruide/ide.py', '_terminal_ide_from_env', 0, 7, 11).
python_function('src/koruide/ide.py', '_terminal_ide_from_parent_chain', 1, 11, 9).
python_function('src/koruide/ide.py', 'detect_terminal_host_ide_id', 0, 3, 3).
python_function('src/koruide/ide.py', 'focused_ide', 1, 6, 1).
python_function('src/koruide/ide.py', 'pick_target', 1, 13, 4).
python_function('src/koruide/ide.py', 'is_linux', 0, 2, 2).
python_function('src/koruide/ide.py', 'detect_running_ides_cached', 0, 4, 2).
python_function('src/koruide/ide.py', 'clear_detect_cache', 0, 1, 0).
python_function('src/koruide/ide.py', '_has_os_injector_profile', 2, 2, 2).
python_function('src/koruide/ide.py', '_auto_profile_candidate_ids', 1, 3, 6).
python_function('src/koruide/ide.py', '_resolve_explicit_drive_target', 2, 6, 1).
python_function('src/koruide/ide.py', '_resolve_auto_drive_target', 2, 13, 4).
python_function('src/koruide/ide.py', 'resolve_drive_target', 2, 12, 7).
python_function('src/koruide/injector.py', '_submit_key_for', 1, 1, 2).
python_function('src/koruide/injector.py', '_which', 1, 1, 1).
python_function('src/koruide/injector.py', '_session_type', 0, 4, 2).
python_function('src/koruide/injector.py', '_forced_injector_backend', 0, 2, 3).
python_function('src/koruide/injector.py', '_ydotool_enter_keycode', 0, 2, 3).
python_function('src/koruide/injector.py', '_ydotool_submit_mode', 0, 3, 3).
python_function('src/koruide/injector.py', '_ydotool_ctrl_keycode', 0, 2, 3).
python_function('src/koruide/injector.py', '_extra_enter_count', 0, 3, 4).
python_function('src/koruide/injector.py', '_default_runner', 2, 2, 2).
python_function('src/koruide/os_injector.py', 'default_config_path', 0, 1, 1).
python_function('src/koruide/os_injector.py', 'iter_config_paths', 0, 4, 7).
python_function('src/koruide/os_injector.py', 'os_injector_env_disabled', 0, 1, 3).
python_function('src/koruide/os_injector.py', 'os_injector_env_forced', 0, 1, 3).
python_function('src/koruide/os_injector.py', 'dry_run_from_env', 0, 1, 3).
python_function('src/koruide/os_injector.py', 'focus_mode_from_env', 0, 2, 3).
python_function('src/koruide/os_injector.py', 'input_mode_from_env', 0, 2, 3).
python_function('src/koruide/os_injector.py', '_is_wayland_session', 0, 1, 3).
python_function('src/koruide/os_injector.py', '_cmd_timeout_seconds', 0, 3, 4).
python_function('src/koruide/os_injector.py', '_post_focus_delay_seconds', 0, 3, 5).
python_function('src/koruide/os_injector.py', 'try_load_profile', 1, 4, 3).
python_function('src/koruide/os_injector.py', '_read_json', 1, 4, 5).
python_function('src/koruide/os_injector.py', 'load_profile', 1, 5, 8).
python_function('src/koruide/os_injector.py', 'save_profile', 1, 3, 7).
python_function('src/koruide/os_injector.py', 'profile_from_mouse', 1, 1, 1).
python_function('src/koruide/os_injector.py', 'capture_mouse_xy', 0, 6, 6).
python_function('src/koruide/os_injector.py', 'capture_from_xdotool', 0, 1, 1).
python_function('src/koruide/os_injector.py', '_run_cmd', 1, 5, 5).
python_function('src/koruide/os_injector.py', '_xdotool', 1, 1, 1).
python_function('src/koruide/os_injector.py', '_tool_pid', 1, 4, 2).
python_function('src/koruide/os_injector.py', '_clipboard_backend', 0, 3, 1).
python_function('src/koruide/os_injector.py', '_set_clipboard', 1, 3, 4).
python_function('src/koruide/os_injector.py', 'inject_with_profile', 0, 15, 14).
python_function('src/koruide/os_injector.py', 'try_drive_with_profile', 0, 10, 7).
python_function('src/koruide/plugin_installer.py', '_valid_ide', 1, 2, 2).
python_function('src/koruide/plugin_installer.py', '_ide_from_terminal_env', 0, 1, 1).
python_function('src/koruide/plugin_installer.py', '_terminal_vscode_flavor', 0, 5, 3).
python_function('src/koruide/plugin_installer.py', '_repo_root', 0, 4, 4).
python_function('src/koruide/plugin_installer.py', '_plugin_package_version', 1, 4, 5).
python_function('src/koruide/plugin_installer.py', '_versioned_vsix_candidates', 1, 2, 1).
python_function('src/koruide/plugin_installer.py', '_running_vscode_flavor', 0, 7, 4).
python_function('src/koruide/plugin_installer.py', '_vscode_flavor', 0, 2, 2).
python_function('src/koruide/plugin_installer.py', 'resolve_target_ide', 1, 10, 6).
python_function('src/koruide/plugin_installer.py', 'resolve_extension_vsix', 0, 11, 14).
python_function('src/koruide/plugin_installer.py', '_resolve_ide_command', 1, 3, 2).
python_function('src/koruide/plugin_installer.py', '_settings_path_for_ide', 1, 2, 4).
python_function('src/koruide/plugin_installer.py', '_configure_socket_path', 2, 8, 12).
python_function('src/koruide/plugin_installer.py', '_run', 1, 1, 1).
python_function('src/koruide/plugin_installer.py', '_env_reassert_extension_install', 0, 1, 3).
python_function('src/koruide/plugin_installer.py', '_extension_is_installed', 2, 4, 4).
python_function('src/koruide/plugin_installer.py', '_parse_extension_version', 1, 4, 5).
python_function('src/koruide/plugin_installer.py', 'installed_extension_version_for_ide', 1, 6, 4).
python_function('src/koruide/plugin_installer.py', '_reassert_extension_extra', 1, 9, 5).
python_function('src/koruide/plugin_installer.py', '_result_already_installed', 2, 2, 3).
python_function('src/koruide/plugin_installer.py', '_install_extension_vsix', 3, 10, 4).
python_function('src/koruide/plugin_installer.py', 'install_plugin_for_ide', 0, 9, 10).
python_function('src/koruide/plugin_installer.py', 'format_plugin_install_result', 1, 2, 1).
python_function('src/koruide/protocol.py', '_filter_extras', 2, 6, 3).
python_function('src/koruide/protocol.py', 'decode', 1, 12, 9).
python_function('src/koruide/protocol.py', 'hello', 0, 1, 1).
python_function('src/koruide/protocol.py', 'chat_send', 1, 1, 1).
python_function('src/koruide/protocol.py', 'drive', 1, 1, 1).
python_function('src/koruide/protocol.py', 'ack', 1, 2, 2).
python_function('src/koruide/protocol.py', 'error', 2, 1, 1).
python_function('src/koruide/protocol.py', 'session_started', 0, 1, 1).
python_function('src/koruide/protocol.py', 'session_ended', 0, 1, 1).
python_function('src/koruide/protocol.py', 'message_sent', 0, 1, 1).
python_function('src/koruide/protocol.py', 'message_received', 0, 1, 1).
python_function('src/koruide/protocol.py', 'status_error', 0, 1, 1).
python_function('src/koruide/socket.py', '_autopilot_socket_basename', 0, 7, 6).
python_function('src/koruide/socket.py', 'default_socket_path', 0, 4, 10).
python_function('src/koruide/utils.py', 'resolve_xdg_path', 1, 2, 3).
python_function('tests/test_activity_log.py', 'test_activity_flushes_with_timestamp', 1, 5, 4).
python_function('tests/test_activity_log.py', 'test_activity_disabled', 2, 2, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_plugin_socket_backend_forwards_send_chat_to_drive', 0, 2, 5).
python_function('tests/test_agent_backend_runtime.py', 'test_mcp_tool_backend_returns_ok_marker', 0, 5, 4).
python_function('tests/test_agent_backend_runtime.py', 'test_mcp_tool_backend_no_server_field', 0, 3, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_noop_backend_returns_ok_with_reason', 0, 4, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_resolves_plugin_socket_with_client', 0, 3, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_plugin_socket_requires_client', 0, 1, 2).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_resolves_mcp_tool', 0, 3, 2).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_resolves_mcp_tool_without_server', 0, 3, 2).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_resolves_none_to_noop', 0, 4, 2).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_resolves_os_injector_from_env', 1, 3, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_os_injector_requires_profile_env', 1, 1, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_normalizes_case_and_whitespace', 0, 2, 3).
python_function('tests/test_agent_backend_runtime.py', 'test_factory_rejects_unknown_backend_id', 0, 1, 2).
python_function('tests/test_agent_backend_runtime.py', 'test_all_backends_implement_send_chat', 2, 3, 6).
python_function('tests/test_agent_backends.py', 'test_list_contains_core_backends', 0, 3, 1).
python_function('tests/test_agent_backends.py', 'test_iter_matches_list_count', 0, 2, 3).
python_function('tests/test_agent_backends.py', 'test_get_profile_returns_none_for_unknown', 0, 2, 1).
python_function('tests/test_agent_backends.py', 'test_mcp_profile_is_tools_only', 0, 4, 1).
python_function('tests/test_agent_backends.py', 'test_backend_aliases_normalize_to_profiles', 0, 3, 2).
python_function('tests/test_agent_backends.py', 'test_load_agent_integration_config_from_koru_yaml', 1, 7, 3).
python_function('tests/test_agent_backends.py', 'test_validate_agent_integration_config_reports_unknown_backend', 1, 3, 3).
python_function('tests/test_agent_backends_cli.py', 'test_list_text_prints_ids', 1, 3, 2).
python_function('tests/test_agent_backends_cli.py', 'test_list_json_is_array', 1, 5, 4).
python_function('tests/test_agent_backends_cli.py', 'test_show_one_json', 1, 4, 3).
python_function('tests/test_agent_backends_cli.py', 'test_unknown_id_errors', 1, 3, 2).
python_function('tests/test_agent_cli.py', '_run_main', 0, 1, 4).
python_function('tests/test_agent_cli.py', 'test_agent_list_json_includes_ready_summary', 0, 11, 10).
python_function('tests/test_agent_cli.py', 'test_agent_env_exports_cursor_lane', 0, 5, 4).
python_function('tests/test_autoloop_cli.py', 'test_packaged_autoloop_script_matches_repo_script', 0, 2, 4).
python_function('tests/test_autoloop_cli.py', 'test_autoloop_print_script', 1, 3, 2).
python_function('tests/test_autoloop_cli.py', 'test_autoloop_runs_packaged_script_with_env_assignments', 1, 8, 5).
python_function('tests/test_autonomous.py', 'test_effective_flags_matrix', 0, 5, 2).
python_function('tests/test_autonomous.py', 'test_scan_after_idle_queue_runs_scan_when_queue_idle', 2, 3, 7).
python_function('tests/test_autonomous.py', 'test_scan_after_idle_min_interval_skips_second_scan', 2, 4, 8).
python_function('tests/test_autonomous.py', 'test_idle_streak_skip_increments_telemetry', 2, 5, 9).
python_function('tests/test_autonomous.py', 'test_ticket_sources_env_overrides_cli_queue_to_scan', 2, 3, 8).
python_function('tests/test_autonomous.py', 'test_ticket_sources_env_invalid_keeps_cli_queue', 3, 4, 8).
python_function('tests/test_autonomous.py', 'test_autonomous_environ_doctor_probe_invalid_ticket_sources', 2, 3, 2).
python_function('tests/test_autonomous.py', 'test_autonomous_environ_doctor_probe_pass_summary', 2, 4, 3).
python_function('tests/test_autonomous.py', 'test_looks_like_autonomous_matches_koru_cli_auto', 0, 2, 1).
python_function('tests/test_autonomous.py', 'test_looks_like_autonomous_matches_koru_autonomous_regex', 0, 2, 1).
python_function('tests/test_autonomous.py', 'test_auto_main_argv_injects_replace_existing', 1, 5, 6).
python_function('tests/test_autonomous.py', 'test_auto_invocation_uses_full_autonomous_defaults', 2, 12, 4).
python_function('tests/test_autonomous.py', 'test_auto_invocation_can_enable_adaptive_pipeline', 2, 3, 4).
python_function('tests/test_autonomous.py', 'test_auto_pipeline_profiles_escalate_when_queue_stays_idle', 0, 15, 7).
python_function('tests/test_autonomous.py', 'test_effective_cycle_autopilot_skips_required_plugin_when_missing', 1, 3, 6).
python_function('tests/test_autonomous.py', 'test_effective_cycle_autopilot_allows_non_plugin_required_ide', 0, 2, 1).
python_function('tests/test_autonomous.py', 'test_effective_cycle_scan_skips_after_waiting_input', 1, 3, 6).
python_function('tests/test_autonomous.py', 'test_effective_cycle_scan_waiting_override', 1, 2, 3).
python_function('tests/test_autonomous.py', 'test_build_queue_command_omits_unsupported_all_queues_flag', 0, 3, 1).
python_function('tests/test_autonomous.py', 'test_stop_prior_autonomous_for_auto_start_terminates', 2, 4, 5).
python_function('tests/test_autonomous.py', 'test_guard_existing_autonomous_noninteractive_blocks_duplicate', 2, 2, 5).
python_function('tests/test_autonomous.py', 'test_guard_existing_autonomous_replace_existing_terminates', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_guard_existing_autonomous_replace_existing_terminates_stale_wup', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_guard_existing_autonomous_interactive_decline_blocks_duplicate', 2, 2, 5).
python_function('tests/test_autonomous.py', 'test_autonomous_jsonl_keyboard_interrupt_emits_reason', 2, 8, 13).
python_function('tests/test_autonomous.py', 'test_queue_loop_result_summary_includes_waiting_ticket', 0, 3, 2).
python_function('tests/test_autonomous.py', 'test_queue_loop_waiting_ticket_label_helper', 0, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_env_overrides_cli', 1, 3, 3).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_ignores_bad_env', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_auto_env_does_not_override_cli', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_headless_forces_auto', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_headless_allow_autopilot_honors_env', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_koru_ide_mode_headless', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_ssh_without_display_headless', 1, 2, 4).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_ssh_with_display_uses_cli', 1, 2, 4).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_os_environ_autopilot_ide', 1, 2, 3).
python_function('tests/test_autonomous.py', 'test_resolve_autopilot_ide_headless_allow_yes', 1, 2, 2).
python_function('tests/test_autonomous.py', '_isolate_integrated_terminal_env', 1, 2, 1).
python_function('tests/test_autonomous.py', 'test_apply_agent_lane_environ_auto_cursor', 2, 3, 5).
python_function('tests/test_autonomous.py', 'test_apply_agent_lane_environ_auto_prefers_vscode_terminal', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_apply_agent_lane_environ_auto_prefers_vscodium_terminal', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_apply_agent_lane_environ_none_is_noop', 2, 3, 2).
python_function('tests/test_autonomous.py', 'test_autonomous_main_prepends_up_for_flags', 2, 2, 4).
python_function('tests/test_autonomous.py', 'test_up_single_cycle_queue_only_no_autopilot', 2, 4, 6).
python_function('tests/test_autonomous.py', 'test_safe_up_uses_queue_diagnostics_without_autopilot', 2, 7, 7).
python_function('tests/test_autonomous.py', 'test_up_single_cycle_all_sources_runs_scan', 2, 2, 5).
python_function('tests/test_autonomous.py', 'test_up_auto_installs_plugin_before_autopilot_loop', 2, 4, 7).
python_function('tests/test_autonomous.py', 'test_setup_autopilot_plugin_unsupported_skips_wait', 2, 3, 6).
python_function('tests/test_autonomous.py', 'test_status_has_autopilot_plugin_matches_specific_ide', 1, 3, 2).
python_function('tests/test_autonomous.py', 'test_status_has_autopilot_plugin_rejects_stale_plugin_when_strict', 1, 4, 3).
python_function('tests/test_autonomous.py', 'test_autonomous_defaults_to_strict_plugin_policy', 1, 4, 7).
python_function('tests/test_autonomous.py', 'test_autonomous_respects_explicit_plugin_version_policy', 1, 4, 6).
python_function('tests/test_autonomous.py', 'test_wait_for_autopilot_plugin_polls_until_connected', 1, 3, 7).
python_function('tests/test_autonomous.py', 'test_start_or_reuse_daemon_reuses_current_version', 2, 6, 8).
python_function('tests/test_autonomous.py', 'test_start_or_reuse_daemon_restarts_daemon_without_version', 2, 8, 6).
python_function('tests/test_autonomous.py', 'test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message', 2, 6, 7).
python_function('tests/test_autonomous.py', 'test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list', 3, 6, 6).
python_function('tests/test_autonomous.py', 'test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping', 2, 7, 7).
python_function('tests/test_autonomous.py', 'test_run_cycle_drives_llm_ready_waiting_ticket_without_stagnation_skip', 2, 5, 8).
python_function('tests/test_autonomous.py', 'test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure', 2, 6, 7).
python_function('tests/test_autonomous.py', 'test_run_cycle_plugin_required_failure_skips_os_injector_fallback', 2, 7, 8).
python_function('tests/test_autonomous.py', 'test_run_cycle_autopilot_focus_error_retry_loop_retries_and_warns', 3, 4, 7).
python_function('tests/test_autonomous.py', 'test_run_cycle_does_not_retry_missing_plugin_as_focus_error', 3, 4, 6).
python_function('tests/test_autonomous.py', 'test_run_cycle_skips_drive_when_required_plugin_missing', 3, 4, 6).
python_function('tests/test_autonomous.py', 'test_run_cycle_visible_typing_does_not_require_plugin', 2, 3, 6).
python_function('tests/test_autonomous.py', 'test_run_cycle_jetbrains_does_not_require_plugin_by_default', 2, 3, 6).
python_function('tests/test_autonomous.py', '_fast_autonomous_up', 1, 1, 2).
python_function('tests/test_autonomous.py', 'test_up_keeps_running_on_waiting_input_by_default', 2, 3, 4).
python_function('tests/test_autonomous.py', 'test_up_stops_on_waiting_input_when_flag_set', 2, 3, 5).
python_function('tests/test_autonomous.py', 'test_up_restarts_autopilot_when_socket_disappears_between_cycles', 2, 3, 9).
python_function('tests/test_autonomous.py', 'test_compute_backoff_sleep_caps_stagnation', 0, 5, 1).
python_function('tests/test_autonomous.py', 'test_env_apply_autoloop_defaults_enables_full_diagnostics', 1, 4, 3).
python_function('tests/test_autonomous.py', 'test_run_idle_diagnostics_profile_off_message', 2, 4, 2).
python_function('tests/test_autonomous.py', 'test_run_idle_diagnostics_creates_deduped_ticket', 2, 5, 4).
python_function('tests/test_autonomous.py', 'test_wup_watch_command_uses_testql_mode', 1, 7, 5).
python_function('tests/test_autonomous.py', 'test_wup_watch_command_prefers_project_venv_wrapper', 1, 2, 5).
python_function('tests/test_autonomous.py', 'test_wup_watch_command_keeps_explicit_testql_bin', 1, 2, 2).
python_function('tests/test_autonomous.py', 'test_wup_watch_command_normalizes_percent_cpu_throttle', 1, 2, 3).
python_function('tests/test_autonomous.py', 'test_wup_subprocess_env_loads_project_wup_env', 2, 3, 4).
python_function('tests/test_autonomous.py', 'test_start_wup_watch_passes_playwright_env', 2, 6, 6).
python_function('tests/test_autonomous.py', 'test_wup_profiled_compose_services_start_before_watch', 2, 2, 7).
python_function('tests/test_autonomous.py', 'test_wup_compose_ps_accepts_json_lines', 0, 2, 2).
python_function('tests/test_autonomous.py', 'test_wup_topology_gate_uses_pipeline_for_gate_wup', 2, 4, 5).
python_function('tests/test_autonomous.py', 'test_read_wup_health_creates_high_priority_planfile_ticket', 1, 6, 7).
python_function('tests/test_autonomous.py', 'test_read_wup_health_ignores_degraded_fleet_and_clears_marker', 1, 4, 6).
python_function('tests/test_autonomous_diagnostics.py', 'test_build_idle_checks_quick_profile_skips_deep_tools', 2, 2, 2).
python_function('tests/test_autonomous_diagnostics.py', 'test_build_idle_checks_full_includes_redup_when_available', 2, 3, 2).
python_function('tests/test_autonomous_diagnostics.py', 'test_build_idle_checks_full_uses_changed_redup_when_wup_configured', 2, 5, 4).
python_function('tests/test_autonomous_diagnostics.py', 'test_run_idle_diagnostics_profile_off', 0, 3, 4).
python_function('tests/test_autonomous_parser_detection.py', 'test_looks_like_koru_auto_command', 0, 2, 1).
python_function('tests/test_autonomous_parser_detection.py', 'test_looks_like_koru_autonomous_up_command', 0, 2, 1).
python_function('tests/test_autonomous_parser_detection.py', 'test_looks_like_unrelated_command', 0, 2, 1).
python_function('tests/test_autonomous_process_detection.py', 'test_find_existing_autonomous_does_not_skip_sibling_from_same_shell', 2, 2, 5).
python_function('tests/test_autonomous_scenarios.py', 'test_autonomous_main_safe_up_expands_args', 0, 8, 3).
python_function('tests/test_autonomous_scenarios.py', 'test_autonomous_cycle_smoke_scenario', 0, 4, 8).
python_function('tests/test_autonomous_scenarios.py', 'test_autonomous_cycle_autopilot_skipped_when_no_client', 0, 1, 7).
python_function('tests/test_autonomous_scenarios.py', 'test_run_cycle_auto_heals_stale_socket', 0, 3, 9).
python_function('tests/test_autonomous_scenarios.py', 'test_autonomous_cycle_skips_autopilot_after_repeated_idle_when_threshold_set', 0, 4, 11).
python_function('tests/test_autonomous_startup.py', 'test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker', 1, 3, 5).
python_function('tests/test_autonomous_startup.py', 'test_resolve_autopilot_ide_for_autonomous_returns_string_lane', 0, 4, 2).
python_function('tests/test_autonomous_startup.py', 'test_resolve_agent_lane_respects_terminal_jetbrains_hint', 1, 3, 3).
python_function('tests/test_autonomous_startup.py', 'test_resolve_autopilot_ide_keeps_jetbrains_lane_when_plugin_ide_running', 0, 3, 2).
python_function('tests/test_autonomous_startup.py', 'test_resolve_autopilot_ide_keeps_jetbrains_when_no_plugin_ide_running', 0, 3, 2).
python_function('tests/test_autonomous_startup.py', 'test_format_post_startup_operator_hints_mentions_socket', 1, 6, 3).
python_function('tests/test_autonomous_startup.py', 'test_format_post_startup_operator_hints_for_jetbrains_skips_plugin_steps', 0, 5, 4).
python_function('tests/test_autonomous_startup.py', 'test_format_startup_banner_includes_version', 1, 4, 3).
python_function('tests/test_autonomous_startup.py', 'test_build_startup_probe_reports_per_ide_socket_for_explicit_ide', 2, 3, 4).
python_function('tests/test_autonomous_startup.py', 'test_apply_agent_lane_environ_uses_running_ide', 2, 5, 4).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_defaults', 0, 15, 1).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_from_env', 0, 16, 4).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_from_env_defaults', 0, 4, 2).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_from_env_actor_name_fallback', 0, 2, 2).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_ticket_sources_valid', 0, 3, 1).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_autopilot_action_valid', 0, 3, 1).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_idle_diagnostics_profile_valid', 0, 3, 1).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_stagnation_control_fields', 0, 7, 1).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_from_env_idle_streak', 0, 2, 2).
python_function('tests/test_autonomy_config.py', 'test_autonomy_config_diag_state_dir_default', 0, 2, 2).
python_function('tests/test_autonomy_env.py', 'test_auto_loop_env_defaults_cover_core_autoloop_flags', 0, 3, 0).
python_function('tests/test_autonomy_env.py', 'test_env_truthy_matrix', 1, 4, 3).
python_function('tests/test_autonomy_env.py', 'test_apply_autoloop_env_to_args_custom_environ', 0, 6, 2).
python_function('tests/test_autonomy_environment.py', 'test_probe_socket_health_missing_file', 1, 5, 1).
python_function('tests/test_autonomy_environment.py', 'test_probe_socket_health_stale_socket', 1, 4, 2).
python_function('tests/test_autonomy_environment.py', 'test_probe_socket_health_listening_socket', 1, 5, 6).
python_function('tests/test_autonomy_environment.py', 'test_probe_ide_presence_returns_entry_per_known_ide', 1, 5, 2).
python_function('tests/test_autonomy_environment.py', 'test_probe_ide_presence_detects_installed_binary', 1, 6, 7).
python_function('tests/test_autonomy_environment.py', 'test_probe_ide_presence_detects_koru_in_cursor_mcp', 1, 4, 5).
python_function('tests/test_autonomy_environment.py', 'test_probe_ide_presence_ignores_disabled_koru', 1, 4, 5).
python_function('tests/test_autonomy_environment.py', 'test_probe_environment_headless_via_env', 1, 4, 3).
python_function('tests/test_autonomy_environment.py', 'test_probe_environment_flags_stale_socket', 1, 4, 3).
python_function('tests/test_autonomy_environment.py', 'test_probe_environment_flags_missing_mcp_when_ide_installed', 1, 4, 6).
python_function('tests/test_autonomy_environment.py', 'test_remove_stale_socket_skips_when_not_stale', 1, 2, 2).
python_function('tests/test_autonomy_environment.py', 'test_remove_stale_socket_dry_run_does_not_mutate', 1, 3, 4).
python_function('tests/test_autonomy_environment.py', 'test_remove_stale_socket_fixes_real_stale_socket', 1, 3, 4).
python_function('tests/test_autonomy_environment.py', 'test_remove_stale_socket_idempotent_after_fix', 1, 3, 2).
python_function('tests/test_autonomy_environment.py', 'test_heal_environment_repairs_stale_socket', 1, 5, 5).
python_function('tests/test_autonomy_environment.py', 'test_heal_environment_no_op_on_clean_env', 1, 2, 2).
python_function('tests/test_autonomy_environment.py', 'test_summarise_no_repairs', 0, 2, 1).
python_function('tests/test_autonomy_environment.py', 'test_summarise_counts_statuses', 1, 3, 4).
python_function('tests/test_autonomy_prompts.py', '_call', 0, 1, 3).
python_function('tests/test_autonomy_prompts.py', 'test_idle_status_uses_drive_prompt', 0, 4, 1).
python_function('tests/test_autonomy_prompts.py', 'test_handoff_action_returns_drive_prompt', 0, 3, 1).
python_function('tests/test_autonomy_prompts.py', 'test_waiting_input_with_message_uses_ticket_prompt', 0, 3, 1).
python_function('tests/test_autonomy_prompts.py', 'test_waiting_input_empty_message_uses_fallback_prompt', 0, 5, 2).
python_function('tests/test_autonomy_prompts.py', 'test_waiting_input_empty_message_no_ticket_id', 0, 4, 1).
python_function('tests/test_autonomy_prompts.py', 'test_waiting_input_strips_whitespace_message', 0, 2, 1).
python_function('tests/test_autonomy_prompts.py', 'test_stagnation_below_threshold_no_escalation', 0, 2, 1).
python_function('tests/test_autonomy_prompts.py', 'test_stagnation_at_threshold_triggers_escalation', 0, 5, 2).
python_function('tests/test_autonomy_prompts.py', 'test_escalation_includes_status_and_streak', 0, 4, 1).
python_function('tests/test_autonomy_prompts.py', 'test_escalation_skipped_without_ticket_id', 0, 2, 1).
python_function('tests/test_autonomy_prompts.py', 'test_custom_escalation_threshold', 0, 2, 1).
python_function('tests/test_autonomy_prompts.py', 'test_drive_action_with_running_status', 0, 2, 1).
python_function('tests/test_autonomy_prompts.py', 'test_decision_is_frozen', 0, 1, 2).
python_function('tests/test_autopilot_audit.py', '_read_lines', 1, 3, 3).
python_function('tests/test_autopilot_audit.py', 'test_disabled_audit_is_silent', 1, 2, 4).
python_function('tests/test_autopilot_audit.py', 'test_record_writes_ndjson', 1, 9, 6).
python_function('tests/test_autopilot_audit.py', 'test_record_drops_none_values', 1, 3, 4).
python_function('tests/test_autopilot_audit.py', 'test_log_file_is_owner_only', 1, 2, 5).
python_function('tests/test_autopilot_audit.py', 'test_directory_is_owner_only', 1, 2, 5).
python_function('tests/test_autopilot_audit.py', 'test_default_log_path_uses_xdg_state', 2, 2, 3).
python_function('tests/test_autopilot_audit.py', 'test_default_log_path_falls_back_to_home', 1, 2, 2).
python_function('tests/test_autopilot_audit.py', 'test_multiple_records_appear_in_order', 1, 3, 5).
python_function('tests/test_autopilot_audit.py', 'test_rotation_caps_file_size', 1, 5, 8).
python_function('tests/test_autopilot_audit.py', 'test_unwritable_directory_disables_silently', 3, 3, 7).
python_function('tests/test_autopilot_cli.py', 'test_autopilot_parser_requires_action', 0, 1, 2).
python_function('tests/test_autopilot_cli.py', 'test_drive_without_daemon_errors', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_drive_missing_text_errors', 1, 3, 2).
python_function('tests/test_autopilot_cli.py', 'test_drive_prompt_flag', 2, 6, 5).
python_function('tests/test_autopilot_cli.py', 'test_drive_auto_fallbacks_to_direct_when_daemon_cannot_focus', 2, 6, 5).
python_function('tests/test_autopilot_cli.py', 'test_drive_auto_fallback_can_be_disabled_by_env', 2, 4, 7).
python_function('tests/test_autopilot_cli.py', 'test_drive_dry_run_direct', 2, 4, 6).
python_function('tests/test_autopilot_cli.py', 'test_drive_direct_prefers_os_injector_profile', 2, 3, 6).
python_function('tests/test_autopilot_cli.py', 'test_drive_direct_honors_os_profile_override', 2, 4, 7).
python_function('tests/test_autopilot_cli.py', 'test_drive_direct_os_profile_requires_os_injector_when_not_available', 2, 3, 5).
python_function('tests/test_autopilot_cli.py', 'test_drive_direct_os_profile_os_injector_error_no_fallback', 2, 4, 7).
python_function('tests/test_autopilot_cli.py', 'test_drive_direct_falls_back_when_os_injector_fails', 2, 4, 7).
python_function('tests/test_autopilot_cli.py', 'test_calibrate_auto_ide_resolves_from_running_processes', 3, 4, 8).
python_function('tests/test_autopilot_cli.py', 'test_calibrate_writes_profile_from_mouse', 3, 5, 7).
python_function('tests/test_autopilot_cli.py', 'test_session_start_explicit_ides', 3, 6, 10).
python_function('tests/test_autopilot_cli.py', 'test_session_start_keeps_profile_when_smoke_fails', 3, 7, 10).
python_function('tests/test_autopilot_cli.py', 'test_session_start_warns_on_duplicate_coordinates', 3, 9, 11).
python_function('tests/test_autopilot_cli.py', 'test_ide_list_empty', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_ide_list_marks_focused_ide', 2, 5, 4).
python_function('tests/test_autopilot_cli.py', 'test_doctor_json_output', 2, 6, 5).
python_function('tests/test_autopilot_cli.py', 'test_doctor_fix_text_output', 2, 6, 4).
python_function('tests/test_autopilot_cli.py', 'test_doctor_fix_json_output', 2, 6, 5).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_dry_run_auto_detect_from_term_program', 3, 9, 8).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_vsix_resolver_prefers_package_version', 2, 2, 6).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_auto_detect_ambiguous_running_ides_errors', 2, 3, 5).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_exec_success_json_payload', 3, 6, 6).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_vscodium_dry_run_uses_codium_cli', 3, 5, 5).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_zed_reports_vsix_plugin_unsupported', 1, 3, 2).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_pycharm_alias_maps_to_jetbrains', 1, 3, 2).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_jetbrains_dry_run_json', 3, 7, 8).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_jetbrains_success_json_payload', 3, 6, 8).
python_function('tests/test_autopilot_cli.py', 'test_install_plugin_auto_detects_pycharm_hosted_as_jetbrains', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_status_when_no_daemon', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_status_accepts_legacy_json_flag', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_shutdown_when_no_daemon', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_handoff_dry_run_prints_brief_and_skips_daemon', 3, 3, 4).
python_function('tests/test_autopilot_cli.py', 'test_handoff_requires_running_daemon', 3, 3, 4).
python_function('tests/test_autopilot_cli.py', 'test_handoff_drives_brief_through_client', 3, 8, 7).
python_function('tests/test_autopilot_cli.py', '_write_audit_log', 2, 2, 4).
python_function('tests/test_autopilot_cli.py', 'test_tail_text_format_renders_entries', 2, 7, 4).
python_function('tests/test_autopilot_cli.py', 'test_tail_json_format_returns_array', 2, 3, 5).
python_function('tests/test_autopilot_cli.py', 'test_tail_n_limits_output', 2, 6, 8).
python_function('tests/test_autopilot_cli.py', 'test_tail_missing_log_errors_cleanly', 2, 3, 3).
python_function('tests/test_autopilot_cli.py', 'test_tail_skips_malformed_lines', 2, 5, 4).
python_function('tests/test_autopilot_cli.py', 'test_install_unit_print_renders_execstart', 2, 4, 3).
python_function('tests/test_autopilot_cli.py', 'test_install_unit_writes_to_xdg_default_path', 3, 5, 7).
python_function('tests/test_autopilot_cli.py', 'test_install_unit_refuses_overwrite_without_force', 2, 4, 4).
python_function('tests/test_autopilot_cli.py', 'test_resolve_koru_bin_falls_back_to_sys_executable_sibling', 2, 2, 6).
python_function('tests/test_autopilot_client_drive_errors.py', 'test_drive_missing_socket_returns_ok_false', 1, 3, 4).
python_function('tests/test_autopilot_config.py', 'test_load_config_returns_defaults_when_file_missing', 1, 4, 1).
python_function('tests/test_autopilot_config.py', 'test_load_config_user_keys_override_defaults', 1, 5, 2).
python_function('tests/test_autopilot_config.py', 'test_load_config_malformed_toml_falls_back_to_defaults', 2, 5, 4).
python_function('tests/test_autopilot_config.py', 'test_load_config_skips_non_string_entries', 1, 5, 2).
python_function('tests/test_autopilot_config.py', 'test_load_config_ignores_unrelated_sections', 1, 2, 2).
python_function('tests/test_autopilot_config.py', 'test_submit_key_for_falls_back_to_default', 0, 3, 2).
python_function('tests/test_autopilot_config.py', 'test_submit_key_for_uses_explicit_default_when_present', 0, 2, 2).
python_function('tests/test_autopilot_config.py', 'test_submit_key_for_falls_back_when_no_default_key', 0, 2, 2).
python_function('tests/test_autopilot_config.py', 'test_default_config_path_uses_xdg_when_set', 2, 2, 3).
python_function('tests/test_autopilot_config.py', 'test_default_config_path_falls_back_to_home', 1, 3, 2).
python_function('tests/test_autopilot_config.py', 'test_cached_config_is_memoised', 1, 3, 7).
python_function('tests/test_autopilot_daemon.py', '_patch_no_running_ides', 1, 1, 1).
python_function('tests/test_autopilot_daemon.py', '_daemon', 2, 2, 4).
python_function('tests/test_autopilot_daemon.py', '_connect_plugin', 1, 3, 10).
python_function('tests/test_autopilot_daemon.py', '_assert_no_more_data', 1, 1, 3).
python_function('tests/test_autopilot_daemon.py', 'running_daemon', 2, 1, 2).
python_function('tests/test_autopilot_daemon.py', 'test_ping_round_trip', 1, 4, 3).
python_function('tests/test_autopilot_daemon.py', 'test_is_running_true_when_daemon_alive', 1, 2, 1).
python_function('tests/test_autopilot_daemon.py', 'test_drive_falls_back_to_injector_when_no_plugin', 1, 4, 1).
python_function('tests/test_autopilot_daemon.py', 'test_drive_require_plugin_blocks_keyboard_fallback', 1, 6, 1).
python_function('tests/test_autopilot_daemon.py', 'test_drive_reports_injector_failure', 2, 3, 4).
python_function('tests/test_autopilot_daemon.py', 'test_drive_uses_os_injector_when_profile_available', 2, 8, 12).
python_function('tests/test_autopilot_daemon.py', 'test_drive_os_injector_skipped_when_env_disabled', 2, 4, 7).
python_function('tests/test_autopilot_daemon.py', 'test_drive_os_injector_forced_without_profile_falls_back_to_keyboard', 2, 4, 6).
python_function('tests/test_autopilot_daemon.py', 'test_drive_os_injector_failure_falls_back_to_keyboard', 2, 4, 8).
python_function('tests/test_autopilot_daemon.py', 'test_drive_empty_text_returns_error', 1, 2, 2).
python_function('tests/test_autopilot_daemon.py', 'test_drive_unknown_type_returns_error', 1, 2, 8).
python_function('tests/test_autopilot_daemon.py', 'test_status_reports_socket_and_plugins', 1, 5, 1).
python_function('tests/test_autopilot_daemon.py', 'test_accept_rejects_foreign_peer_uid', 2, 4, 12).
python_function('tests/test_autopilot_daemon.py', 'test_plugin_hello_then_drive_forwards', 2, 8, 13).
python_function('tests/test_autopilot_daemon.py', 'test_drive_strict_plugin_version_blocks_stale_plugin', 2, 4, 16).
python_function('tests/test_autopilot_daemon.py', 'test_strict_plugin_hello_rejects_stale_without_evicting_current', 2, 8, 16).
python_function('tests/test_autopilot_daemon.py', 'test_repeated_stale_plugin_hello_rejections_are_log_throttled', 2, 7, 21).
python_function('tests/test_autopilot_daemon.py', 'test_rejected_plugin_log_default_interval_is_quiet', 2, 6, 10).
python_function('tests/test_autopilot_daemon.py', 'test_status_reports_rejected_plugin_versions', 2, 6, 15).
python_function('tests/test_autopilot_daemon.py', 'test_message_sent_event_completes_pending_drive_without_plugin_ack', 2, 8, 13).
python_function('tests/test_autopilot_daemon.py', 'test_message_sent_event_does_not_complete_strict_ack_drive', 2, 5, 15).
python_function('tests/test_autopilot_daemon.py', 'test_newer_plugin_connection_replaces_stale_same_ide_client', 2, 7, 14).
python_function('tests/test_autopilot_daemon.py', 'test_visible_typing_prefers_keyboard_even_when_plugin_connected', 2, 5, 15).
python_function('tests/test_autopilot_daemon.py', 'test_plugin_ack_with_shutdown_info_is_relayed', 2, 8, 13).
python_function('tests/test_autopilot_daemon.py', 'test_plugin_ack_submit_failure_uses_os_fallback', 2, 8, 14).
python_function('tests/test_autopilot_daemon.py', 'test_plugin_ack_failure_skips_os_fallback_if_require_plugin', 2, 5, 14).
python_function('tests/test_autopilot_daemon.py', 'test_default_handoff_builds_brief_for_uninitialised_project', 1, 4, 6).
python_function('tests/test_autopilot_daemon.py', 'test_session_ended_triggers_handoff_chat_send', 2, 13, 10).
python_function('tests/test_autopilot_daemon.py', 'test_session_ended_no_handoff_when_disabled', 2, 4, 9).
python_function('tests/test_autopilot_daemon.py', 'test_session_ended_skipped_during_cooldown', 2, 5, 9).
python_function('tests/test_autopilot_daemon.py', 'test_session_started_event_just_acks', 2, 3, 8).
python_function('tests/test_autopilot_daemon.py', 'test_shutdown_stops_daemon', 2, 5, 8).
python_function('tests/test_autopilot_host_setup.py', 'test_build_setup_host_report_has_expected_keys', 0, 6, 2).
python_function('tests/test_autopilot_host_setup.py', 'test_build_setup_host_report_json_roundtrip', 0, 2, 3).
python_function('tests/test_autopilot_host_setup.py', 'test_run_host_setup_install_dry_run_no_sudo', 1, 2, 3).
python_function('tests/test_autopilot_host_setup.py', 'test_run_host_setup_install_calls_apt_when_missing', 1, 2, 6).
python_function('tests/test_autopilot_host_setup.py', 'test_autopilot_cli_setup_host_invokes_runner', 0, 4, 3).
python_function('tests/test_autopilot_ide.py', 'fake_proc', 2, 1, 15).
python_function('tests/test_autopilot_ide.py', 'test_detect_running_ides_finds_windsurf_and_jetbrains', 1, 5, 1).
python_function('tests/test_autopilot_ide.py', 'test_detect_running_ides_deduplicates_same_ide', 1, 2, 2).
python_function('tests/test_autopilot_ide.py', 'test_detect_running_ides_prefers_primary_windsurf_over_devin_helper', 2, 8, 15).
python_function('tests/test_autopilot_ide.py', 'test_detect_running_ides_skips_unknown_processes', 1, 2, 1).
python_function('tests/test_autopilot_ide.py', 'test_detect_running_ides_separates_vscode_and_vscodium', 2, 4, 14).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_prefers_user_choice', 1, 3, 2).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_returns_none_when_pref_not_running', 1, 2, 2).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_defaults_to_first', 2, 3, 4).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_prefers_koru_autopilot_ide_env', 2, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_ignores_koru_autopilot_ide_env_when_not_running', 2, 3, 4).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_empty_list_returns_none', 0, 2, 1).
python_function('tests/test_autopilot_ide.py', 'test_detect_focused_ide_id_from_active_pid', 1, 2, 1).
python_function('tests/test_autopilot_ide.py', 'test_detect_focused_ide_id_returns_none_for_unknown_pid', 1, 2, 1).
python_function('tests/test_autopilot_ide.py', 'test_focused_ide_returns_matching_instance', 1, 3, 2).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_prefers_focused_when_no_explicit_prefer', 2, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_explicit_prefer_beats_focus', 1, 3, 2).
python_function('tests/test_autopilot_ide.py', 'test_resolve_drive_target_auto_picks_first_ide_with_profile', 2, 4, 3).
python_function('tests/test_autopilot_ide.py', 'test_detect_terminal_host_ide_id_cursor_env', 1, 2, 3).
python_function('tests/test_autopilot_ide.py', 'test_detect_terminal_host_ide_id_cursor_beats_windsurf_token', 1, 2, 2).
python_function('tests/test_autopilot_ide.py', 'test_detect_terminal_host_ide_id_vscode_nls_without_pid', 1, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_detect_terminal_host_ide_id_vscodium_from_vscode_family_env', 1, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_detect_terminal_host_ide_id_zed_term_program', 1, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_normalize_ide_id_aliases', 2, 2, 2).
python_function('tests/test_autopilot_ide.py', 'test_pick_target_prefers_terminal_host_over_signature_order', 2, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_resolve_drive_target_terminal_without_profile_skips_other_profiles', 2, 4, 4).
python_function('tests/test_autopilot_ide.py', 'test_resolve_drive_target_auto_prefers_focused_when_it_has_profile', 2, 3, 3).
python_function('tests/test_autopilot_ide.py', 'test_resolve_drive_target_explicit_zed_without_running_process', 1, 4, 2).
python_function('tests/test_autopilot_ide.py', 'test_detect_cached_uses_cache_within_ttl', 1, 2, 5).
python_function('tests/test_autopilot_ide.py', 'test_detect_cached_ttl_zero_always_refreshes', 1, 3, 5).
python_function('tests/test_autopilot_ide.py', 'test_clear_detect_cache_forces_refresh', 1, 3, 5).
python_function('tests/test_autopilot_injector.py', '_fake_runner', 1, 2, 2).
python_function('tests/test_autopilot_injector.py', '_which_factory', 1, 1, 0).
python_function('tests/test_autopilot_injector.py', 'test_select_backend_x11_prefers_xdotool', 0, 2, 3).
python_function('tests/test_autopilot_injector.py', 'test_select_backend_wayland_prefers_wtype_over_ydotool', 0, 2, 3).
python_function('tests/test_autopilot_injector.py', 'test_select_backend_wayland_falls_back_to_ydotool', 0, 2, 3).
python_function('tests/test_autopilot_injector.py', 'test_select_backend_unknown_session_without_display_prefers_wayland_tools', 1, 2, 4).
python_function('tests/test_autopilot_injector.py', 'test_select_backend_no_tools_returns_none', 0, 2, 4).
python_function('tests/test_autopilot_injector.py', 'test_type_text_dry_run_does_not_call_runner', 0, 4, 4).
python_function('tests/test_autopilot_injector.py', 'test_type_text_xdotool_types_and_submits', 0, 7, 4).
python_function('tests/test_autopilot_injector.py', 'test_type_text_xdotool_supports_extra_enter', 1, 4, 7).
python_function('tests/test_autopilot_injector.py', 'test_type_text_ydotool_uses_configurable_enter_key', 1, 6, 6).
python_function('tests/test_autopilot_injector.py', 'test_type_text_ydotool_submit_newline_mode', 1, 3, 7).
python_function('tests/test_autopilot_injector.py', 'test_type_text_ydotool_submit_ctrl_enter_mode', 1, 5, 6).
python_function('tests/test_autopilot_injector.py', 'test_type_text_wtype_uses_modifiers_for_jetbrains', 0, 6, 4).
python_function('tests/test_autopilot_injector.py', 'test_type_text_no_submit_only_types', 0, 2, 5).
python_function('tests/test_autopilot_injector.py', 'test_type_text_propagates_runner_error', 0, 1, 5).
python_function('tests/test_autopilot_injector.py', 'test_type_text_empty_raises', 0, 1, 4).
python_function('tests/test_autopilot_injector.py', 'test_type_text_no_backend_raises', 0, 1, 5).
python_function('tests/test_autopilot_injector.py', 'test_probe_marks_unavailable_when_missing_tool', 0, 5, 3).
python_function('tests/test_autopilot_injector.py', 'test_probe_marks_unavailable_on_wrong_session', 0, 4, 3).
python_function('tests/test_autopilot_injector.py', 'test_wtype_rejects_multi_modifier_submit_key', 1, 3, 8).
python_function('tests/test_autopilot_injector.py', 'test_type_text_wayland_falls_back_when_wtype_fails', 0, 4, 6).
python_function('tests/test_autopilot_injector.py', 'test_injector_forced_backend', 1, 2, 5).
python_function('tests/test_autopilot_injector.py', 'test_wtype_single_modifier_still_works', 0, 2, 4).
python_function('tests/test_autopilot_jetbrains_scaffold.py', 'test_jetbrains_plugin_scaffold_files_exist', 0, 4, 1).
python_function('tests/test_autopilot_jetbrains_scaffold.py', 'test_jetbrains_plugin_metadata_wires_service_and_action', 0, 5, 1).
python_function('tests/test_autopilot_jetbrains_scaffold.py', 'test_jetbrains_plugin_readme_no_longer_stub', 0, 3, 1).
python_function('tests/test_autopilot_os_injector.py', 'test_save_and_load_profile', 1, 4, 5).
python_function('tests/test_autopilot_os_injector.py', 'test_load_profile_accepts_legacy_window_id', 1, 3, 3).
python_function('tests/test_autopilot_os_injector.py', 'test_profile_from_mouse_builds_profile', 0, 2, 2).
python_function('tests/test_autopilot_os_injector.py', 'test_capture_from_xdotool_parses_shell_output', 1, 2, 3).
python_function('tests/test_autopilot_os_injector.py', 'test_inject_with_profile_paste_path_uses_clipboard_then_ctrl_v', 1, 9, 9).
python_function('tests/test_autopilot_os_injector.py', 'test_inject_with_profile_type_fallback_when_no_clip_tools', 1, 6, 7).
python_function('tests/test_autopilot_os_injector.py', 'test_load_profile_missing_raises', 1, 1, 2).
python_function('tests/test_autopilot_os_injector.py', 'test_inject_with_profile_paste_timeout_is_reported', 1, 1, 7).
python_function('tests/test_autopilot_os_injector.py', 'test_try_load_profile_prefers_project_over_cwd', 2, 3, 5).
python_function('tests/test_autopilot_os_injector.py', 'test_iter_config_paths_dedupes_project_and_cwd', 1, 2, 4).
python_function('tests/test_autopilot_os_injector.py', 'test_try_drive_with_profile_skips_saved_profile_on_wayland_unless_forced', 2, 2, 8).
python_function('tests/test_autopilot_os_injector.py', 'test_try_drive_with_profile_forced_works_on_wayland', 2, 3, 7).
python_function('tests/test_autopilot_os_injector.py', 'test_try_drive_with_profile_skips_when_env_disabled', 1, 2, 3).
python_function('tests/test_autopilot_os_injector.py', 'test_try_drive_with_profile_uses_config', 2, 4, 7).
python_function('tests/test_autopilot_os_injector.py', 'test_inject_post_focus_delay_env_controls_sleep', 1, 2, 8).
python_function('tests/test_autopilot_os_injector.py', 'test_inject_post_focus_delay_zero_skips_sleep', 1, 2, 9).
python_function('tests/test_autopilot_plugin_installer.py', 'test_resolve_target_ide_prefers_autopilot_env', 1, 2, 3).
python_function('tests/test_autopilot_plugin_installer.py', 'test_resolve_target_ide_uses_running_supported_ide', 1, 2, 4).
python_function('tests/test_autopilot_plugin_installer.py', 'test_resolve_target_ide_uses_integrated_terminal_hint', 1, 3, 4).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_dry_run_builds_editor_command', 2, 3, 6).
python_function('tests/test_autopilot_plugin_installer.py', 'test_resolve_extension_vsix_finds_repo_plugin_package', 2, 2, 7).
python_function('tests/test_autopilot_plugin_installer.py', 'test_resolve_extension_vsix_prefers_package_version', 2, 2, 7).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_configures_socket_path', 2, 7, 8).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_targets_vscodium_from_integrated_terminal', 2, 6, 9).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_explicit_vscode_does_not_use_codium_hint', 2, 5, 7).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_prefers_running_vscode_over_stale_codium_terminal_hint', 2, 4, 8).
python_function('tests/test_autopilot_plugin_installer.py', 'test_install_plugin_skips_when_extension_already_installed', 1, 2, 4).
python_function('tests/test_autopilot_plugin_installer.py', 'test_installed_extension_version_for_ide_reads_editor_cli', 1, 2, 3).
python_function('tests/test_autopilot_protocol.py', 'test_encode_round_trip_minimal', 0, 5, 4).
python_function('tests/test_autopilot_protocol.py', 'test_encode_strips_reserved_keys_from_data', 0, 4, 3).
python_function('tests/test_autopilot_protocol.py', 'test_decode_rejects_unknown_type', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_rejects_malformed_json', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_rejects_oversized_line', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_rejects_non_object_top_level', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_requires_type_field', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_id_must_be_string_when_present', 0, 1, 2).
python_function('tests/test_autopilot_protocol.py', 'test_decode_extra_fields_land_in_data', 0, 4, 1).
python_function('tests/test_autopilot_protocol.py', 'test_builders_produce_valid_envelopes', 0, 4, 9).
python_function('tests/test_autopilot_protocol.py', 'test_ack_default_ok_true', 0, 2, 1).
python_function('tests/test_autopilot_protocol.py', 'test_error_carries_message', 0, 3, 1).
python_function('tests/test_autopilot_protocol.py', 'test_decode_drops_unknown_fields_for_strict_type', 0, 4, 1).
python_function('tests/test_autopilot_protocol.py', 'test_decode_drops_unknown_fields_on_chat_send', 0, 2, 1).
python_function('tests/test_autopilot_protocol.py', 'test_decode_drops_all_extras_on_zero_field_type', 0, 2, 1).
python_function('tests/test_autopilot_protocol.py', 'test_decode_keeps_arbitrary_extras_for_ack', 0, 4, 1).
python_function('tests/test_autopilot_protocol.py', 'test_decode_keeps_arbitrary_extras_for_error', 0, 4, 1).
python_function('tests/test_autopilot_protocol.py', 'test_drive_with_unknown_ide_field_value_passes_known_fields', 0, 2, 1).
python_function('tests/test_autopilot_socket_path.py', 'test_explicit_socket_env_overrides_all', 2, 2, 5).
python_function('tests/test_autopilot_socket_path.py', 'test_instance_env_changes_basename', 1, 2, 3).
python_function('tests/test_autopilot_socket_path.py', 'test_default_basename_legacy_when_no_instance', 1, 2, 2).
python_function('tests/test_autopilot_socket_path.py', 'test_auto_instance_uses_default_basename', 1, 2, 3).
python_function('tests/test_bootstrap.py', '_write_yaml', 2, 1, 2).
python_function('tests/test_cli.py', '_tmp_git_project', 1, 1, 4).
python_function('tests/test_cli.py', '_run_main', 0, 1, 4).
python_function('tests/test_context.py', '_ok', 1, 1, 1).
python_function('tests/test_context.py', '_fail', 1, 1, 1).
python_function('tests/test_context.py', '_no_git', 1, 1, 0).
python_function('tests/test_context.py', '_init_planfile', 1, 1, 2).
python_function('tests/test_dashboard_topology_post.py', 'test_apply_topology_post_update_rejects_non_object_components', 0, 4, 2).
python_function('tests/test_dashboard_topology_post.py', 'test_apply_topology_post_update_applies_component_toggle', 1, 5, 3).
python_function('tests/test_dev_sync.py', 'test_sync_developer_packages_installs_existing_repos', 1, 3, 7).
python_function('tests/test_dev_sync.py', 'test_sync_developer_packages_skips_dirty_pull', 1, 4, 6).
python_function('tests/test_docker_ide_matrix.py', 'test_headless_bridge_route_honors_each_matrix_ide', 1, 4, 2).
python_function('tests/test_docker_ide_matrix.py', 'test_autopilot_plugin_requirement_matrix', 2, 2, 3).
python_function('tests/test_docker_ide_matrix.py', 'test_every_matrix_ide_has_submit_key_default', 1, 2, 3).
python_function('tests/test_docker_ide_matrix.py', 'test_every_matrix_ide_has_isolated_default_socket', 2, 2, 4).
python_function('tests/test_docker_ide_matrix.py', 'test_container_matrix_env_matches_supported_ide', 0, 3, 2).
python_function('tests/test_docker_ide_matrix_config.py', 'test_docker_ide_matrix_script_covers_supported_systems_and_ides', 0, 5, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_docker_ide_matrix_dockerfile_installs_fake_cli_surface', 0, 3, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_docker_ide_matrix_workflow_exposes_full_matrix', 0, 7, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_docker_ide_matrix_entrypoint_manages_plugin_ides', 0, 4, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_native_ide_matrix_workflow_exposes_windows_and_macos', 0, 7, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_readme_documents_current_ide_matrix_state', 0, 9, 1).
python_function('tests/test_docker_ide_matrix_config.py', 'test_ide_router_docs_document_current_matrix_state', 0, 7, 1).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_ide_control_surfaces_doc_exists_with_key_sections', 0, 7, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_ide_router_doc_links_to_ide_control_surfaces', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_ide_router_doc_links_mcp_and_autopilot', 0, 3, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_mcp_ide_flow_doc_links_to_ide_control_surfaces', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_autopilot_design_doc_links_to_ide_control_surfaces', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_agent_guide_links_to_ide_control_surfaces', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_readme_links_ide_control_surfaces', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_ide_protocol_doc_exists_with_key_protocol_terms', 0, 7, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_ide_protocol_doc_has_no_stale_payload_placeholder', 0, 3, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_readme_links_formal_ide_protocol', 0, 2, 3).
python_function('tests/test_docs_ide_control_surfaces.py', 'test_docs_index_links_formal_ide_protocol', 0, 2, 3).
python_function('tests/test_doctor.py', '_scaffold', 1, 2, 3).
python_function('tests/test_doctor.py', '_run', 1, 1, 1).
python_function('tests/test_doctor.py', '_named', 2, 4, 1).
python_function('tests/test_drive_orchestrator.py', 'test_plugin_required_message_mentions_ide_and_connect_command', 0, 3, 1).
python_function('tests/test_drive_orchestrator.py', 'test_should_try_os_fallback_false_when_plugin_required', 0, 2, 1).
python_function('tests/test_drive_orchestrator.py', 'test_should_try_os_fallback_true_for_submit_failure', 0, 2, 1).
python_function('tests/test_drive_orchestrator.py', 'test_build_message_sent_info_keeps_chat_and_backend', 0, 6, 1).
python_function('tests/test_drive_orchestrator.py', 'test_annotate_plugin_ack_marks_strict_when_winning_commands_exist', 0, 2, 1).
python_function('tests/test_drive_orchestrator.py', 'test_annotate_plugin_ack_marks_plugin_ack_without_winning_commands', 0, 2, 1).
python_function('tests/test_drive_orchestrator.py', 'test_plugin_version_info_marks_mismatch', 1, 5, 2).
python_function('tests/test_drive_orchestrator.py', 'test_plugin_version_policy_can_block', 1, 2, 2).
python_function('tests/test_drive_orchestrator.py', 'test_bundled_expected_plugin_version_matches_vscode_package_json', 0, 2, 4).
python_function('tests/test_drive_orchestrator.py', 'test_strict_plugin_version_blocks_when_expected_version_missing', 1, 3, 4).
python_function('tests/test_e2e.py', '_tmp_git_project', 1, 1, 4).
python_function('tests/test_e2e.py', '_run_main', 0, 3, 4).
python_function('tests/test_e2e.py', '_write_sprint', 3, 1, 3).
python_function('tests/test_e2e.py', '_write_config', 3, 1, 3).
python_function('tests/test_e2e.py', '_ts', 1, 1, 3).
python_function('tests/test_e2e.py', '_done_ticket', 2, 1, 1).
python_function('tests/test_e2e.py', '_init_project', 1, 1, 2).
python_function('tests/test_e2e.py', '_extract_json', 1, 3, 3).
python_function('tests/test_gate.py', '_ok', 1, 1, 1).
python_function('tests/test_gate.py', '_fail', 1, 1, 1).
python_function('tests/test_gate.py', 'test_authorize_gate_records_structured_note', 1, 12, 9).
python_function('tests/test_gate.py', 'test_authorize_gate_rejects_unknown_mode', 1, 1, 3).
python_function('tests/test_gate.py', 'test_authorize_gate_requires_reason', 1, 1, 3).
python_function('tests/test_gate.py', 'test_authorize_gate_propagates_planfile_failure', 1, 1, 3).
python_function('tests/test_gate.py', 'test_parse_authorizations_round_trip', 0, 3, 4).
python_function('tests/test_gate.py', 'test_parse_authorizations_ignores_malformed_or_unrelated_notes', 0, 2, 1).
python_function('tests/test_gate.py', 'test_parse_authorizations_returns_records_in_insertion_order', 0, 3, 3).
python_function('tests/test_gate.py', 'test_valid_modes_constant_matches_documented_set', 0, 2, 1).
python_function('tests/test_gc.py', '_write_sprint', 3, 1, 3).
python_function('tests/test_gc.py', '_ts', 1, 1, 3).
python_function('tests/test_gc.py', '_ticket', 4, 1, 1).
python_function('tests/test_gc_cli_helpers.py', 'test_gc_statuses_from_args_splits_csv', 0, 2, 2).
python_function('tests/test_gc_cli_helpers.py', 'test_gc_result_to_json_shape', 0, 3, 3).
python_function('tests/test_gc_cli_helpers.py', 'test_print_gc_text_report_empty', 1, 2, 3).
python_function('tests/test_ide_client.py', 'test_legacy_adapter_forwards_all_operations', 0, 5, 7).
python_function('tests/test_ide_client.py', 'test_build_legacy_ide_client_uses_autopilot_client', 1, 4, 5).
python_function('tests/test_ide_client.py', 'test_build_koruide_client_uses_koruide_package', 1, 3, 5).
python_function('tests/test_ide_client.py', 'test_build_ide_client_defaults_to_legacy', 1, 2, 4).
python_function('tests/test_ide_client.py', 'test_build_ide_client_can_select_koruide', 1, 2, 3).
python_function('tests/test_ide_client.py', 'test_build_ide_client_uses_env_when_backend_not_passed', 1, 2, 4).
python_function('tests/test_ide_client_contract.py', '_legacy_factory', 1, 1, 1).
python_function('tests/test_ide_client_contract.py', '_koruide_factory', 1, 1, 1).
python_function('tests/test_ide_client_contract.py', 'test_contract_is_running', 1, 3, 4).
python_function('tests/test_ide_client_contract.py', 'test_contract_drive', 1, 5, 4).
python_function('tests/test_ide_client_contract.py', 'test_contract_status', 1, 4, 4).
python_function('tests/test_ide_client_contract.py', 'test_contract_shutdown', 1, 3, 4).
python_function('tests/test_ide_router.py', 'test_is_headless_false_minimal_env', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_koru_headless_yes', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_koru_headless_on', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_koru_headless_false_explicit', 0, 3, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_ide_mode_whitespace_case_insensitive', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_ssh_empty_display_still_headless', 0, 2, 2).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_env_ide_case_insensitive', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_normalizes_vscode_family_alias', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_normalizes_zed_alias', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_sets_primary_surface', 0, 3, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_ide_shell_surface', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_ide_router_main_help_exits_zero', 0, 2, 2).
python_function('tests/test_ide_router.py', 'test_ide_router_main_unknown_flag_exits_nonzero', 0, 2, 2).
python_function('tests/test_ide_router.py', 'test_ide_router_main_bad_format_exits_nonzero', 1, 2, 3).
python_function('tests/test_ide_router.py', 'test_is_headless_ssh_without_display', 0, 2, 2).
python_function('tests/test_ide_router.py', 'test_is_headless_ssh_with_display_not_headless', 0, 2, 2).
python_function('tests/test_ide_router.py', 'test_is_headless_windows_ignores_ssh_without_display', 1, 2, 2).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_bad_env_uses_cli', 0, 3, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_whitespace_env_treated_as_missing', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_cli_invalid_env_empty_uses_auto', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_cli_auto_env_empty', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_notes_mention_escape_hatch', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_ide_shell_notes_mention_mcp', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_ide_router_main_json', 2, 4, 5).
python_function('tests/test_ide_router.py', 'test_ide_router_main_text', 2, 4, 3).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_env_overrides_cli', 0, 4, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_auto_env_does_not_override_cli', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_forces_auto', 0, 4, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_allow_autopilot_honors_env', 0, 3, 1).
python_function('tests/test_ide_router.py', 'test_is_headless_via_ide_mode', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_cli_ide_whitespace_normalized', 0, 2, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_allow_autopilot_yes_string', 0, 3, 1).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_environ_none_uses_os_environ', 1, 2, 3).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_headless_all_recommend_flags_false', 0, 4, 1).
python_function('tests/test_ide_router.py', 'test_ide_router_main_json_when_headless', 2, 5, 6).
python_function('tests/test_ide_router.py', 'test_resolve_ide_route_vscode_explicit_env', 0, 2, 1).
python_function('tests/test_ide_runtime.py', 'test_build_host_setup_report_delegates_to_legacy_backend', 1, 2, 3).
python_function('tests/test_ide_runtime.py', 'test_detect_running_ides_normalizes_rows', 1, 4, 3).
python_function('tests/test_ide_work.py', '_ok', 1, 1, 1).
python_function('tests/test_init.py', '_detach_ci_env', 0, 3, 0).
python_function('tests/test_init.py', '_reattach_ci_env', 1, 1, 1).
python_function('tests/test_install_manager.py', 'test_collect_report_flags_path_mismatch_and_plugin_version_missing', 2, 6, 4).
python_function('tests/test_install_manager.py', 'test_collect_report_uses_explicit_ide_socket_when_env_is_unset', 2, 4, 7).
python_function('tests/test_install_manager.py', 'test_collect_report_flags_connected_plugin_version_mismatch', 2, 4, 2).
python_function('tests/test_install_manager.py', 'test_collect_report_flags_installed_plugin_version_mismatch', 2, 4, 2).
python_function('tests/test_install_manager.py', 'test_collect_report_marks_installed_ok_but_not_connected_as_info', 2, 5, 2).
python_function('tests/test_install_manager.py', 'test_collect_report_flags_stale_live_extension_host', 2, 6, 2).
python_function('tests/test_install_manager.py', 'test_collect_report_warns_for_pyenv_shim', 2, 3, 3).
python_function('tests/test_install_manager.py', 'test_collect_report_warns_when_daemon_not_running', 2, 4, 2).
python_function('tests/test_install_manager.py', 'test_repair_installation_records_plugin_action', 2, 3, 5).
python_function('tests/test_install_manager.py', 'test_collect_report_for_zed_does_not_require_vsix_plugin', 2, 5, 4).
python_function('tests/test_install_manager.py', 'test_collect_report_auto_still_checks_plugin_connection', 2, 4, 2).
python_function('tests/test_koru_gate_capture.py', 'test_first_meaningful_line_skips_cloud_init_noise', 0, 2, 2).
python_function('tests/test_koru_gate_capture.py', 'test_first_meaningful_line_falls_back_to_nonempty_when_only_noise', 0, 2, 2).
python_function('tests/test_koru_queue_argv.py', 'test_build_queue_argv_apply_minimal', 1, 6, 3).
python_function('tests/test_koru_queue_argv.py', 'test_build_queue_argv_dry_and_max_steps', 1, 3, 2).
python_function('tests/test_koruapi.py', 'test_list_integrations_has_dsl_and_scan', 0, 5, 1).
python_function('tests/test_koruapi.py', 'test_dsl_roundtrip_invoke', 0, 2, 2).
python_function('tests/test_koruapi.py', 'test_unknown_integration', 0, 1, 3).
python_function('tests/test_koruapi.py', 'test_wired_handlers_are_catalogued', 0, 3, 3).
python_function('tests/test_koruapi.py', 'test_tool_list_tickets_status_filters', 1, 5, 5).
python_function('tests/test_koruapi.py', 'test_openapi_document_lists_invoke_path', 0, 4, 2).
python_function('tests/test_koruapi_transports.py', 'test_build_serve_parser_defaults', 0, 2, 2).
python_function('tests/test_koruapi_transports.py', 'test_integrations_include_gate_regix', 0, 2, 1).
python_function('tests/test_koruapi_transports.py', 'test_mcp_main_version_exit', 0, 2, 1).
python_function('tests/test_korudsl.py', 'test_normalize_and_roundtrip', 0, 4, 3).
python_function('tests/test_korudsl.py', 'test_library_to_dsl_objectives', 0, 2, 2).
python_function('tests/test_koruide_bridges.py', 'test_koruide_ide_bridge_exports_legacy_symbols', 0, 4, 0).
python_function('tests/test_koruide_bridges.py', 'test_koruide_injector_bridge_exports_legacy_symbols', 0, 4, 0).
python_function('tests/test_koruide_bridges.py', 'test_koruide_os_injector_bridge_exports_legacy_symbols', 0, 5, 0).
python_function('tests/test_koruide_bridges.py', 'test_autopilot_daemon_shim_points_to_koruide_implementation', 0, 3, 0).
python_function('tests/test_koruide_bridges.py', 'test_autopilot_audit_shim_points_to_koruide_implementation', 0, 3, 0).
python_function('tests/test_koruide_bridges.py', 'test_autopilot_host_setup_shim_points_to_koruide_implementation', 0, 3, 0).
python_function('tests/test_koruide_bridges.py', 'test_autopilot_plugin_installer_shim_points_to_koruide_implementation', 0, 3, 0).
python_function('tests/test_koruide_bridges.py', 'test_autopilot_config_shim_points_to_koruide_implementation', 0, 4, 0).
python_function('tests/test_koruide_client.py', 'test_koruide_client_forwards_all_operations', 0, 5, 7).
python_function('tests/test_koruide_client.py', 'test_build_client_sets_socket_path_and_timeout', 0, 4, 3).
python_function('tests/test_koruide_client.py', 'test_injected_client_without_request_raises_on_request_path', 0, 5, 7).
python_function('tests/test_koruide_client.py', 'test_drive_missing_socket_returns_ok_false', 1, 3, 4).
python_function('tests/test_local_service.py', '_urlopen_json', 1, 2, 6).
python_function('tests/test_local_service.py', '_urlopen_bytes', 1, 1, 2).
python_function('tests/test_local_service.py', 'local_service_server', 0, 2, 7).
python_function('tests/test_local_service.py', 'test_health_returns_ok_and_version', 1, 4, 3).
python_function('tests/test_local_service.py', 'test_post_event_roundtrip_and_ndjson_events', 1, 8, 11).
python_function('tests/test_local_service.py', 'test_post_enqueue_alias', 1, 3, 8).
python_function('tests/test_local_service.py', 'test_enqueue_adds_single_queue_item', 1, 5, 3).
python_function('tests/test_local_service.py', 'test_queue_claim_and_complete_with_lease', 1, 8, 4).
python_function('tests/test_local_service.py', 'test_queue_claim_filters_action_types', 1, 4, 3).
python_function('tests/test_local_service.py', 'test_worker_lifecycle_prefers_new_healthy_version', 1, 9, 3).
python_function('tests/test_local_service.py', 'test_worker_registration_keeps_manager_metadata', 1, 4, 3).
python_function('tests/test_local_service.py', 'test_worker_with_bad_health_is_quarantined', 1, 3, 3).
python_function('tests/test_local_service.py', 'test_lifecycle_decision_registers_unknown_worker', 1, 3, 3).
python_function('tests/test_local_service.py', 'test_post_empty_body_is_400', 1, 2, 3).
python_function('tests/test_local_service.py', 'test_unknown_path_404', 1, 2, 2).
python_function('tests/test_mcp_provision.py', 'test_detect_ides_uses_runtime_bridge', 1, 2, 2).
python_function('tests/test_mcp_provision.py', 'test_provision_cursor_dry_run_does_not_write', 1, 5, 2).
python_function('tests/test_mcp_provision.py', 'test_provision_cursor_writes_file_and_then_is_idempotent', 1, 5, 5).
python_function('tests/test_mcp_provision.py', 'test_provision_zed_writes_context_servers', 1, 4, 3).
python_function('tests/test_mcp_provision.py', 'test_provision_vscodium_uses_vscode_workspace_mcp_file', 1, 4, 2).
python_function('tests/test_mcp_provision.py', 'test_provision_upgrades_bare_koru_command_to_absolute', 2, 4, 9).
python_function('tests/test_mcp_provision.py', 'test_remove_from_config_removes_koru_entry', 1, 4, 6).
python_function('tests/test_mcp_provision.py', 'test_remove_from_config_removes_zed_context_server', 1, 4, 6).
python_function('tests/test_mcp_provision.py', 'test_init_ide_main_json_output_for_cursor_dry_run', 2, 5, 5).
python_function('tests/test_mcp_provision.py', 'test_init_ide_main_json_output_for_zed_dry_run', 2, 4, 4).
python_function('tests/test_mcp_provision.py', 'test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command', 2, 6, 10).
python_function('tests/test_mcp_provision.py', 'test_ensure_koru_mcp_not_disabled_includes_global_windsurf', 2, 4, 9).
python_function('tests/test_mcp_provision.py', 'test_ensure_koru_mcp_not_disabled_handles_zed_context_servers', 2, 5, 10).
python_function('tests/test_mcp_server.py', 'test_initialize_message_returns_server_info', 0, 5, 1).
python_function('tests/test_mcp_server.py', 'test_tools_list_includes_required_koru_tools', 0, 4, 2).
python_function('tests/test_mcp_server.py', 'test_tools_call_unknown_tool_returns_error_payload', 0, 4, 1).
python_function('tests/test_mcp_server.py', 'test_tool_job_status_unknown_job', 0, 3, 1).
python_function('tests/test_mcp_server.py', 'test_run_ticket_invokes_queue_mode_without_ticket_flag', 2, 6, 5).
python_function('tests/test_mcp_server.py', 'test_run_ticket_timeout_updates_job_status', 2, 5, 6).
python_function('tests/test_mcp_server.py', 'test_run_ticket_error_updates_job_status', 2, 5, 6).
python_function('tests/test_mcp_server.py', 'test_regix_gate_command_uses_workdir_not_project', 1, 7, 2).
python_function('tests/test_mcp_server.py', 'test_redup_gate_command_uses_supported_cli_shape', 1, 2, 2).
python_function('tests/test_mcp_server.py', 'test_job_store_is_ephemeral_across_imports', 1, 5, 4).
python_function('tests/test_mcp_server.py', 'test_job_store_persists_to_disk_and_reloads', 1, 6, 6).
python_function('tests/test_operator_pipeline.py', 'probe', 1, 1, 1).
python_function('tests/test_operator_pipeline.py', 'test_build_operator_steps_mcp_pending_without_config', 2, 5, 2).
python_function('tests/test_operator_pipeline.py', 'test_build_operator_steps_mcp_ok_when_configured', 2, 4, 5).
python_function('tests/test_operator_pipeline.py', 'test_build_operator_steps_skips_plugin_for_jetbrains', 2, 6, 3).
python_function('tests/test_operator_pipeline.py', 'test_build_operator_steps_plugin_probe_uses_resolved_ide', 2, 5, 2).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_creates_tickets', 3, 3, 5).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing', 3, 5, 5).
python_function('tests/test_operator_pipeline.py', 'test_candidate_planfile_health_urls_use_serve_endpoint', 1, 2, 4).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_dedup_markers', 3, 3, 4).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_recovers_missing_marker_from_open_ticket', 3, 9, 8).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_replaces_stale_ide_marker', 3, 8, 10).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_closes_resolved_marker_ticket', 3, 7, 9).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_keeps_marker_when_close_times_out', 3, 6, 9).
python_function('tests/test_operator_pipeline.py', 'test_run_startup_operator_pipeline_closes_marker_when_plugin_step_skipped', 3, 7, 10).
python_function('tests/test_planfile_queue.py', '_ok', 1, 1, 1).
python_function('tests/test_planfile_queue.py', '_ticket_args', 1, 1, 1).
python_function('tests/test_plugin_router.py', 'test_plugin_for_prefers_newest_matching_client', 0, 2, 3).
python_function('tests/test_plugin_router.py', 'test_drop_stale_plugins_removes_older_same_ide', 0, 6, 4).
python_function('tests/test_plugin_router.py', 'test_status_rows_include_only_plugin_clients', 0, 2, 4).
python_function('tests/test_policy.py', '_write_policy', 2, 1, 4).
python_function('tests/test_post_run_verify.py', '_ok', 1, 1, 1).
python_function('tests/test_post_run_verify.py', '_fail', 1, 1, 1).
python_function('tests/test_pyproject_metadata.py', '_pyproject', 0, 1, 2).
python_function('tests/test_pyproject_metadata.py', '_uv_lock_koru_package', 0, 3, 3).
python_function('tests/test_pyproject_metadata.py', 'test_base_runtime_dependencies_stay_small', 0, 2, 1).
python_function('tests/test_pyproject_metadata.py', 'test_all_extra_matches_union_of_other_extras', 0, 5, 3).
python_function('tests/test_pyproject_metadata.py', 'test_readme_documents_each_installation_extra', 0, 3, 2).
python_function('tests/test_pyproject_metadata.py', 'test_uv_lock_koru_metadata_matches_pyproject', 0, 4, 3).
python_function('tests/test_queue_clean.py', '_ok', 1, 1, 1).
python_function('tests/test_queue_clean.py', '_fail', 2, 1, 1).
python_function('tests/test_queue_clean.py', 'test_label_match_picks_only_fixture_labelled_tickets', 0, 6, 4).
python_function('tests/test_queue_clean.py', 'test_name_heuristic_only_runs_when_explicit', 0, 4, 1).
python_function('tests/test_queue_clean.py', 'test_name_heuristic_does_not_match_real_tickets_with_test_word', 0, 2, 1).
python_function('tests/test_queue_clean.py', 'test_active_tickets_skipped_by_default_but_surfaced', 0, 3, 2).
python_function('tests/test_queue_clean.py', 'test_include_active_promotes_skipped_back_to_candidates', 0, 3, 2).
python_function('tests/test_queue_clean.py', 'test_max_age_modifies_but_never_alone', 0, 9, 9).
python_function('tests/test_queue_clean.py', 'test_age_calculation_handles_z_suffix_and_naive_dates', 0, 5, 3).
python_function('tests/test_queue_clean.py', '_list_response', 1, 1, 2).
python_function('tests/test_queue_clean.py', 'test_clean_queue_dry_run_lists_but_does_not_close', 1, 7, 7).
python_function('tests/test_queue_clean.py', 'test_clean_queue_apply_closes_each_candidate_with_audit_note', 1, 10, 11).
python_function('tests/test_queue_clean.py', 'test_clean_queue_records_failures_per_ticket', 1, 3, 6).
python_function('tests/test_queue_clean.py', 'test_clean_queue_propagates_list_failure_as_runtime_error', 1, 1, 3).
python_function('tests/test_queue_clean.py', 'test_clean_queue_handles_empty_list_gracefully', 1, 4, 3).
python_function('tests/test_queue_clean.py', 'test_cleanup_candidate_explanation_is_human_readable', 0, 5, 2).
python_function('tests/test_queue_clean.py', 'test_report_to_dict_is_json_serialisable', 0, 7, 5).
python_function('tests/test_queue_cli_helpers.py', 'test_queue_status_marker_known_status', 0, 2, 1).
python_function('tests/test_queue_cli_helpers.py', 'test_queue_loop_exit_code_success', 0, 3, 1).
python_function('tests/test_queue_cli_helpers.py', 'test_single_task_ticket_lists', 0, 2, 2).
python_function('tests/test_queue_cli_helpers.py', 'test_emit_queue_run_started_does_not_raise', 0, 1, 2).
python_function('tests/test_queue_cli_helpers.py', 'test_run_queue_loop_mode_stops_after_local_manager_drain', 1, 5, 7).
python_function('tests/test_redup_integration.py', 'test_changed_scan_command_uses_current_python_module', 0, 3, 1).
python_function('tests/test_redup_integration.py', 'test_scan_and_check_commands_use_current_python_module', 1, 3, 3).
python_function('tests/test_redup_integration.py', 'test_changed_scan_runner_uses_current_python', 0, 2, 1).
python_function('tests/test_redup_integration.py', 'test_run_changed_scan_skips_full_fallback_by_default', 2, 6, 8).
python_function('tests/test_redup_integration.py', 'test_run_changed_scan_full_fallback_is_opt_in', 2, 3, 7).
python_function('tests/test_refactor_planfile_handoff.py', 'test_render_handoff_mentions_analysis_paths', 1, 3, 1).
python_function('tests/test_refactor_planfile_handoff.py', 'test_render_handoff_notes_when_analysis_present', 1, 2, 3).
python_function('tests/test_regix_taskfile.py', 'test_quality_regix_uses_current_regix_gates_command', 0, 7, 1).
python_function('tests/test_run_log.py', '_result', 0, 1, 3).
python_function('tests/test_runtime_insights.py', 'test_collect_runtime_insights_summarizes_processes', 1, 5, 3).
python_function('tests/test_runtime_insights.py', 'test_collect_runtime_insights_includes_detected_ides', 1, 3, 4).
python_function('tests/test_scan.py', '_ok', 3, 1, 1).
python_function('tests/test_scan.py', '_marker_fixture', 0, 2, 1).
python_function('tests/test_semcod_tools.py', 'test_detect_semcod_tools_covers_core_semcod_extensions', 1, 6, 2).
python_function('tests/test_semcod_tools.py', 'test_detect_semcod_tools_marks_pyproject_config_without_binary', 1, 4, 2).
python_function('tests/test_serve.py', '_minimal_planfile_project', 0, 1, 4).
python_function('tests/test_serve.py', '_free_port', 0, 1, 4).
python_function('tests/test_serve.py', '_start', 2, 3, 8).
python_function('tests/test_serve.py', '_get', 2, 1, 4).
python_function('tests/test_serve.py', '_post_json', 3, 1, 7).
python_function('tests/test_serve.py', 'test_cmdline_suggests_koru_serve_from_bytes', 0, 4, 1).
python_function('tests/test_serve.py', 'test_bulk_waiting_input_action_approve', 0, 4, 5).
python_function('tests/test_serve.py', 'test_bulk_waiting_input_action_reject', 0, 6, 6).
python_function('tests/test_serve.py', 'test_start_serve_background_shutdown', 0, 3, 10).
python_function('tests/test_shell_evidence.py', 'test_format_shell_run_note_includes_meta_and_streams', 0, 7, 5).
python_function('tests/test_shell_evidence.py', 'test_format_shell_run_note_truncates_long_stdout', 0, 4, 5).
python_function('tests/test_shell_evidence.py', 'test_format_shell_run_note_hard_total_cap', 0, 2, 2).
python_function('tests/test_stdio_autonomous_jsonl.py', '_parse_jsonl', 1, 3, 4).
python_function('tests/test_stdio_autonomous_jsonl.py', 'test_jsonl_session_emits_versioned_envelope', 2, 15, 7).
python_function('tests/test_stdio_autonomous_jsonl.py', 'test_default_stdio_format_from_env_jsonl', 1, 3, 2).
python_function('tests/test_stdio_autonomous_jsonl.py', 'test_stdio_event_schema_version_constant', 0, 2, 0).
python_function('tests/test_tools.py', 'test_load_registry_from_explicit_path', 1, 4, 5).
python_function('tests/test_tools.py', 'test_detect_tools_marks_available_via_command', 1, 5, 2).
python_function('tests/test_tools.py', 'test_detect_tools_marks_available_via_marker', 1, 3, 3).
python_function('tests/test_tools.py', 'test_infer_adapter_kind_defaults', 0, 4, 1).
python_function('tests/test_tools.py', 'test_build_tool_task_scaffold_contains_expected_fields', 0, 5, 1).
python_function('tests/test_tools.py', 'test_build_tool_task_scaffold_plugin_bridge_shape', 0, 6, 1).
python_function('tests/test_topology_cli.py', 'test_render_topology_text_includes_components_and_pipelines', 0, 4, 1).
python_function('tests/test_wup_taskfile.py', 'test_quality_wup_checks_status_and_respects_topology_gate', 0, 5, 1).
python_function('tests/test_wup_taskfile.py', 'test_operator_pipeline_taskfile_commands_exist', 0, 10, 1).
python_function('tests/test_wup_taskfile.py', 'test_wup_yaml_is_bootstrapped_for_koru_project', 0, 5, 1).

% ── Python Classes ───────────────────────────────────────
python_class('src/koru/agent_backend_runtime.py', 'AgentBackend').
python_method('AgentBackend', 'send_chat', 2, 2, 0).
python_class('src/koru/agent_backend_runtime.py', 'PluginSocketBackend').
python_method('PluginSocketBackend', 'send_chat', 2, 2, 1).
python_class('src/koru/agent_backend_runtime.py', 'McpToolBackend').
python_method('McpToolBackend', 'send_chat', 2, 2, 0).
python_class('src/koru/agent_backend_runtime.py', 'NoopBackend').
python_method('NoopBackend', 'send_chat', 2, 2, 0).
python_class('src/koru/agent_backend_runtime.py', 'OsInjectorBackend').
python_method('OsInjectorBackend', 'send_chat', 2, 2, 3).
python_class('src/koru/agent_backends.py', 'AgentBackendProfile').
python_class('src/koru/agent_backends.py', 'LaneConfig').
python_class('src/koru/agent_backends.py', 'AgentIntegrationConfig').
python_class('src/koru/agents.py', 'AgentOption').
python_method('AgentOption', 'to_dict', 0, 1, 0).
python_class('src/koru/autonomous.py', 'ExistingAutonomousProcess').
python_class('src/koru/autonomous.py', 'ExistingManagedProcess').
python_class('src/koru/autonomous.py', 'AutoPipelineState').
python_class('src/koru/autonomous.py', 'AutoPipelineProfile').
python_class('src/koru/autonomous_cycle.py', 'DiagnosticResult').
python_class('src/koru/autonomous_cycle.py', 'AutoloopState').
python_class('src/koru/autonomous_process_guard.py', 'ExistingAutonomousProcess').
python_class('src/koru/autonomous_process_guard.py', 'ExistingManagedProcess').
python_class('src/koru/autonomous_startup.py', 'AutonomousStartupProbe').
python_class('src/koru/autonomous_wup.py', 'WupWatchConfig').
python_class('src/koru/autonomous_wup.py', 'WupHealthResult').
python_class('src/koru/autonomous_wup.py', '_WupEventState').
python_class('src/koru/autonomy/config.py', 'AutonomyConfig').
python_method('AutonomyConfig', 'from_env', 1, 4, 9).
python_class('src/koru/autonomy/environment.py', 'IDEPresence').
python_method('IDEPresence', 'installed', 0, 1, 0).
python_class('src/koru/autonomy/environment.py', 'SocketHealth').
python_method('SocketHealth', 'healthy', 0, 2, 0).
python_class('src/koru/autonomy/environment.py', 'EnvironmentReport').
python_method('EnvironmentReport', 'installed_ides', 0, 3, 0).
python_method('EnvironmentReport', 'mcp_enabled_ides', 0, 3, 0).
python_class('src/koru/autonomy/heal.py', 'RepairResult').
python_class('src/koru/autonomy/operator_pipeline.py', 'OperatorStep').
python_class('src/koru/autonomy/operator_pipeline.py', 'OperatorPipelineResult').
python_class('src/koru/autonomy/post_run_verify.py', '_HasIdeVerifyState').
python_class('src/koru/autonomy/post_run_verify.py', 'PostRunVerifyConfig').
python_class('src/koru/autonomy/prompts.py', 'PromptDecision').
python_class('src/koru/autopilot/install_manager.py', 'ManagerIssue').
python_method('ManagerIssue', 'to_dict', 0, 2, 0).
python_class('src/koru/autopilot/install_manager.py', 'InstallManagerReport').
python_method('InstallManagerReport', 'to_dict', 0, 2, 1).
python_class('src/koru/bootstrap.py', 'ValidationError').
python_method('ValidationError', '__str__', 0, 1, 0).
python_class('src/koru/bootstrap.py', 'ImportReport').
python_method('ImportReport', 'summary', 0, 4, 3).
python_class('src/koru/dev_sync.py', 'SyncItem').
python_class('src/koru/doctor.py', 'Check').
python_method('Check', 'to_dict', 0, 2, 0).
python_class('src/koru/doctor.py', 'DoctorReport').
python_method('DoctorReport', 'has_failures', 0, 2, 1).
python_method('DoctorReport', 'has_warnings', 0, 2, 1).
python_method('DoctorReport', 'summary', 0, 2, 1).
python_method('DoctorReport', 'to_dict', 0, 2, 3).
python_class('src/koru/gate.py', 'GateAuthorization').
python_method('GateAuthorization', 'to_note', 0, 1, 2).
python_class('src/koru/gc.py', 'GcCandidate').
python_class('src/koru/gc.py', 'GcResult').
python_method('GcResult', 'summary', 0, 3, 3).
python_class('src/koru/ide_client.py', 'IDEControlClient').
python_method('IDEControlClient', 'is_running', 0, 1, 0).
python_method('IDEControlClient', 'drive', 1, 3, 0).
python_method('IDEControlClient', 'status', 0, 1, 0).
python_method('IDEControlClient', 'shutdown', 0, 1, 0).
python_class('src/koru/ide_client.py', 'LegacyAutopilotClientAdapter').
python_method('LegacyAutopilotClientAdapter', 'is_running', 0, 1, 2).
python_method('LegacyAutopilotClientAdapter', 'drive', 1, 3, 7).
python_method('LegacyAutopilotClientAdapter', 'status', 0, 1, 1).
python_method('LegacyAutopilotClientAdapter', 'shutdown', 0, 1, 1).
python_class('src/koru/ide_router.py', 'IDERoute').
python_class('src/koru/init.py', 'InitReport').
python_method('InitReport', '_env_bit', 0, 2, 0).
python_method('InitReport', '_lane_summary', 0, 5, 1).
python_method('InitReport', '_init_summary', 0, 9, 2).
python_method('InitReport', 'summary', 0, 2, 2).
python_class('src/koru/local_manager_client.py', 'LocalManagerClient').
python_method('LocalManagerClient', 'from_env', 1, 1, 2).
python_method('LocalManagerClient', 'enabled', 0, 1, 1).
python_method('LocalManagerClient', 'post', 2, 4, 8).
python_method('LocalManagerClient', 'register_worker', 0, 3, 4).
python_method('LocalManagerClient', 'heartbeat_worker', 0, 2, 1).
python_method('LocalManagerClient', 'claim_action', 0, 2, 1).
python_method('LocalManagerClient', 'complete_action', 0, 2, 1).
python_class('src/koru/local_manager_client.py', 'LocalManagerSession').
python_method('LocalManagerSession', 'enabled', 0, 1, 0).
python_method('LocalManagerSession', 'start', 0, 6, 6).
python_method('LocalManagerSession', 'heartbeat', 0, 1, 1).
python_method('LocalManagerSession', 'should_stop', 0, 1, 1).
python_method('LocalManagerSession', 'complete', 0, 2, 1).
python_class('src/koru/local_manager_state.py', 'EventBuffer').
python_method('EventBuffer', '__init__', 1, 1, 2).
python_method('EventBuffer', 'append', 1, 1, 1).
python_method('EventBuffer', 'snapshot', 0, 2, 1).
python_class('src/koru/local_manager_state.py', 'ActionQueue').
python_method('ActionQueue', '__init__', 1, 1, 2).
python_method('ActionQueue', 'enqueue', 3, 1, 4).
python_method('ActionQueue', 'claim', 0, 8, 15).
python_method('ActionQueue', 'complete', 0, 4, 4).
python_method('ActionQueue', 'snapshot', 0, 2, 3).
python_class('src/koru/local_manager_state.py', 'WorkerRegistry').
python_method('WorkerRegistry', '__init__', 0, 1, 1).
python_method('WorkerRegistry', 'register', 1, 14, 10).
python_method('WorkerRegistry', 'heartbeat', 1, 11, 10).
python_method('WorkerRegistry', '_reconcile_locked', 0, 9, 6).
python_method('WorkerRegistry', '_reply_locked', 1, 1, 2).
python_method('WorkerRegistry', 'snapshot', 0, 2, 2).
python_class('src/koru/local_manager_state.py', 'ServiceState').
python_method('ServiceState', '__init__', 1, 1, 3).
python_class('src/koru/local_service.py', 'LocalServiceConfig').
python_class('src/koru/loop.py', 'CommandResult').
python_class('src/koru/loop.py', 'RunRecord').
python_class('src/koru/loop.py', 'LoopReport').
python_class('src/koru/policy.py', 'Policy').
python_method('Policy', 'to_dict', 0, 1, 1).
python_class('src/koru/queue/local_manager.py', 'QueueManagerEarlyExit').
python_class('src/koru/queue/types.py', 'CommandResult').
python_class('src/koru/queue/types.py', 'QueueRunResult').
python_class('src/koru/queue/types.py', 'QueueLoopResult').
python_method('QueueLoopResult', 'ticket_id', 0, 1, 0).
python_method('QueueLoopResult', 'summary', 0, 2, 3).
python_class('src/koru/queue/types.py', 'ApiRunResult').
python_class('src/koru/queue/types.py', 'LlmRunResult').
python_class('src/koru/queue_clean.py', 'CleanupCandidate').
python_method('CleanupCandidate', 'explanation', 0, 3, 1).
python_class('src/koru/queue_clean.py', 'CleanupReport').
python_method('CleanupReport', 'to_dict', 0, 3, 2).
python_class('src/koru/run_log.py', 'RunLogWriter').
python_method('RunLogWriter', '_emit', 1, 3, 5).
python_method('RunLogWriter', 'write_header', 0, 1, 4).
python_method('RunLogWriter', 'write_iteration', 0, 3, 4).
python_method('RunLogWriter', 'write_footer', 0, 4, 6).
python_class('src/koru/scan.py', 'Suggestion').
python_method('Suggestion', 'to_dict', 0, 2, 1).
python_class('src/koru/scan.py', 'ScanResult').
python_method('ScanResult', 'to_dict', 0, 2, 2).
python_class('src/koru/semcod_tools.py', 'SemcodTool').
python_method('SemcodTool', 'to_dict', 0, 1, 0).
python_class('src/koru/tasks.py', 'CreatedTask').
python_class('src/koru/topology.py', 'ToggleResult').
python_class('src/koru/topology_cli.py', 'TopologyMutation').
python_class('src/koruapi/dashboard_serve.py', 'ServeConfig').
python_class('src/koruapi/integrations.py', 'IntegrationSpec').
python_class('src/koruapi/invoke_handlers.py', 'InvokeError').
python_class('src/koruapi/server.py', 'KoruAPIHandler').
python_method('KoruAPIHandler', 'log_message', 1, 1, 2).
python_method('KoruAPIHandler', 'do_GET', 0, 5, 8).
python_method('KoruAPIHandler', 'do_POST', 0, 2, 4).
python_class('src/koruide/audit.py', '_JSONFormatter').
python_method('_JSONFormatter', 'format', 1, 1, 1).
python_class('src/koruide/audit.py', 'AuditLog').
python_method('AuditLog', '__init__', 0, 4, 12).
python_method('AuditLog', 'record', 1, 6, 7).
python_method('AuditLog', 'close', 0, 3, 3).
python_class('src/koruide/client.py', 'KoruIDEClient').
python_method('KoruIDEClient', '__init__', 0, 2, 1).
python_method('KoruIDEClient', '_connect', 0, 1, 4).
python_method('KoruIDEClient', 'request', 1, 7, 13).
python_method('KoruIDEClient', 'is_running', 0, 4, 6).
python_method('KoruIDEClient', 'drive', 1, 4, 4).
python_method('KoruIDEClient', 'status', 0, 2, 4).
python_method('KoruIDEClient', 'shutdown', 0, 2, 4).
python_class('src/koruide/config.py', 'AutopilotConfig').
python_method('AutopilotConfig', 'submit_key_for', 1, 2, 1).
python_class('src/koruide/daemon.py', '_Client').
python_class('src/koruide/daemon.py', 'AutopilotDaemon').
python_method('AutopilotDaemon', '__init__', 0, 7, 9).
python_method('AutopilotDaemon', 'start', 0, 3, 12).
python_method('AutopilotDaemon', 'serve_forever', 0, 5, 6).
python_method('AutopilotDaemon', 'stop', 0, 1, 1).
python_method('AutopilotDaemon', '_shutdown', 0, 3, 9).
python_method('AutopilotDaemon', '_accept', 0, 6, 9).
python_method('AutopilotDaemon', '_on_readable', 1, 7, 14).
python_method('AutopilotDaemon', '_dispatch', 2, 3, 6).
python_method('AutopilotDaemon', '_send', 2, 2, 3).
python_method('AutopilotDaemon', '_drop', 1, 2, 4).
python_method('AutopilotDaemon', '_plugin_for', 1, 1, 1).
python_method('AutopilotDaemon', '_handle_drive', 2, 9, 14).
python_method('AutopilotDaemon', '_drive_via_plugin', 6, 4, 15).
python_method('AutopilotDaemon', '_try_os_injector_drive', 3, 2, 3).
python_method('AutopilotDaemon', '_drive_via_keyboard', 5, 12, 19).
python_method('AutopilotDaemon', '_handle_hello', 2, 6, 14).
python_method('AutopilotDaemon', '_log_rejected_plugin_connection', 0, 6, 8).
python_method('AutopilotDaemon', '_handle_status', 2, 5, 12).
python_method('AutopilotDaemon', '_plugin_ack_needs_os_fallback', 0, 1, 1).
python_method('AutopilotDaemon', '_relay_os_fallback_ack', 6, 3, 7).
python_method('AutopilotDaemon', '_relay_message_sent_ack', 2, 3, 9).
python_method('AutopilotDaemon', '_handle_ack', 2, 10, 14).
python_method('AutopilotDaemon', '_event_path', 0, 1, 2).
python_method('AutopilotDaemon', '_append_event', 2, 2, 6).
python_method('AutopilotDaemon', '_handle_plugin_event', 2, 15, 14).
python_method('AutopilotDaemon', '_handle_shutdown', 2, 2, 6).
python_method('AutopilotDaemon', '_handle_ping', 2, 2, 3).
python_method('AutopilotDaemon', '_build_handler_table', 0, 1, 0).
python_class('src/koruide/drive_orchestrator.py', 'DriveOrchestrator').
python_method('DriveOrchestrator', 'plugin_required_message', 1, 2, 0).
python_method('DriveOrchestrator', 'should_try_os_fallback', 0, 8, 3).
python_method('DriveOrchestrator', 'build_message_sent_info', 0, 3, 2).
python_method('DriveOrchestrator', 'annotate_plugin_ack', 0, 7, 4).
python_method('DriveOrchestrator', 'strict_plugin_ack_required', 0, 1, 3).
python_method('DriveOrchestrator', 'expected_plugin_version', 0, 5, 8).
python_method('DriveOrchestrator', 'strict_plugin_version_required', 0, 2, 3).
python_method('DriveOrchestrator', 'plugin_version_info', 0, 10, 3).
python_method('DriveOrchestrator', 'should_block_plugin_version', 1, 4, 3).
python_method('DriveOrchestrator', 'plugin_version_block_message', 1, 3, 1).
python_method('DriveOrchestrator', 'should_fail_strict_plugin_ack', 0, 6, 4).
python_method('DriveOrchestrator', 'plugin_ack_summary', 1, 8, 3).
python_class('src/koruide/ide.py', 'RunningIDE').
python_method('RunningIDE', 'to_dict', 0, 1, 0).
python_class('src/koruide/injector.py', 'BackendStatus').
python_method('BackendStatus', 'to_dict', 0, 1, 0).
python_class('src/koruide/injector.py', 'InjectionResult').
python_method('InjectionResult', 'to_dict', 0, 1, 0).
python_class('src/koruide/injector.py', 'InjectorError').
python_class('src/koruide/injector.py', 'Injector').
python_method('Injector', 'probe', 0, 1, 1).
python_method('Injector', '_candidate_backends', 0, 6, 5).
python_method('Injector', 'select_backend', 0, 2, 1).
python_method('Injector', '_type_with_backend', 3, 14, 8).
python_method('Injector', 'type_text', 1, 8, 8).
python_method('Injector', 'submit_only', 0, 5, 7).
python_method('Injector', '_probe_one', 1, 5, 2).
python_method('Injector', '_call', 1, 4, 4).
python_method('Injector', '_press_wtype', 1, 4, 5).
python_class('src/koruide/os_injector.py', 'OsInjectorError').
python_class('src/koruide/os_injector.py', 'OsInjectorProfile').
python_class('src/koruide/plugin_installer.py', 'PluginInstallResult').
python_method('PluginInstallResult', 'to_dict', 0, 5, 0).
python_class('src/koruide/plugin_router.py', 'PluginClient').
python_class('src/koruide/plugin_router.py', 'PluginStatusRow').
python_method('PluginStatusRow', 'to_dict', 0, 2, 0).
python_class('src/koruide/plugin_router.py', 'PluginRouter').
python_method('PluginRouter', '__init__', 1, 2, 0).
python_method('PluginRouter', 'plugin_for', 1, 5, 3).
python_method('PluginRouter', 'drop_stale_plugins', 2, 6, 5).
python_method('PluginRouter', 'status_rows', 0, 3, 4).
python_class('src/koruide/protocol.py', 'ProtocolError').
python_class('src/koruide/protocol.py', 'Message').
python_method('Message', 'to_dict', 0, 4, 1).
python_method('Message', 'encode', 0, 1, 3).
python_class('tests/test_agents.py', 'TestAgentDetection').
python_method('TestAgentDetection', 'test_detects_project_hints_without_cli', 0, 3, 10).
python_method('TestAgentDetection', 'test_detects_openrouter_lane_from_env', 0, 3, 9).
python_method('TestAgentDetection', 'test_select_agent_prefers_launchable_when_noninteractive', 0, 1, 7).
python_method('TestAgentDetection', 'test_detects_gemini_cli_when_available', 0, 3, 7).
python_method('TestAgentDetection', 'test_select_agent_can_pick_gemini_when_only_launchable', 0, 1, 7).
python_method('TestAgentDetection', 'test_detects_cline_when_available', 0, 3, 7).
python_method('TestAgentDetection', 'test_select_agent_can_pick_cline_when_only_launchable', 0, 1, 7).
python_method('TestAgentDetection', 'test_agent_lane_environment_cursor', 0, 1, 3).
python_method('TestAgentDetection', 'test_normalize_agent_lane_id_strips_garbage', 0, 1, 2).
python_method('TestAgentDetection', 'test_format_agent_lane_exports_is_shell_safe', 0, 1, 2).
python_method('TestAgentDetection', 'test_detects_qwen_code_when_available', 0, 3, 7).
python_method('TestAgentDetection', 'test_select_agent_can_pick_qwen_when_only_launchable', 0, 1, 7).
python_method('TestAgentDetection', 'test_detects_opencode_when_available', 0, 3, 7).
python_method('TestAgentDetection', 'test_select_agent_can_pick_opencode_when_only_launchable', 0, 1, 7).
python_class('tests/test_agents.py', 'TestAgentLaneEnv').
python_method('TestAgentLaneEnv', 'test_qwen_lane_env_defaults', 0, 1, 2).
python_method('TestAgentLaneEnv', 'test_opencode_lane_env_defaults', 0, 1, 2).
python_class('tests/test_agents.py', 'TestAutopilotBackendForLane').
python_method('TestAutopilotBackendForLane', 'test_backend_matrix', 0, 1, 2).
python_class('tests/test_autopilot_daemon.py', '_StubInjector').
python_method('_StubInjector', '__init__', 0, 2, 0).
python_method('_StubInjector', 'type_text', 1, 2, 3).
python_method('_StubInjector', 'probe', 0, 1, 0).
python_method('_StubInjector', 'select_backend', 0, 1, 0).
python_class('tests/test_autopilot_daemon.py', '_LineReader').
python_method('_LineReader', '__init__', 1, 2, 1).
python_method('_LineReader', 'read_line', 0, 4, 5).
python_method('_LineReader', 'read_message', 0, 1, 2).
python_class('tests/test_autopilot_daemon.py', '_DaemonHarness').
python_method('_DaemonHarness', '__init__', 1, 2, 2).
python_method('_DaemonHarness', 'start', 0, 1, 3).
python_method('_DaemonHarness', 'stop', 0, 2, 2).
python_method('_DaemonHarness', 'client', 1, 1, 1).
python_class('tests/test_bootstrap.py', 'TestLoadFlatPipeline').
python_method('TestLoadFlatPipeline', 'test_loads_header_and_tasks', 0, 1, 6).
python_method('TestLoadFlatPipeline', 'test_missing_file_raises', 0, 1, 2).
python_method('TestLoadFlatPipeline', 'test_missing_tasks_raises', 0, 1, 5).
python_class('tests/test_bootstrap.py', 'TestValidateFlatPipeline').
python_method('TestValidateFlatPipeline', 'test_valid_pipeline_has_no_errors', 0, 1, 3).
python_method('TestValidateFlatPipeline', 'test_missing_id_reported', 0, 1, 4).
python_method('TestValidateFlatPipeline', 'test_duplicate_id_reported', 0, 2, 4).
python_method('TestValidateFlatPipeline', 'test_invalid_executor_kind', 0, 2, 4).
python_method('TestValidateFlatPipeline', 'test_invalid_priority_reported', 0, 2, 4).
python_method('TestValidateFlatPipeline', 'test_unknown_blocked_by_reference', 0, 2, 4).
python_method('TestValidateFlatPipeline', 'test_cycle_detected', 0, 2, 4).
python_method('TestValidateFlatPipeline', '_load', 1, 1, 4).
python_class('tests/test_bootstrap.py', 'TestMaterializeToPlanfile').
python_method('TestMaterializeToPlanfile', 'test_creates_planfile_structure', 0, 1, 12).
python_method('TestMaterializeToPlanfile', 'test_default_execution_state_ready_for_unblocked', 0, 1, 8).
python_method('TestMaterializeToPlanfile', 'test_default_execution_state_pending_for_blocked', 0, 1, 8).
python_method('TestMaterializeToPlanfile', 'test_overwrite_protection', 0, 1, 7).
python_class('tests/test_bootstrap.py', 'TestImportFlatPipeline').
python_method('TestImportFlatPipeline', 'test_full_round_trip', 0, 1, 7).
python_method('TestImportFlatPipeline', 'test_invalid_pipeline_raises_value_error', 0, 1, 6).
python_class('tests/test_bootstrap.py', 'TestImportReport').
python_method('TestImportReport', 'test_summary_includes_key_facts', 0, 1, 4).
python_class('tests/test_bootstrap.py', 'TestValidationError').
python_method('TestValidationError', 'test_str_format', 0, 1, 3).
python_class('tests/test_cli.py', 'TestBareInvocation').
python_method('TestBareInvocation', '_parse', 0, 1, 3).
python_method('TestBareInvocation', 'test_no_args_is_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_project_only_is_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_init_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_init_skip_host_environment_flag', 0, 1, 3).
python_method('TestBareInvocation', 'test_init_agent_lane_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_doctor_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_context_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_queue_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_watch_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_bootstrap_is_not_bare', 0, 1, 3).
python_method('TestBareInvocation', 'test_command_is_not_bare', 0, 1, 3).
python_class('tests/test_cli.py', 'TestDoctorDispatch').
python_method('TestDoctorDispatch', 'setUp', 0, 1, 1).
python_method('TestDoctorDispatch', 'tearDown', 0, 1, 1).
python_method('TestDoctorDispatch', 'test_doctor_default_is_text', 0, 2, 5).
python_method('TestDoctorDispatch', 'test_doctor_json', 0, 1, 4).
python_method('TestDoctorDispatch', 'test_doctor_fix_text_is_guidance_only', 0, 1, 4).
python_method('TestDoctorDispatch', 'test_doctor_fix_json', 0, 1, 6).
python_method('TestDoctorDispatch', 'test_doctor_exit_0_on_no_failures', 0, 1, 3).
python_class('tests/test_cli.py', 'TestInitDispatch').
python_method('TestInitDispatch', 'setUp', 0, 1, 1).
python_method('TestInitDispatch', 'tearDown', 0, 1, 1).
python_method('TestInitDispatch', 'test_init_creates_planfile', 0, 1, 6).
python_method('TestInitDispatch', 'test_init_duplicate_rejected', 0, 1, 3).
python_method('TestInitDispatch', 'test_init_agent_lane_none_skips_helpers', 0, 1, 7).
python_class('tests/test_cli.py', 'TestInitAgentLaneDispatch').
python_method('TestInitAgentLaneDispatch', 'setUp', 0, 1, 1).
python_method('TestInitAgentLaneDispatch', 'tearDown', 0, 1, 1).
python_method('TestInitAgentLaneDispatch', 'test_fails_without_planfile', 0, 1, 4).
python_method('TestInitAgentLaneDispatch', 'test_ok_when_planfile_exists', 0, 1, 5).
python_class('tests/test_cli.py', 'TestContextDispatch').
python_method('TestContextDispatch', 'setUp', 0, 1, 1).
python_method('TestContextDispatch', 'tearDown', 0, 1, 1).
python_method('TestContextDispatch', 'test_context_json_default', 0, 1, 5).
python_method('TestContextDispatch', 'test_context_markdown', 0, 1, 4).
python_class('tests/test_cli.py', 'TestBareEmitsMarkdown').
python_method('TestBareEmitsMarkdown', 'setUp', 0, 1, 1).
python_method('TestBareEmitsMarkdown', 'tearDown', 0, 1, 1).
python_method('TestBareEmitsMarkdown', 'test_bare_produces_markdown', 0, 1, 4).
python_class('tests/test_cli.py', 'TestTopologySubcommand').
python_method('TestTopologySubcommand', 'setUp', 0, 1, 2).
python_method('TestTopologySubcommand', 'tearDown', 0, 1, 1).
python_method('TestTopologySubcommand', 'test_topology_json_lists_components_and_pipelines', 0, 1, 5).
python_method('TestTopologySubcommand', 'test_topology_disable_then_is_enabled_false', 0, 1, 4).
python_method('TestTopologySubcommand', 'test_topology_enabled_components_for_pipeline', 0, 1, 5).
python_class('tests/test_cli.py', 'TestInitCiSubcommand').
python_method('TestInitCiSubcommand', 'test_init_ci_exits_zero_with_paths', 0, 1, 3).
python_class('tests/test_cli.py', 'TestAutoMain').
python_method('TestAutoMain', 'test_auto_main_stops_prior_and_injects_replace_existing', 0, 1, 11).
python_method('TestAutoMain', 'test_auto_main_allow_duplicate_skips_stop_and_replace_flag', 0, 2, 8).
python_method('TestAutoMain', 'test_subcommand_auto_routes_to_auto_main', 0, 1, 4).
python_method('TestAutoMain', 'test_auto_main_help_does_not_stop_existing_loop', 0, 1, 5).
python_class('tests/test_cli.py', 'TestSubcommandDispatch').
python_method('TestSubcommandDispatch', 'test_table_contains_all_documented_subcommands', 0, 1, 3).
python_method('TestSubcommandDispatch', 'test_table_values_are_callables', 0, 2, 3).
python_method('TestSubcommandDispatch', 'test_each_subcommand_routes_to_its_handler', 0, 2, 7).
python_method('TestSubcommandDispatch', 'test_unknown_first_arg_falls_through_to_argparse', 0, 3, 7).
python_method('TestSubcommandDispatch', 'test_empty_argv_does_not_call_any_handler', 0, 2, 6).
python_class('tests/test_context.py', 'TestBuildContext').
python_method('TestBuildContext', 'test_brief_with_runnable_ticket', 0, 1, 8).
python_method('TestBuildContext', 'test_autonomy_loop_brief_reads_telemetry_file', 0, 2, 12).
python_method('TestBuildContext', 'test_brief_when_queue_idle', 0, 1, 9).
python_method('TestBuildContext', 'test_no_active_ticket_brief_compacts_traceback_error', 0, 1, 3).
python_method('TestBuildContext', 'test_brief_when_queue_idle_ticket_next_json_null', 0, 1, 9).
python_method('TestBuildContext', 'test_brief_when_planfile_errors', 0, 1, 8).
python_method('TestBuildContext', 'test_specific_ticket_uses_show', 0, 4, 9).
python_method('TestBuildContext', 'test_instructions_include_no_commit_rule', 0, 1, 9).
python_method('TestBuildContext', 'test_instructions_include_ci_command_when_set', 0, 1, 9).
python_method('TestBuildContext', 'test_self_service_includes_concrete_ticket_commands', 0, 1, 10).
python_method('TestBuildContext', 'test_brief_is_json_serialisable', 0, 1, 7).
python_method('TestBuildContext', 'test_files_in_scope_appear_in_instructions', 0, 1, 8).
python_method('TestBuildContext', 'test_fixture_tickets_are_skipped_by_default', 0, 1, 8).
python_method('TestBuildContext', 'test_real_ticket_picked_over_fixture_in_mixed_queue', 0, 1, 8).
python_method('TestBuildContext', 'test_include_fixtures_flag_brings_them_back', 0, 1, 8).
python_method('TestBuildContext', 'test_single_object_fixture_is_filtered', 0, 2, 8).
python_method('TestBuildContext', 'test_explicit_ticket_id_bypasses_fixture_filter', 0, 1, 8).
python_method('TestBuildContext', 'test_all_tickets_are_populated_from_list', 0, 4, 12).
python_class('tests/test_context.py', 'TestMarkdownHandoff').
python_method('TestMarkdownHandoff', 'test_renders_ticket_section', 0, 1, 8).
python_method('TestMarkdownHandoff', 'test_renders_policy_table', 0, 1, 8).
python_method('TestMarkdownHandoff', 'test_renders_idle_brief_without_crash', 0, 1, 7).
python_class('tests/test_context.py', 'TestProjectPipelineInHandoff').
python_method('TestProjectPipelineInHandoff', 'test_context_includes_pipeline_when_koru_yaml_present', 0, 2, 12).
python_method('TestProjectPipelineInHandoff', 'test_pipeline_absent_without_koru_yaml', 0, 1, 7).
python_class('tests/test_context.py', 'TestSetupRequired').
python_method('TestSetupRequired', 'test_instructions_swap_to_setup_guide', 0, 1, 8).
python_method('TestSetupRequired', 'test_self_service_exposes_init_only', 0, 1, 6).
python_method('TestSetupRequired', 'test_environment_planfile_initialised_false', 0, 1, 5).
python_method('TestSetupRequired', 'test_markdown_renders_setup_required_block', 0, 1, 6).
python_class('tests/test_docker_e2e.py', 'TestDockerE2E').
python_method('TestDockerE2E', 'docker_image', 0, 3, 9).
python_method('TestDockerE2E', 'test_project', 1, 3, 5).
python_method('TestDockerE2E', 'test_docker_image_builds_successfully', 1, 3, 2).
python_method('TestDockerE2E', 'test_koru_help_in_docker', 1, 3, 2).
python_method('TestDockerE2E', 'test_koru_doctor_in_docker', 1, 3, 3).
python_method('TestDockerE2E', 'test_koru_init_in_docker', 1, 4, 4).
python_method('TestDockerE2E', 'test_task_creation_with_priority_in_docker', 2, 13, 7).
python_method('TestDockerE2E', 'test_autonomous_mode_single_cycle_in_docker', 2, 4, 1).
python_method('TestDockerE2E', 'test_priority_ordering_in_docker', 2, 5, 1).
python_method('TestDockerE2E', 'test_external_tool_detection_in_docker', 1, 6, 1).
python_method('TestDockerE2E', 'test_agent_detection_in_docker', 1, 5, 3).
python_method('TestDockerE2E', 'test_full_workflow_in_docker', 2, 24, 13).
python_class('tests/test_docker_e2e.py', 'TestDockerComposeIntegration').
python_method('TestDockerComposeIntegration', 'test_docker_compose_build', 0, 2, 2).
python_method('TestDockerComposeIntegration', 'test_docker_compose_test_profile', 0, 11, 4).
python_method('TestDockerComposeIntegration', 'test_docker_compose_deps_profile', 0, 9, 4).
python_class('tests/test_doctor.py', 'TestHappyPath').
python_method('TestHappyPath', 'test_full_scaffold_passes_all_required_checks', 0, 1, 11).
python_class('tests/test_doctor.py', 'TestKoruProjectPipelineProbe').
python_method('TestKoruProjectPipelineProbe', 'test_warns_when_planfile_ok_but_koru_yaml_missing', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestPlanfileCliVersionProbe').
python_method('TestPlanfileCliVersionProbe', 'test_parses_version_from_stderr', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestAutonomousEnvironDoctorIntegration').
python_method('TestAutonomousEnvironDoctorIntegration', 'test_doctor_includes_autonomous_environ_check', 0, 1, 9).
python_method('TestAutonomousEnvironDoctorIntegration', 'test_doctor_fails_on_invalid_ticket_sources_env', 0, 1, 9).
python_method('TestAutonomousEnvironDoctorIntegration', 'test_warns_when_no_git', 0, 1, 8).
python_class('tests/test_doctor.py', 'TestPlanfileBinary').
python_method('TestPlanfileBinary', 'test_explicit_env_var_resolves', 0, 1, 10).
python_method('TestPlanfileBinary', 'test_missing_binary_fails', 0, 3, 9).
python_class('tests/test_doctor.py', 'TestPlanfileConfigCheck').
python_method('TestPlanfileConfigCheck', 'test_missing_config_fails', 0, 1, 8).
python_method('TestPlanfileConfigCheck', 'test_malformed_config_fails', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestSprintsCheck').
python_method('TestSprintsCheck', 'test_empty_sprint_warns', 0, 1, 7).
python_method('TestSprintsCheck', 'test_no_sprints_dir_fails', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestPolicyYamlCheck').
python_method('TestPolicyYamlCheck', 'test_absent_policy_passes', 0, 1, 6).
python_method('TestPolicyYamlCheck', 'test_malformed_policy_fails', 0, 1, 7).
python_method('TestPolicyYamlCheck', 'test_string_truthy_value_warns', 0, 1, 8).
python_class('tests/test_doctor.py', 'TestGitignoreCheck').
python_method('TestGitignoreCheck', 'test_warns_when_runtime_not_ignored', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestCiCommandCheck').
python_method('TestCiCommandCheck', 'test_empty_warns', 0, 1, 6).
python_method('TestCiCommandCheck', 'test_resolved_passes', 0, 1, 7).
python_class('tests/test_doctor.py', 'TestPytestCollectProbe').
python_method('TestPytestCollectProbe', '_scaffold_with_pyproject', 1, 1, 2).
python_method('TestPytestCollectProbe', 'test_pass_when_collection_succeeds_with_count', 0, 1, 9).
python_method('TestPytestCollectProbe', 'test_pass_when_count_not_parseable', 0, 1, 8).
python_method('TestPytestCollectProbe', 'test_warn_when_zero_tests_collected', 0, 1, 9).
python_method('TestPytestCollectProbe', 'test_warn_when_collection_errors', 0, 1, 9).
python_method('TestPytestCollectProbe', 'test_fail_when_collection_times_out', 0, 1, 10).
python_method('TestPytestCollectProbe', 'test_skip_when_pytest_not_installed', 0, 1, 8).
python_method('TestPytestCollectProbe', 'test_probe_skipped_entirely_when_no_pyproject_and_no_tests', 0, 2, 5).
python_method('TestPytestCollectProbe', 'test_env_var_overrides_timeout', 0, 1, 3).
python_class('tests/test_doctor.py', 'TestReportShape').
python_method('TestReportShape', 'test_to_dict_keys_stable', 0, 2, 7).
python_method('TestReportShape', 'test_render_text_groups_status', 0, 1, 7).
python_method('TestReportShape', 'test_summary_counts_match_checks', 0, 1, 9).
python_class('tests/test_doctor.py', 'TestWupAndInotifyProbes').
python_method('TestWupAndInotifyProbes', 'test_inotify_watches_non_linux_skipped', 0, 1, 5).
python_method('TestWupAndInotifyProbes', 'test_inotify_watches_linux_low_limit_fails', 0, 1, 5).
python_method('TestWupAndInotifyProbes', 'test_inotify_watches_linux_high_limit_passes', 0, 1, 5).
python_method('TestWupAndInotifyProbes', 'test_wup_binary_missing_warns', 0, 1, 5).
python_method('TestWupAndInotifyProbes', 'test_wup_binary_present_passes', 0, 1, 5).
python_class('tests/test_dotenv_loader.py', 'TestParseDotenv').
python_method('TestParseDotenv', 'test_simple_pairs', 0, 1, 2).
python_method('TestParseDotenv', 'test_export_prefix_supported', 0, 1, 2).
python_method('TestParseDotenv', 'test_double_quoted_with_escapes', 0, 1, 2).
python_method('TestParseDotenv', 'test_single_quoted_literal', 0, 1, 2).
python_method('TestParseDotenv', 'test_inline_comments_stripped', 0, 1, 2).
python_method('TestParseDotenv', 'test_skips_blank_and_comment_lines', 0, 1, 2).
python_method('TestParseDotenv', 'test_invalid_lines_silently_skipped', 0, 1, 2).
python_method('TestParseDotenv', 'test_openrouter_realworld_line', 0, 1, 2).
python_class('tests/test_dotenv_loader.py', 'TestLoadDotenv').
python_method('TestLoadDotenv', 'setUp', 0, 1, 1).
python_method('TestLoadDotenv', 'tearDown', 0, 1, 2).
python_method('TestLoadDotenv', 'test_no_dotenv_returns_empty', 0, 1, 4).
python_method('TestLoadDotenv', 'test_loads_keys_into_environ', 0, 1, 7).
python_method('TestLoadDotenv', 'test_does_not_override_existing_env', 0, 1, 5).
python_method('TestLoadDotenv', 'test_override_flag_replaces_existing', 0, 1, 5).
python_method('TestLoadDotenv', 'test_env_local_overrides_env', 0, 1, 6).
python_method('TestLoadDotenv', 'test_openrouter_key_propagated', 0, 1, 7).
python_class('tests/test_e2e.py', 'TestE2EInitDoctorContext').
python_method('TestE2EInitDoctorContext', 'setUp', 0, 1, 1).
python_method('TestE2EInitDoctorContext', 'tearDown', 0, 1, 1).
python_method('TestE2EInitDoctorContext', 'test_init_then_doctor_passes', 0, 1, 7).
python_method('TestE2EInitDoctorContext', 'test_init_then_bare_koru_emits_markdown', 0, 1, 5).
python_method('TestE2EInitDoctorContext', 'test_init_then_context_json_has_policy', 0, 1, 6).
python_method('TestE2EInitDoctorContext', 'test_init_then_context_markdown_has_ticket', 0, 1, 5).
python_method('TestE2EInitDoctorContext', 'test_doctor_json_format', 0, 1, 6).
python_method('TestE2EInitDoctorContext', 'test_doctor_fails_on_empty_project', 0, 1, 3).
python_method('TestE2EInitDoctorContext', 'test_double_init_rejected', 0, 1, 2).
python_class('tests/test_e2e.py', 'TestE2ETask').
python_method('TestE2ETask', 'setUp', 0, 1, 2).
python_method('TestE2ETask', 'tearDown', 0, 1, 1).
python_method('TestE2ETask', 'test_task_creates_ticket', 0, 2, 13).
python_method('TestE2ETask', 'test_task_increments_id', 0, 3, 8).
python_method('TestE2ETask', 'test_task_empty_text_fails', 0, 1, 3).
python_method('TestE2ETask', 'test_task_with_priority', 0, 3, 8).
python_method('TestE2ETask', 'test_task_with_tool_scaffold', 0, 4, 9).
python_method('TestE2ETask', 'test_task_with_plugin_bridge_scaffold', 0, 4, 9).
python_class('tests/test_e2e.py', 'TestE2EGc').
python_method('TestE2EGc', 'setUp', 0, 1, 5).
python_method('TestE2EGc', 'tearDown', 0, 1, 1).
python_method('TestE2EGc', 'test_gc_dry_run_text', 0, 1, 5).
python_method('TestE2EGc', 'test_gc_dry_run_json', 0, 1, 7).
python_method('TestE2EGc', 'test_gc_keep_last_protects_newest', 0, 1, 4).
python_method('TestE2EGc', 'test_gc_custom_statuses', 0, 1, 5).
python_method('TestE2EGc', 'test_gc_no_stale_tickets_message', 0, 1, 4).
python_method('TestE2EGc', 'test_gc_apply_with_fake_runner', 0, 1, 6).
python_class('tests/test_e2e.py', 'TestE2EScan').
python_method('TestE2EScan', 'setUp', 0, 1, 2).
python_method('TestE2EScan', 'tearDown', 0, 1, 1).
python_method('TestE2EScan', '_marker_fixture', 0, 2, 1).
python_method('TestE2EScan', 'test_scan_detects_todo_markers', 0, 1, 6).
python_method('TestE2EScan', 'test_scan_json_format', 0, 1, 7).
python_method('TestE2EScan', 'test_scan_with_limit', 0, 2, 8).
python_method('TestE2EScan', 'test_scan_clean_project_no_suggestions', 0, 3, 6).
python_class('tests/test_e2e.py', 'TestE2EQueueLoop').
python_method('TestE2EQueueLoop', 'setUp', 0, 1, 3).
python_method('TestE2EQueueLoop', 'tearDown', 0, 1, 1).
python_method('TestE2EQueueLoop', 'test_queue_dry_run', 0, 1, 4).
python_method('TestE2EQueueLoop', 'test_queue_processes_next_ticket', 0, 2, 5).
python_method('TestE2EQueueLoop', 'test_queue_idle_when_no_runnable_tickets', 0, 1, 6).
python_class('tests/test_e2e.py', 'TestE2EQueueLoopMode').
python_method('TestE2EQueueLoopMode', 'setUp', 0, 1, 3).
python_method('TestE2EQueueLoopMode', 'tearDown', 0, 1, 1).
python_method('TestE2EQueueLoopMode', 'test_loop_finds_and_processes_tickets', 0, 1, 4).
python_method('TestE2EQueueLoopMode', 'test_loop_reports_completed_count', 0, 1, 4).
python_class('tests/test_e2e.py', 'TestE2EBootstrap').
python_method('TestE2EBootstrap', 'setUp', 0, 1, 3).
python_method('TestE2EBootstrap', 'tearDown', 0, 1, 1).
python_method('TestE2EBootstrap', 'test_bootstrap_creates_planfile_structure', 0, 1, 6).
python_method('TestE2EBootstrap', 'test_bootstrap_ticket_count', 0, 1, 6).
python_method('TestE2EBootstrap', 'test_bootstrap_rejects_without_force', 0, 1, 4).
python_method('TestE2EBootstrap', 'test_bootstrap_force_overwrites', 0, 1, 4).
python_class('tests/test_e2e.py', 'TestE2EGate').
python_method('TestE2EGate', 'setUp', 0, 1, 3).
python_method('TestE2EGate', 'tearDown', 0, 1, 1).
python_method('TestE2EGate', 'test_gate_authorize_dry_run', 0, 1, 3).
python_method('TestE2EGate', 'test_gate_authorize_json_format', 0, 2, 5).
python_class('tests/test_e2e.py', 'TestE2EFullLifecycle').
python_method('TestE2EFullLifecycle', 'setUp', 0, 1, 1).
python_method('TestE2EFullLifecycle', 'tearDown', 0, 1, 1).
python_method('TestE2EFullLifecycle', 'test_full_lifecycle', 0, 1, 6).
python_class('tests/test_e2e.py', 'TestE2EInitFromPipeline').
python_method('TestE2EInitFromPipeline', 'setUp', 0, 1, 3).
python_method('TestE2EInitFromPipeline', 'tearDown', 0, 1, 1).
python_method('TestE2EInitFromPipeline', 'test_init_from_custom_pipeline', 0, 2, 12).
python_class('tests/test_e2e.py', 'TestE2EHumanTicket').
python_method('TestE2EHumanTicket', 'setUp', 0, 1, 3).
python_method('TestE2EHumanTicket', 'tearDown', 0, 1, 1).
python_method('TestE2EHumanTicket', 'test_human_ticket_returns_waiting_input', 0, 1, 4).
python_class('tests/test_e2e.py', 'TestE2EContextFixtureFiltering').
python_method('TestE2EContextFixtureFiltering', 'setUp', 0, 1, 5).
python_method('TestE2EContextFixtureFiltering', 'tearDown', 0, 1, 1).
python_method('TestE2EContextFixtureFiltering', 'test_context_without_fixtures_skips_synthetic', 0, 2, 6).
python_method('TestE2EContextFixtureFiltering', 'test_context_with_fixtures_includes_all', 0, 1, 3).
python_class('tests/test_events.py', 'FakeResponse').
python_method('FakeResponse', '__enter__', 0, 1, 0).
python_method('FakeResponse', '__exit__', 0, 1, 0).
python_class('tests/test_events.py', 'TestManagementEvents').
python_method('TestManagementEvents', 'test_emit_management_event_posts_expected_payload', 0, 1, 8).
python_method('TestManagementEvents', 'test_emit_management_event_is_disabled_without_url', 0, 1, 3).
python_class('tests/test_gc.py', 'TestCollectGcCandidates').
python_method('TestCollectGcCandidates', 'test_finds_old_done_tickets', 0, 2, 7).
python_method('TestCollectGcCandidates', 'test_includes_failed_and_blocked', 0, 2, 6).
python_method('TestCollectGcCandidates', 'test_no_candidates_when_all_recent', 0, 1, 6).
python_method('TestCollectGcCandidates', 'test_missing_timestamp_treated_as_old', 0, 1, 7).
python_method('TestCollectGcCandidates', 'test_empty_sprint', 0, 1, 5).
python_method('TestCollectGcCandidates', 'test_custom_statuses', 0, 2, 8).
python_class('tests/test_gc.py', 'TestRunGc').
python_method('TestRunGc', 'test_dry_run_does_not_delete', 0, 1, 10).
python_method('TestRunGc', 'test_keep_last_protects_recent', 0, 1, 6).
python_method('TestRunGc', 'test_keep_last_larger_than_candidates_keeps_all', 0, 1, 6).
python_method('TestRunGc', 'test_apply_calls_planfile_delete', 0, 2, 13).
python_method('TestRunGc', 'test_apply_creates_archive', 0, 1, 15).
python_method('TestRunGc', 'test_no_archive_flag', 0, 1, 7).
python_method('TestRunGc', 'test_no_candidates_returns_empty_result', 0, 1, 6).
python_method('TestRunGc', 'test_delete_failure_records_error', 0, 1, 9).
python_method('TestRunGc', 'test_summary_string', 0, 1, 3).
python_class('tests/test_ide_client_contract.py', '_TransportStub').
python_method('_TransportStub', '__init__', 0, 1, 0).
python_method('_TransportStub', 'is_running', 0, 1, 1).
python_method('_TransportStub', 'drive', 1, 1, 2).
python_method('_TransportStub', 'status', 0, 1, 1).
python_method('_TransportStub', 'shutdown', 0, 1, 1).
python_class('tests/test_ide_work.py', 'TestIdeWork').
python_method('TestIdeWork', 'test_fetch_next_open_ticket_sorts_by_priority', 0, 2, 6).
python_method('TestIdeWork', 'test_resolve_idle_drive_prompt_uses_ticket_when_open', 0, 1, 7).
python_method('TestIdeWork', 'test_resolve_idle_drive_prompt_falls_back_when_no_open', 0, 1, 5).
python_method('TestIdeWork', 'test_release_stale_in_progress_reopens_old_ticket', 0, 3, 10).
python_method('TestIdeWork', 'test_extract_ticket_id_from_text', 0, 1, 3).
python_method('TestIdeWork', 'test_build_ide_work_prompt_includes_description', 0, 1, 2).
python_class('tests/test_init.py', 'TestStarterInit').
python_method('TestStarterInit', 'test_creates_planfile_layout', 0, 1, 7).
python_method('TestStarterInit', 'test_writes_policy_stub_and_loads_safe_defaults', 0, 1, 11).
python_method('TestStarterInit', 'test_policy_stub_constant_is_valid_yaml', 0, 1, 3).
python_method('TestStarterInit', 'test_appends_gitignore_entry', 0, 1, 5).
python_method('TestStarterInit', 'test_gitignore_idempotent', 0, 1, 6).
python_method('TestStarterInit', 'test_preserves_existing_gitignore_content', 0, 1, 6).
python_method('TestStarterInit', 'test_policy_stub_not_overwritten_on_force', 0, 1, 7).
python_method('TestStarterInit', 'test_no_starter_yaml_left_behind', 0, 1, 6).
python_method('TestStarterInit', 'test_writes_koru_yaml_on_first_init', 0, 1, 10).
python_method('TestStarterInit', 'test_host_environment_bundle_written_by_default', 0, 1, 6).
python_method('TestStarterInit', 'test_host_environment_skipped_when_disabled', 0, 1, 6).
python_method('TestStarterInit', 'test_force_init_preserves_existing_koru_yaml', 0, 1, 8).
python_class('tests/test_init.py', 'TestForceAndConflicts').
python_method('TestForceAndConflicts', 'test_re_init_without_force_raises', 0, 1, 4).
python_method('TestForceAndConflicts', 'test_re_init_with_force_succeeds', 0, 1, 4).
python_class('tests/test_init.py', 'TestFromExternalPipeline').
python_method('TestFromExternalPipeline', 'test_imports_user_supplied_pipeline', 0, 1, 9).
python_class('tests/test_init.py', 'TestRuntimeContract').
python_method('TestRuntimeContract', 'test_init_does_not_leave_files_outside_planfile', 0, 2, 6).
python_class('tests/test_init.py', 'TestAgentLaneArtifacts').
python_method('TestAgentLaneArtifacts', 'test_auto_local_writes_shell_helpers', 0, 1, 8).
python_method('TestAgentLaneArtifacts', 'test_auto_cursor_when_dot_cursor', 0, 1, 10).
python_method('TestAgentLaneArtifacts', 'test_auto_vscode_when_dot_vscode', 0, 1, 7).
python_method('TestAgentLaneArtifacts', 'test_auto_cursor_beats_vscode_when_both', 0, 1, 7).
python_method('TestAgentLaneArtifacts', 'test_auto_prefers_persisted_shell_env_lane', 0, 1, 8).
python_method('TestAgentLaneArtifacts', 'test_auto_ci_forces_local_even_with_dot_cursor', 0, 2, 7).
python_method('TestAgentLaneArtifacts', 'test_none_skips_helpers', 0, 1, 7).
python_class('tests/test_init.py', 'TestRefreshInitAgentLane').
python_method('TestRefreshInitAgentLane', 'test_requires_planfile', 0, 1, 6).
python_method('TestRefreshInitAgentLane', 'test_writes_after_init_with_agent_lane_none', 0, 1, 10).
python_class('tests/test_loop.py', 'TestKoruLoop').
python_method('TestKoruLoop', 'test_search_root_for_include_uses_literal_prefix', 0, 1, 3).
python_method('TestKoruLoop', 'test_discover_repositories_with_pattern', 0, 1, 6).
python_method('TestKoruLoop', 'test_run_closed_loop_retries_failed_repositories', 0, 1, 7).
python_method('TestKoruLoop', 'test_run_closed_loop_single_round_when_all_succeed', 0, 1, 7).
python_method('TestKoruLoop', 'test_command_value_rejects_blank_value', 0, 1, 2).
python_class('tests/test_planfile_queue.py', 'TestPlanfileCommand').
python_method('TestPlanfileCommand', 'test_falls_back_to_path_cli_when_module_cli_missing', 0, 1, 8).
python_method('TestPlanfileCommand', 'test_module_cli_probe_treats_missing_parent_as_missing', 0, 1, 8).
python_class('tests/test_planfile_queue.py', 'TestPlanfileQueue').
python_method('TestPlanfileQueue', 'test_shell_ticket_runs_lifecycle_commands', 0, 7, 16).
python_method('TestPlanfileQueue', 'test_ticket_claim_failure_returns_claim_failed', 0, 1, 8).
python_method('TestPlanfileQueue', 'test_human_ticket_returns_waiting_input', 0, 1, 7).
python_method('TestPlanfileQueue', 'test_shell_failure_marks_ticket_failed', 0, 3, 11).
python_method('TestPlanfileQueue', 'test_api_ticket_runs_lifecycle_commands', 0, 2, 12).
python_method('TestPlanfileQueue', 'test_api_failure_marks_ticket_failed', 0, 3, 11).
python_method('TestPlanfileQueue', 'test_idle_when_planfile_returns_no_ticket', 0, 1, 6).
python_method('TestPlanfileQueue', 'test_planfile_error_propagates', 0, 1, 5).
python_method('TestPlanfileQueue', 'test_dry_run_returns_command_without_executing', 0, 1, 8).
python_method('TestPlanfileQueue', 'test_unsupported_executor_kind', 0, 1, 7).
python_method('TestPlanfileQueue', 'test_shell_ticket_without_command_auto_completes', 0, 2, 10).
python_method('TestPlanfileQueue', 'test_scan_ticket_without_executor_waits_for_ide_prompt', 0, 1, 8).
python_method('TestPlanfileQueue', 'test_api_ticket_without_endpoint_requests_input', 0, 3, 10).
python_method('TestPlanfileQueue', 'test_interactive_human_ticket_completes_with_answer', 0, 2, 11).
python_method('TestPlanfileQueue', 'test_interactive_human_ticket_cancellation_leaves_ticket', 0, 2, 9).
python_method('TestPlanfileQueue', 'test_interactive_with_dry_run_does_not_prompt', 0, 1, 7).
python_class('tests/test_planfile_queue.py', 'TestPlanfileQueueLlm').
python_method('TestPlanfileQueueLlm', '_llm_ticket', 0, 2, 0).
python_method('TestPlanfileQueueLlm', 'test_llm_ticket_runs_lifecycle_commands', 0, 2, 13).
python_method('TestPlanfileQueueLlm', 'test_llm_ticket_failure_marks_failed', 0, 4, 12).
python_method('TestPlanfileQueueLlm', 'test_llm_ticket_without_prompt_requests_input', 0, 3, 11).
python_method('TestPlanfileQueueLlm', 'test_llm_dry_run_returns_request_without_calling', 0, 1, 10).
python_method('TestPlanfileQueueLlm', 'test_llm_default_runner_without_api_key_returns_clear_error', 0, 4, 6).
python_class('tests/test_planfile_queue.py', 'TestPlanfileQueueLoop').
python_method('TestPlanfileQueueLoop', '_make_runner', 1, 1, 5).
python_method('TestPlanfileQueueLoop', 'test_loop_drains_three_shell_tickets_to_idle', 0, 1, 8).
python_method('TestPlanfileQueueLoop', 'test_loop_breaks_on_waiting_input_without_interactive', 0, 1, 6).
python_method('TestPlanfileQueueLoop', 'test_loop_continues_past_failed_ticket', 0, 1, 6).
python_method('TestPlanfileQueueLoop', 'test_loop_respects_max_iterations_cap', 0, 2, 9).
python_method('TestPlanfileQueueLoop', 'test_loop_stop_callback_drains_after_current_iteration', 0, 1, 6).
python_method('TestPlanfileQueueLoop', 'test_loop_with_interactive_drains_human_tickets', 0, 1, 6).
python_method('TestPlanfileQueueLoop', 'test_loop_validates_max_iterations', 0, 1, 4).
python_class('tests/test_planfile_queue.py', 'TestAppendShellEvidenceNote').
python_method('TestAppendShellEvidenceNote', 'test_short_flag_when_long_option_unsupported', 0, 3, 9).
python_method('TestAppendShellEvidenceNote', 'test_artifact_when_both_note_flags_missing', 0, 1, 13).
python_class('tests/test_plugin_router.py', '_Sock').
python_method('_Sock', 'fileno', 0, 1, 0).
python_class('tests/test_plugin_router.py', '_Client').
python_method('_Client', '__post_init__', 0, 1, 1).
python_class('tests/test_policy.py', 'TestDefaults').
python_method('TestDefaults', 'test_defaults_are_strict', 0, 1, 4).
python_method('TestDefaults', 'test_default_forbidden_paths_include_critical', 0, 2, 2).
python_method('TestDefaults', 'test_default_shell_patterns_include_critical', 0, 2, 2).
python_method('TestDefaults', 'test_to_dict_keys_are_sorted', 0, 1, 6).
python_class('tests/test_policy.py', 'TestLoad').
python_method('TestLoad', 'test_missing_file_returns_defaults', 0, 1, 5).
python_method('TestLoad', 'test_malformed_yaml_falls_back_to_defaults', 0, 1, 5).
python_method('TestLoad', 'test_top_level_non_mapping_falls_back_to_defaults', 0, 1, 5).
python_method('TestLoad', 'test_string_truthy_value_is_rejected', 0, 1, 5).
python_method('TestLoad', 'test_explicit_loosening_is_honoured', 0, 1, 8).
python_method('TestLoad', 'test_zero_or_negative_timeout_falls_back_to_default', 0, 1, 5).
python_method('TestLoad', 'test_unknown_keys_are_ignored', 0, 1, 5).
python_class('tests/test_policy.py', 'TestViolations').
python_method('TestViolations', 'test_git_commit_blocked_by_default', 0, 1, 5).
python_method('TestViolations', 'test_git_push_blocked_by_default', 0, 2, 4).
python_method('TestViolations', 'test_force_push_double_flag', 0, 3, 6).
python_method('TestViolations', 'test_branch_create_blocked', 0, 2, 4).
python_method('TestViolations', 'test_rm_rf_root_blocked', 0, 2, 4).
python_method('TestViolations', 'test_safe_command_passes', 0, 1, 3).
python_method('TestViolations', 'test_empty_command_passes', 0, 1, 3).
python_method('TestViolations', 'test_loosened_policy_allows_commit', 0, 1, 3).
python_method('TestViolations', 'test_path_helper_resolves', 0, 1, 5).
python_class('tests/test_post_run_verify.py', '_State').
python_class('tests/test_post_run_verify.py', 'TestPostRunVerify').
python_method('TestPostRunVerify', 'test_load_from_koru_yaml', 0, 2, 6).
python_method('TestPostRunVerify', 'test_verify_reopens_on_failure', 0, 3, 13).
python_method('TestPostRunVerify', 'test_verify_after_ide_work_pending_done', 0, 1, 11).
python_method('TestPostRunVerify', 'test_fetch_recently_done_ticket_ids', 0, 1, 8).
python_method('TestPostRunVerify', 'test_run_verify_commands_success', 0, 1, 6).
python_class('tests/test_queue_cli_helpers.py', 'FakeLocalManagerClient').
python_method('FakeLocalManagerClient', '__init__', 0, 1, 0).
python_method('FakeLocalManagerClient', 'register_worker', 0, 1, 1).
python_method('FakeLocalManagerClient', 'claim_action', 0, 1, 1).
python_method('FakeLocalManagerClient', 'heartbeat_worker', 0, 1, 1).
python_method('FakeLocalManagerClient', 'complete_action', 0, 1, 1).
python_class('tests/test_run_log.py', 'TestOpenRunLog').
python_method('TestOpenRunLog', 'test_constructor_does_not_create_file', 0, 1, 8).
python_method('TestOpenRunLog', 'test_eager_creates_runs_dir_only', 0, 1, 10).
python_method('TestOpenRunLog', 'test_path_is_under_planfile_dot_koru_runs', 0, 1, 8).
python_class('tests/test_run_log.py', 'TestWriteEvents').
python_method('TestWriteEvents', 'test_header_iteration_footer_round_trip', 0, 2, 16).
python_method('TestWriteEvents', 'test_each_line_is_json', 0, 2, 9).
python_method('TestWriteEvents', 'test_keys_are_sorted_in_output', 0, 1, 12).
python_method('TestWriteEvents', 'test_message_truncation_500_chars', 0, 1, 10).
python_class('tests/test_run_log.py', 'TestErrorTolerance').
python_method('TestErrorTolerance', 'test_io_error_does_not_propagate', 0, 1, 7).
python_class('tests/test_runtime.py', 'TestPathHelpers').
python_method('TestPathHelpers', 'test_planfile_dir_is_under_project', 0, 1, 5).
python_method('TestPathHelpers', 'test_runtime_dir_is_under_planfile', 0, 1, 5).
python_method('TestPathHelpers', 'test_runs_dir_is_under_runtime_dir', 0, 1, 5).
python_method('TestPathHelpers', 'test_path_helpers_do_not_create_directories', 0, 1, 8).
python_method('TestPathHelpers', 'test_path_helpers_resolve_relative_input', 0, 1, 5).
python_class('tests/test_runtime.py', 'TestRunIdGenerator').
python_method('TestRunIdGenerator', 'test_run_id_format', 0, 1, 2).
python_method('TestRunIdGenerator', 'test_run_id_custom_prefix', 0, 1, 3).
python_method('TestRunIdGenerator', 'test_run_ids_sort_chronologically', 0, 1, 3).
python_method('TestRunIdGenerator', 'test_run_id_does_not_contain_path_separators', 0, 1, 4).
python_class('tests/test_runtime.py', 'TestEnsureRunsDir').
python_method('TestEnsureRunsDir', 'test_creates_full_subtree', 0, 1, 9).
python_method('TestEnsureRunsDir', 'test_writes_readme_stub_on_first_call', 0, 1, 8).
python_method('TestEnsureRunsDir', 'test_idempotent_does_not_overwrite_readme', 0, 1, 7).
python_method('TestEnsureRunsDir', 'test_does_not_write_outside_planfile', 0, 2, 6).
python_class('tests/test_scan.py', 'TestScanCLI').
python_method('TestScanCLI', 'test_json_output_uses_scan_result_dict_and_semcod_flag', 0, 1, 11).
python_class('tests/test_scan.py', 'TestScanPytestCollect').
python_method('TestScanPytestCollect', 'test_returns_empty_when_no_tests_and_no_pyproject', 0, 1, 4).
python_method('TestScanPytestCollect', 'test_empty_on_clean_collect', 0, 1, 6).
python_method('TestScanPytestCollect', 'test_parses_per_file_collection_errors', 0, 1, 8).
python_method('TestScanPytestCollect', 'test_falls_back_to_umbrella_import_ticket', 0, 1, 8).
python_method('TestScanPytestCollect', 'test_collection_timeout_emits_diagnostic_ticket', 0, 1, 8).
python_method('TestScanPytestCollect', 'test_timeout_value_is_reflected_in_ticket', 0, 1, 8).
python_method('TestScanPytestCollect', 'test_pytest_not_installed_stays_silent', 0, 1, 6).
python_class('tests/test_scan.py', 'TestScanTodoMarkers').
python_method('TestScanTodoMarkers', 'test_filters_files_below_threshold', 0, 1, 6).
python_method('TestScanTodoMarkers', 'test_groups_markers_per_file', 0, 5, 10).
python_method('TestScanTodoMarkers', 'test_respects_koruignore_file_glob', 0, 1, 8).
python_method('TestScanTodoMarkers', 'test_respects_koruignore_directory_prefix', 0, 1, 9).
python_method('TestScanTodoMarkers', 'test_ignores_common_virtualenv_dirs_by_default', 0, 1, 9).
python_class('tests/test_scan.py', 'TestScanMissingGates').
python_method('TestScanMissingGates', 'test_no_suggestions_when_tool_missing', 0, 2, 5).
python_method('TestScanMissingGates', 'test_skips_when_config_already_present', 0, 2, 5).
python_class('tests/test_scan.py', 'TestScanMissingTools').
python_method('TestScanMissingTools', 'test_no_pyproject_returns_empty', 0, 1, 4).
python_method('TestScanMissingTools', 'test_skips_tools_not_in_registry', 0, 1, 5).
python_class('tests/test_scan.py', 'TestScanGitignoreDrift').
python_method('TestScanGitignoreDrift', 'test_no_gitignore_returns_empty', 0, 1, 4).
python_method('TestScanGitignoreDrift', 'test_present_entry_skips_suggestion', 0, 1, 5).
python_method('TestScanGitignoreDrift', 'test_missing_entry_suggests', 0, 1, 6).
python_class('tests/test_scan.py', 'TestRunScan').
python_method('TestRunScan', 'test_dry_run_returns_suggestions_no_apply', 0, 1, 8).
python_method('TestRunScan', 'test_apply_creates_tickets_and_skips_duplicates', 0, 3, 10).
python_method('TestRunScan', 'test_apply_create_failure_is_skipped', 0, 1, 8).
python_method('TestRunScan', 'test_apply_creates_human_executor_tickets_without_custom_runner', 0, 1, 8).
python_method('TestRunScan', 'test_apply_uses_stable_title_and_deduplicates_by_signal', 0, 1, 12).
python_method('TestRunScan', 'test_apply_deduplicates_planfile_source_tool_payload', 0, 2, 10).
python_method('TestRunScan', 'test_existing_scan_titles_ignores_done_tickets', 0, 1, 7).
python_method('TestRunScan', 'test_limit_caps_suggestions', 0, 2, 8).
python_method('TestRunScan', 'test_priority_ordering_critical_first', 0, 2, 8).
python_class('tests/test_scan.py', 'TestScanSemcodArtifacts').
python_method('TestScanSemcodArtifacts', 'test_jscpd_report_emits_when_duplicates', 0, 2, 8).
python_method('TestScanSemcodArtifacts', 'test_code2llm_analysis_emits_when_god_rows', 0, 2, 7).
python_method('TestScanSemcodArtifacts', 'test_code2llm_analysis_emits_dup_ticket', 0, 2, 7).
python_method('TestScanSemcodArtifacts', 'test_code2llm_analysis_emits_cc_ticket', 0, 2, 7).
python_method('TestScanSemcodArtifacts', 'test_code2llm_analysis_emits_refactor_items', 0, 3, 7).
python_method('TestScanSemcodArtifacts', 'test_testql_export_emits_when_many_failures', 0, 3, 8).
python_method('TestScanSemcodArtifacts', 'test_redup_filtered_emits_when_many_groups', 0, 3, 9).
python_method('TestScanSemcodArtifacts', 'test_redup_changed_emits_when_wup_scan_has_groups', 0, 2, 8).
python_class('tests/test_serve.py', 'TestServe').
python_method('TestServe', 'setUp', 0, 1, 6).
python_method('TestServe', 'tearDown', 0, 1, 3).
python_method('TestServe', 'test_health_endpoint', 0, 1, 4).
python_method('TestServe', 'test_dashboard_html_served_on_root', 0, 1, 3).
python_method('TestServe', 'test_api_context_returns_brief', 0, 1, 4).
python_method('TestServe', 'test_api_handoff_returns_markdown', 0, 1, 3).
python_method('TestServe', 'test_api_topology_returns_components_and_pipelines', 0, 1, 4).
python_method('TestServe', 'test_api_topology_post_persists_toggle', 0, 1, 7).
python_method('TestServe', 'test_api_topology_post_rejects_empty_update', 0, 1, 4).
python_method('TestServe', 'test_unknown_path_returns_404', 0, 3, 3).
python_class('tests/test_serve.py', 'TestServeAutoPort').
python_method('TestServeAutoPort', 'test_auto_port_skips_busy_port', 0, 2, 20).
python_method('TestServeAutoPort', 'test_without_auto_port_busy_raises', 0, 1, 10).
python_class('tests/test_serve.py', 'TestServeReplacePrior').
python_method('TestServeReplacePrior', 'test_bind_retries_after_prior_listener_stopped', 0, 1, 10).
python_class('tests/test_tasks.py', 'TestNaturalLanguageTask').
python_method('TestNaturalLanguageTask', 'test_creates_planfile_ticket_from_sentence', 0, 1, 7).
python_method('TestNaturalLanguageTask', 'test_increments_next_id', 0, 1, 6).
python_method('TestNaturalLanguageTask', 'test_rejects_empty_text', 0, 1, 4).
python_method('TestNaturalLanguageTask', 'test_scaffold_overrides_ticket_shape', 0, 1, 7).
python_class('tests/test_topology.py', 'TestTopology').
python_method('TestTopology', 'setUp', 0, 1, 2).
python_method('TestTopology', 'tearDown', 0, 1, 1).
python_method('TestTopology', 'test_load_defaults_without_file', 0, 1, 3).
python_method('TestTopology', 'test_toggle_and_persist', 0, 1, 6).
python_method('TestTopology', 'test_enabled_components_for_pipeline_respects_component_flags', 0, 1, 6).
python_class('tests/test_watch.py', 'FakeWebSocket').
python_method('FakeWebSocket', '__init__', 1, 2, 1).
python_method('FakeWebSocket', '__aenter__', 0, 1, 0).
python_method('FakeWebSocket', '__aexit__', 0, 1, 0).
python_method('FakeWebSocket', 'recv', 0, 1, 1).
python_class('tests/test_watch.py', 'TestWatch').
python_method('TestWatch', 'test_format_queue_event_for_execution_change', 0, 1, 2).
python_method('TestWatch', 'test_format_management_event', 0, 1, 2).
python_method('TestWatch', 'test_watch_planfile_events_prints_compact_lines', 0, 1, 4).

% ── Dependencies ─────────────────────────────────────────

% ── Makefile Targets ─────────────────────────────────────

% ── Taskfile Tasks ───────────────────────────────────────
taskfile_task('', 'Show all available tasks').
taskfile_task('', 'Show koru version').
taskfile_task('', 'Install koru in editable mode').
taskfile_task('', 'Install koru with dev dependencies (pytest etc.)').
taskfile_task('', 'Install semcod toolchain used by koru (planfile, wup, testql, regix, redup, sumr/sumd, doql, redeploy, ...)').
taskfile_task('', 'Run default koru tests (slow Docker/integration tests are deselected by pytest addopts)').
taskfile_task('', 'Run every koru test, including slow Docker/integration tests').
taskfile_task('', 'Run Docker E2E tests only (slow; deselected by default addopts)').
taskfile_task('', 'Run Docker OS x IDE smoke matrix. Vars: SYSTEMS, IDES (defaults cover Debian/Ubuntu/Fedora/Alpine and VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed)').
taskfile_task('', 'Run tests without verbose output').
taskfile_task('', 'Fastest possible test run (fail fast, no header)').
taskfile_task('', 'Run tests in parallel (safe only for isolated subsets)').
taskfile_task('', 'Run ruff on koru sources and tests').
taskfile_task('', 'Run ruff with autofix').
taskfile_task('', 'Local CI equivalent (lint + tests)').
taskfile_task('', 'Run closed-loop across workspace. Vars: WORKSPACE, INCLUDE, COMMAND').
taskfile_task('', 'Run pytest in closed-loop mode').
taskfile_task('', 'Run ruff in closed-loop mode').
taskfile_task('', 'Run one task from planfile queue. Vars: PROJECT, ACTOR, DRY_RUN').
taskfile_task('', 'Preview one runnable planfile queue task without executing it').
taskfile_task('', 'Watch planfile WebSocket events. Vars: WS_URL, MAX_EVENTS').
taskfile_task('', 'Continuous intake+execution loop (scan + queue --loop + idle diagnostics + autopilot drive). See scripts/koru-autoloop.sh header for all env vars.').
taskfile_task('', 'Clear autoloop diagnostic dedup markers; optionally close [AUTO-DIAG] tickets. Usage: task queue:autoloop:reset-diag-markers CLOSE_TICKETS=true CHECK=regix').
taskfile_task('', 'Start the local koru dashboard/API for operator checks').
taskfile_task('', 'Provision koru MCP config for Cursor, VS Code, and Windsurf').
taskfile_task('', 'Check autopilot daemon/plugin install, live version, and socket status').
taskfile_task('', 'Probe host injector dependencies for autopilot').
taskfile_task('', 'Calibrate OS injector chat coordinates for an IDE (IDE=vscode|vscodium|cursor|windsurf|jetbrains|zed)').
taskfile_task('', 'Run regix gates locally (LLM-free regression metrics)').
taskfile_task('', 'Compare working tree against HEAD with regix').
taskfile_task('', 'Check WUP on-change watcher configuration').
taskfile_task('', 'Run redup duplicate detection (default: current dir)').
taskfile_task('', 'Run incremental redup scan over files changed since BASE_REF (default: HEAD)').
taskfile_task('', 'Run redup with budget check (uses scripts/redup-check.sh)').
taskfile_task('', 'Validate file with vallm (FILE=path/to/file.py)').
taskfile_task('', 'Validate with LLM-as-judge (requires OPENROUTER_API_KEY, FILE=...)').
taskfile_task('', 'Show SUMR.md staleness vs HEAD (LLM-free; exit 1 if stale)').
taskfile_task('', 'Refresh SUMR.md only if stale (debounced; safe for hooks/cron)').
taskfile_task('', 'Force-refresh SUMR.md (bumps sumd/code2llm/redup/doql + regenerates)').
taskfile_task('', 'Install git post-merge hook (HOOK=post-commit|both for alt)').
taskfile_task('', 'Remove sumr-refresh git hooks (leaves foreign hooks intact)').
taskfile_task('', 'Run configured semcod/* gates and create/update deduplicated planfile tickets on failures').
taskfile_task('', 'Show highest-priority open ticket').
taskfile_task('', 'List open tickets').
taskfile_task('', 'Show ticket details (TID=PLF-XXX)').
taskfile_task('', 'Mark ticket as done (TID=PLF-XXX)').
taskfile_task('', 'Export ticket as LLM-ready prompt (TID=PLF-XXX)').
taskfile_task('', 'List available templates').
taskfile_task('', 'Copy all template configs to current directory').
taskfile_task('', 'Copy single template (TPL=pyqual.yaml|redup.toml|redsl.yaml|...)').
taskfile_task('', 'Copy docker-compose.quality.yml template').
taskfile_task('', 'Copy SUMR-refresh stack (script + git hooks + weekly workflow)').
taskfile_task('', 'Copy redeploy templates (local + device baseline) to redeploy/').
taskfile_task('', 'Copy observability stack (Prometheus + Grafana + Loki + Alertmanager + healing-webhook)').
taskfile_task('', 'Copy .windsurf/ bootstrap (rules.md + mcp_config.example.json)').
taskfile_task('', 'Copy GH Actions templates (version-drift + code-quality) to .github/workflows/').
taskfile_task('', 'Copy .pre-commit-config.yaml template').
taskfile_task('', 'Copy wup.yaml template (on-change file watcher feeding testql gates)').
taskfile_task('', 'Bootstrap on-change gate triad configs (wup.yaml + regix.yaml)').
taskfile_task('', 'List available scripts').
taskfile_task('', 'Run redup-check.sh (PATH=. by default)').
taskfile_task('', 'Run redup precommit hook').
taskfile_task('', 'Run regix precommit hook').
taskfile_task('', 'Run redsl gate precommit hook').
taskfile_task('', 'Sync planfile tickets with TODO.md').
taskfile_task('', 'Start background koru autonomous soak (--max-cycles 0, logs to .planfile/.koru/soak.log)').
taskfile_task('', 'Show current long-run autonomy soak status (PID, uptime, cycle, ticket, report)').
taskfile_task('', 'Start or restart the background soak completion monitor for STARTER-009').
taskfile_task('', 'Show interim/final soak reports when present').
taskfile_task('', 'Stop the background soak run and monitor, write a stop report, optionally mark ticket done').
taskfile_task('', 'Plan deploy without changes — DEVICE=<name> SPEC=<file> (defaults: local + deployment.md)').
taskfile_task('', 'Dry run deploy (preview commands) — DEVICE=<name>').
taskfile_task('', 'Deploy locally via Docker Compose').
taskfile_task('', 'Deploy to remote device — DEVICE=<name> (e.g. pi109, edge01)').
taskfile_task('', 'Read-only diagnose — DEVICE=<name> (default: local)').
taskfile_task('', 'Resume failed deploy — DEVICE=<name> STEP=<step_id>').
taskfile_task('', 'Snapshot device state into app.doql.less (drift baseline) — DEVICE_HOST=<user@host>').
taskfile_task('', 'Ensure the shared quality-net docker network exists').
taskfile_task('', 'Bring up the full observability + self-healing stack (10 services)').
taskfile_task('', 'Bring up observability without Loki/Promtail (skip if disk is tight)').
taskfile_task('', 'Stop the observability stack').
taskfile_task('', 'Show status of observability containers').
taskfile_task('', 'Tail logs of one observability service — SVC=<name> (default: healing-webhook)').
taskfile_task('', 'Sanity check — curl health endpoints of all observability services').
taskfile_task('', 'Hot-reload Prometheus rules (no restart)').
taskfile_task('', 'Run healing-webhook locally on port 8810').
taskfile_task('', 'Build healing-webhook Docker image').
taskfile_task('', 'Run healing-webhook in Docker (port 8810)').
taskfile_task('', 'Send test alertmanager payload to local webhook').
taskfile_task('', 'Open documentation index').
taskfile_task('', 'Serve docs over HTTP (port 8000)').
taskfile_task('', 'List available workflows (markdown instructions for agents)').
taskfile_task('', 'Show workflow content (NAME=testql-autoloop|aider-docker-autoloop|...)').

% ── Environment Variables ────────────────────────────────
env_variable('OPENROUTER_API_KEY', '*(not set)*', 'Required: OpenRouter API key (https://openrouter.ai/keys)').
env_variable('LLM_MODEL', 'openrouter/qwen/qwen3-coder-next', 'Model (default: openrouter/qwen/qwen3-coder-next)').
env_variable('PFIX_AUTO_APPLY', 'true', 'true = apply fixes without asking').
env_variable('PFIX_AUTO_INSTALL_DEPS', 'true', 'true = auto pip/uv install').
env_variable('PFIX_AUTO_RESTART', 'false', 'true = os.execv restart after fix').
env_variable('PFIX_MAX_RETRIES', '3', '').
env_variable('PFIX_DRY_RUN', 'false', '').
env_variable('PFIX_ENABLED', 'true', '').
env_variable('PFIX_GIT_COMMIT', 'false', 'true = auto-commit fixes').
env_variable('PFIX_GIT_PREFIX', 'pfix:', 'commit message prefix').
env_variable('PFIX_CREATE_BACKUPS', 'false', 'false = disable .pfix_backups/ directory').

% ── TestQL Scenarios ─────────────────────────────────────
testql_scenario('generated-cli-tests.testql.toon.yaml', 'cli').
testql_scenario('generated-from-pytests.testql.toon.yaml', 'integration').

% ── Semantic Facts from SUMD.md ──────────────────────────
sumd_declared_file('app.doql.less', 'doql').
sumd_declared_file('testql-scenarios/generated-cli-tests.testql.toon.yaml', 'testql').
sumd_declared_file('testql-scenarios/generated-from-pytests.testql.toon.yaml', 'testql').
sumd_declared_file('Taskfile.yml', 'taskfile').
sumd_declared_file('project/map.toon.yaml', 'analysis').
sumd_declared_file('project/logic.pl', 'analysis').
sumd_declared_file('project/calls.toon.yaml', 'analysis').
sumd_interface('api', '').
sumd_interface('cli', 'argparse').
sumd_interface('cli', '').
sumd_workflow('default', 'manual').
sumd_workflow_step('default', 1, 'task --list-all').
sumd_workflow('version', 'manual').
sumd_workflow('install', 'manual').
sumd_workflow_step('install', 1, 'pip install -e .').
sumd_workflow('install:dev', 'manual').
sumd_workflow_step('install:dev', 1, 'pip install -e ".[dev]" || pip install -e .').
sumd_workflow('install:tools', 'manual').
sumd_workflow_step('install:tools', 1, 'pip install planfile wup testql regix "redup>=0.4.28" vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun').
sumd_workflow_step('install:tools', 2, 'echo "✓ semcod toolchain installed. Optional interactive agent: pip install aider-chat"').
sumd_workflow('test', 'manual').
sumd_workflow('test:all', 'manual').
sumd_workflow('test:docker', 'manual').
sumd_workflow('test:docker:ide-matrix', 'manual').
sumd_workflow('test:fast', 'manual').
sumd_workflow_step('test:fast', 1, 'python3 -m pytest tests/ -q').
sumd_workflow('test:quick', 'manual').
sumd_workflow_step('test:quick', 1, 'python3 -m pytest tests/ -q --maxfail=1 --no-header').
sumd_workflow('test:parallel', 'manual').
sumd_workflow_step('test:parallel', 1, 'python3 -m pytest tests/ -q -n auto --maxfail=1').
sumd_workflow('lint', 'manual').
sumd_workflow_step('lint', 1, 'python3 -m ruff check src tests').
sumd_workflow('lint:fix', 'manual').
sumd_workflow_step('lint:fix', 1, 'python3 -m ruff check src tests --fix').
sumd_workflow('loop', 'manual').
sumd_workflow('queue:run', 'manual').
sumd_workflow('queue:watch', 'manual').
sumd_workflow('queue:autoloop', 'manual').
sumd_workflow('queue:autoloop:reset-diag-markers', 'manual').
sumd_workflow('koru:server', 'manual').
sumd_workflow('koru:mcp:bootstrap', 'manual').
sumd_workflow('koru:operator:plugin-probe', 'manual').
sumd_workflow('koru:operator:setup-host', 'manual').
sumd_workflow('koru:ide-os:calibrate', 'manual').
sumd_workflow('quality:regix', 'manual').
sumd_quality_workflow('quality:regix', 'regix').
sumd_workflow('quality:regix:local', 'manual').
sumd_quality_workflow('quality:regix:local', 'regix:local').
sumd_workflow_step('quality:regix:local', 1, 'regix compare HEAD --local').
sumd_workflow('quality:wup', 'manual').
sumd_quality_workflow('quality:wup', 'wup').
sumd_workflow('quality:redup', 'manual').
sumd_quality_workflow('quality:redup', 'redup').
sumd_workflow('quality:redup:changed', 'manual').
sumd_quality_workflow('quality:redup:changed', 'redup:changed').
sumd_workflow_step('quality:redup:changed', 1, 'bash -lc \'set -euo pipefail').
sumd_workflow('quality:redup:check', 'manual').
sumd_quality_workflow('quality:redup:check', 'redup:check').
sumd_workflow('quality:vallm', 'manual').
sumd_quality_workflow('quality:vallm', 'vallm').
sumd_workflow('quality:vallm:semantic', 'manual').
sumd_quality_workflow('quality:vallm:semantic', 'vallm:semantic').
sumd_workflow('quality:sumr:status', 'manual').
sumd_quality_workflow('quality:sumr:status', 'sumr:status').
sumd_workflow('quality:sumr:auto', 'manual').
sumd_quality_workflow('quality:sumr:auto', 'sumr:auto').
sumd_workflow('quality:sumr:refresh', 'manual').
sumd_quality_workflow('quality:sumr:refresh', 'sumr:refresh').
sumd_workflow('quality:sumr:install-hook', 'manual').
sumd_quality_workflow('quality:sumr:install-hook', 'sumr:install-hook').
sumd_workflow('quality:sumr:uninstall-hook', 'manual').
sumd_quality_workflow('quality:sumr:uninstall-hook', 'sumr:uninstall-hook').
sumd_workflow_step('quality:sumr:uninstall-hook', 1, 'bash scripts/git-hooks/install.sh --uninstall').
sumd_workflow('quality:semcod:planfile', 'manual').
sumd_quality_workflow('quality:semcod:planfile', 'semcod:planfile').
sumd_workflow_step('quality:semcod:planfile', 1, 'bash scripts/koru-semcod-gates.sh').
sumd_workflow('tickets:next', 'manual').
sumd_workflow_step('tickets:next', 1, 'planfile ticket next').
sumd_workflow('tickets:list', 'manual').
sumd_workflow_step('tickets:list', 1, 'planfile ticket list --status open --format yaml').
sumd_workflow('tickets:show', 'manual').
sumd_workflow('tickets:done', 'manual').
sumd_workflow('tickets:export', 'manual').
sumd_workflow('template:list', 'manual').
sumd_workflow_step('template:list', 1, 'ls templates/').
sumd_workflow('template:install', 'manual').
sumd_workflow_step('template:install', 1, 'cp templates/pyqual.yaml.template ./pyqual.yaml').
sumd_workflow_step('template:install', 2, 'cp templates/redup.toml.template ./redup.toml').
sumd_workflow_step('template:install', 3, 'cp templates/redsl.yaml.template ./redsl.yaml').
sumd_workflow_step('template:install', 4, 'cp templates/regix.yaml.template ./regix.yaml').
sumd_workflow_step('template:install', 5, 'cp templates/llx.toml.template ./llx.toml').
sumd_workflow_step('template:install', 6, 'cp templates/llx.yaml.template ./llx.yaml').
sumd_workflow_step('template:install', 7, 'cp templates/prefact.yaml.template ./prefact.yaml').
sumd_workflow_step('template:install', 8, 'echo "✓ All templates copied. Review and edit before committing."').
sumd_workflow('template:install:single', 'manual').
sumd_workflow('template:install:compose', 'manual').
sumd_workflow_step('template:install:compose', 1, 'cp templates/docker-compose.quality.yml.template ./docker-compose.quality.yml').
sumd_workflow_step('template:install:compose', 2, 'echo "✓ docker-compose.quality.yml copied. Review service definitions."').
sumd_workflow('template:install:sumr', 'manual').
sumd_workflow_step('template:install:sumr', 1, 'mkdir -p scripts scripts/git-hooks .github/workflows').
sumd_workflow_step('template:install:sumr', 2, 'cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh').
sumd_workflow_step('template:install:sumr', 3, 'cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge').
sumd_workflow_step('template:install:sumr', 4, 'cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit').
sumd_workflow_step('template:install:sumr', 5, 'cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh').
sumd_workflow_step('template:install:sumr', 6, 'cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml').
sumd_workflow_step('template:install:sumr', 7, 'chmod +x scripts/sumr-refresh.sh scripts/git-hooks/post-merge scripts/git-hooks/post-commit scripts/git-hooks/install.sh').
sumd_workflow_step('template:install:sumr', 8, 'grep -q \'^\.sumr/$\' .gitignore 2>/dev/null || echo \'.sumr/\' >> .gitignore').
sumd_workflow_step('template:install:sumr', 9, 'echo "✓ SUMR stack installed. Next: task quality:sumr:install-hook (see workflows/sumr-refresh-loop.md)"').
sumd_workflow('template:install:redeploy', 'manual').
sumd_workflow_step('template:install:redeploy', 1, 'mkdir -p redeploy/local redeploy/device').
sumd_workflow_step('template:install:redeploy', 2, 'cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md').
sumd_workflow_step('template:install:redeploy', 3, 'cp templates/redeploy/device/manifest.yaml.template    redeploy/device/manifest.yaml').
sumd_workflow_step('template:install:redeploy', 4, 'cp templates/redeploy/device/migration.md.template     redeploy/device/migration.md').
sumd_workflow_step('template:install:redeploy', 5, 'cp templates/redeploy/device/diagnose.md.template      redeploy/device/diagnose.md').
sumd_workflow_step('template:install:redeploy', 6, 'echo "✓ redeploy templates installed at redeploy/"').
sumd_workflow_step('template:install:redeploy', 7, 'echo "  Next: substitute placeholders (see workflows/redeploy-multi-device.md Krok 3)"').
sumd_workflow_step('template:install:redeploy', 8, 'echo "        rename redeploy/device/ → redeploy/<your-device>/"').
sumd_workflow_step('template:install:redeploy', 9, 'echo "        sed -i \'s/<APP_NAME>/myapp/g\' redeploy/local/*.md redeploy/device/*"').
sumd_workflow('template:install:observability', 'manual').
sumd_workflow_step('template:install:observability', 1, 'mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning').
sumd_workflow_step('template:install:observability', 2, 'cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml').
sumd_workflow_step('template:install:observability', 3, 'cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml').
sumd_workflow_step('template:install:observability', 4, 'cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml').
sumd_workflow_step('template:install:observability', 5, 'cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml').
sumd_workflow_step('template:install:observability', 6, 'echo "✓ Observability stack installed."').
sumd_workflow_step('template:install:observability', 7, 'echo "  Next: substitute <APP_NAME>/<APP_PORT> placeholders, then task monitor:up"').
sumd_workflow_step('template:install:observability', 8, 'echo "  See: workflows/observability-bootstrap.md"').
sumd_workflow('template:install:windsurf', 'manual').
sumd_workflow_step('template:install:windsurf', 1, 'mkdir -p .windsurf').
sumd_workflow_step('template:install:windsurf', 2, 'cp templates/.windsurf/rules.md.template               .windsurf/rules.md').
sumd_workflow_step('template:install:windsurf', 3, 'cp templates/.windsurf/mcp_config.example.json.template .windsurf/mcp_config.example.json').
sumd_workflow_step('template:install:windsurf', 4, 'echo "✓ .windsurf/ installed."').
sumd_workflow_step('template:install:windsurf', 5, 'echo "  Next: substitute <APP_NAME>/<REPO_PATH>, then merge mcp_config into ~/.codeium/windsurf/mcp_config.json"').
sumd_workflow('template:install:ci', 'manual').
sumd_workflow_step('template:install:ci', 1, 'mkdir -p .github/workflows').
sumd_workflow_step('template:install:ci', 2, 'cp templates/github-workflows/version-drift.yml.template   .github/workflows/version-drift.yml').
sumd_workflow_step('template:install:ci', 3, 'cp templates/github-workflows/code-quality.yml.template    .github/workflows/code-quality.yml').
sumd_workflow_step('template:install:ci', 4, 'mkdir -p scripts').
sumd_workflow_step('template:install:ci', 5, 'cp templates/scripts/check-version-drift.sh.template       scripts/check-version-drift.sh').
sumd_workflow_step('template:install:ci', 6, 'chmod +x scripts/check-version-drift.sh').
sumd_workflow_step('template:install:ci', 7, 'echo "✓ CI templates installed."').
sumd_workflow_step('template:install:ci', 8, 'echo "  Next: ensure VERSION file at repo root + commit + push"').
sumd_workflow('template:install:precommit', 'manual').
sumd_workflow_step('template:install:precommit', 1, 'cp templates/.pre-commit-config.yaml.template .pre-commit-config.yaml').
sumd_workflow_step('template:install:precommit', 2, 'echo "✓ .pre-commit-config.yaml installed."').
sumd_workflow_step('template:install:precommit', 3, 'echo "  Next: substitute <APP_NAME>, then: pip install pre-commit && pre-commit install"').
sumd_workflow('template:install:wup', 'manual').
sumd_workflow_step('template:install:wup', 1, 'cp templates/wup.yaml.template ./wup.yaml').
sumd_workflow('template:install:on-change-gates', 'manual').
sumd_workflow_step('template:install:on-change-gates', 1, 'test -f regix.yaml || cp templates/regix.yaml.template ./regix.yaml').
sumd_workflow_step('template:install:on-change-gates', 2, 'echo "✓ on-change gate triad installed (wup.yaml + regix.yaml)"').
sumd_workflow_step('template:install:on-change-gates', 3, 'echo "  testql scenarios are project-specific — re-use existing testql-testing/scenarios/ or write new TOON YAML by hand"').
sumd_workflow_step('template:install:on-change-gates', 4, 'echo "  Workflow guide: see koru workflows/on-change-gates.md"').
sumd_workflow_step('template:install:on-change-gates', 5, 'echo "  Slash command:  /koru-gate (invokes all three on demand)"').
sumd_workflow('scripts:list', 'manual').
sumd_workflow_step('scripts:list', 1, 'ls scripts/').
sumd_workflow('scripts:redup:check', 'manual').
sumd_workflow('scripts:redup:precommit', 'manual').
sumd_workflow_step('scripts:redup:precommit', 1, 'bash scripts/redup-precommit.sh').
sumd_workflow('scripts:regix:precommit', 'manual').
sumd_workflow_step('scripts:regix:precommit', 1, 'bash scripts/regix-precommit.sh').
sumd_workflow('scripts:redsl:precommit', 'manual').
sumd_workflow_step('scripts:redsl:precommit', 1, 'bash scripts/redsl-gate-precommit.sh').
sumd_workflow('scripts:planfile:sync-todo', 'manual').
sumd_workflow_step('scripts:planfile:sync-todo', 1, 'python3 scripts/planfile-sync-todo.py').
sumd_workflow('scripts:soak:start', 'manual').
sumd_workflow_step('scripts:soak:start', 1, 'bash scripts/koru-soak-start.sh').
sumd_workflow('scripts:soak:status', 'manual').
sumd_workflow_step('scripts:soak:status', 1, 'bash scripts/koru-soak-status.sh').
sumd_workflow('scripts:soak:monitor', 'manual').
sumd_workflow('scripts:soak:report', 'manual').
sumd_workflow('scripts:soak:stop', 'manual').
sumd_workflow_step('scripts:soak:stop', 1, 'bash scripts/koru-soak-stop.sh').
sumd_workflow('deploy:plan', 'manual').
sumd_workflow('deploy:dry', 'manual').
sumd_workflow('deploy:local', 'manual').
sumd_workflow_step('deploy:local', 1, 'redeploy run redeploy/local/deployment.md').
sumd_workflow('deploy:device', 'manual').
sumd_workflow('deploy:diagnose', 'manual').
sumd_workflow('deploy:resume', 'manual').
sumd_workflow('deploy:drift', 'manual').
sumd_workflow('monitor:net', 'manual').
sumd_workflow('monitor:up', 'manual').
sumd_workflow_step('monitor:up', 1, 'docker compose -f docker-compose.observability.yml up -d --build').
sumd_workflow_step('monitor:up', 2, 'echo ""').
sumd_workflow('monitor:up:lite', 'manual').
sumd_workflow_step('monitor:up:lite', 1, 'docker compose -f docker-compose.observability.yml up -d --build prometheus alertmanager grafana blackbox-exporter node-exporter cadvisor uptime-kuma healing-webhook').
sumd_workflow('monitor:down', 'manual').
sumd_workflow_step('monitor:down', 1, 'docker compose -f docker-compose.observability.yml down').
sumd_workflow('monitor:status', 'manual').
sumd_workflow_step('monitor:status', 1, 'docker compose -f docker-compose.observability.yml ps').
sumd_workflow('monitor:logs', 'manual').
sumd_workflow('monitor:probe', 'manual').
sumd_workflow('monitor:reload-prometheus', 'manual').
sumd_workflow('webhook:run', 'manual').
sumd_workflow_step('webhook:run', 1, 'cd services/healing-webhook && python3 app.py').
sumd_workflow('webhook:docker:build', 'manual').
sumd_workflow_step('webhook:docker:build', 1, 'docker build -t koru-healing-webhook:latest services/healing-webhook/').
sumd_workflow('webhook:docker:run', 'manual').
sumd_workflow_step('webhook:docker:run', 1, 'docker run --rm -p 8810:8810 koru-healing-webhook:latest').
sumd_workflow('webhook:test', 'manual').
sumd_workflow('docs', 'manual').
sumd_workflow_step('docs', 1, 'echo "Documentation: docs/README.md"').
sumd_workflow_step('docs', 2, 'echo "Agent guide:   docs/agent-guide.md"').
sumd_workflow_step('docs', 3, 'echo "Tool catalog:  docs/llm-tools/README.md"').
sumd_workflow_step('docs', 4, 'echo "CLI examples:  docs/cli-examples.md"').
sumd_workflow('docs:serve', 'manual').
sumd_workflow_step('docs:serve', 1, 'cd docs && python3 -m http.server 8000').
sumd_workflow('workflow:list', 'manual').
sumd_workflow_step('workflow:list', 1, 'ls workflows/').
sumd_workflow('workflow:show', 'manual').
sumd_deploy_target('docker_compose').
sumd_deploy_compose_file('docker-compose.yml').
```

## Call Graph

*440 nodes · 500 edges · 76 modules · CC̄=4.1*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 350 | 0 | **350** |
| `_build_handler` *(in src.koruapi.dashboard_serve)* | 1 | 1 | 105 | **106** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 5 | 47 | **52** |
| `_drive_via_keyboard` *(in src.koruide.daemon.AutopilotDaemon)* | 12 ⚠ | 0 | 47 | **47** |
| `activity` *(in src.koru.activity_log)* | 4 | 34 | 7 | **41** |
| `_stdio_info` *(in src.koru.autonomous)* | 1 | 40 | 1 | **41** |
| `_build_parser` *(in src.koru.cli)* | 1 | 3 | 36 | **39** |
| `emit_management_event` *(in src.koru.events)* | 8 | 32 | 7 | **39** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.22s
# nodes: 440 | edges: 500 | modules: 76
# CC̄=4.1

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:350  out:0  total:350
  src.koruapi.dashboard_serve._build_handler
    CC=1  in:1  out:105  total:106
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:47  total:52
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=12  in:0  out:47  total:47
  src.koru.activity_log.activity
    CC=4  in:34  out:7  total:41
  src.koru.autonomous._stdio_info
    CC=1  in:40  out:1  total:41
  src.koru.cli._build_parser
    CC=1  in:3  out:36  total:39
  src.koru.events.emit_management_event
    CC=8  in:32  out:7  total:39
  src.koru.tasks.create_nl_task
    CC=12  in:7  out:28  total:35
  src.koruide.ide.normalize_ide_id
    CC=6  in:23  out:11  total:34
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  src.koru.cli._topology_main
    CC=12  in:0  out:32  total:32
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.cli._task_main
    CC=11  in:0  out:27  total:27
  src.koru.ide_runtime.detect_running_ides
    CC=5  in:15  out:12  total:27
  src.koru.init.init_project
    CC=7  in:3  out:23  total:26
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koruide.os_injector.inject_with_profile
    CC=15  in:3  out:23  total:26

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
  services.healing-webhook.ticket_builder  [2 funcs]
    _infer_paths  CC=7  out:1
    build_ticket_payload  CC=11  out:25
  src.koru.activity_log  [2 funcs]
    activity  CC=4  out:7
    activity_info  CC=5  out:11
  src.koru.agent_backends  [6 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    iter_agent_backend_profiles  CC=1  out:0
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.agent_cli_helpers  [3 funcs]
    print_agent_list  CC=10  out:7
    run_agent_handoff  CC=3  out:10
    try_agent_env_exports  CC=7  out:7
  src.koru.agents  [2 funcs]
    agent_lane_environment  CC=1  out:3
    detect_agent_options  CC=4  out:21
  src.koru.autonomous  [32 funcs]
    _ancestor_pids  CC=7  out:8
    _apply_agent_lane_environ  CC=3  out:3
    _as_managed  CC=1  out:1
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _create_diagnostic_ticket  CC=2  out:8
    _current_koru_version  CC=2  out:1
    _daemon_activity_log  CC=2  out:3
    _daemon_status_compatible  CC=4  out:2
    _daemon_status_version  CC=7  out:6
  src.koru.autonomous_diagnostics  [5 funcs]
    _has_redup_module  CC=2  out:2
    build_idle_checks  CC=11  out:20
    create_diagnostic_ticket  CC=2  out:6
    run_idle_check_loop  CC=6  out:8
    run_idle_diagnostics  CC=3  out:9
  src.koru.autonomous_parser  [1 funcs]
    looks_like_autonomous_up_command  CC=2  out:3
  src.koru.autonomous_process_guard  [2 funcs]
    find_existing_autonomous_processes  CC=11  out:16
    find_existing_wup_processes  CC=11  out:15
  src.koru.autonomy.env  [1 funcs]
    env_truthy  CC=3  out:3
  src.koru.autopilot.doctor_cli  [1 funcs]
    render_doctor_text  CC=1  out:4
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
  src.koru.cli  [40 funcs]
    _agent_backends_main  CC=8  out:23
    _agent_main  CC=3  out:7
    _auto_main  CC=6  out:6
    _bootstrap_main  CC=5  out:18
    _build_agent_parser  CC=1  out:12
    _build_gate_parser  CC=1  out:11
    _build_gc_parser  CC=1  out:14
    _build_parser  CC=1  out:36
    _build_queue_parser  CC=1  out:11
    _build_runtime_context_parser  CC=1  out:4
  src.koru.cli_gate  [2 funcs]
    build_gate_parser  CC=1  out:11
    gate_main  CC=5  out:12
  src.koru.context  [2 funcs]
    build_context  CC=6  out:16
    render_markdown_handoff  CC=10  out:47
  src.koru.dev_sync  [4 funcs]
    _is_dirty  CC=2  out:3
    _pull_repo  CC=7  out:4
    dev_main  CC=7  out:18
    sync_developer_packages  CC=9  out:16
  src.koru.doctor  [1 funcs]
    run_diagnostics  CC=6  out:11
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.gate  [2 funcs]
    _resolve_actor  CC=4  out:1
    authorize_gate  CC=9  out:16
  src.koru.gc  [1 funcs]
    run_gc  CC=11  out:9
  src.koru.gc_cli_helpers  [5 funcs]
    emit_gc_management_event  CC=2  out:3
    gc_result_to_json  CC=3  out:1
    gc_statuses_from_args  CC=3  out:4
    print_gc_report  CC=2  out:4
    print_gc_text_report  CC=12  out:14
  src.koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
  src.koru.ide_router  [2 funcs]
    is_headless_environment  CC=8  out:6
    resolve_ide_route  CC=7  out:7
  src.koru.ide_runtime  [1 funcs]
    detect_running_ides  CC=5  out:12
  src.koru.init  [2 funcs]
    init_project  CC=7  out:23
    refresh_init_agent_lane  CC=4  out:11
  src.koru.local_service  [2 funcs]
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:12
  src.koru.loop  [3 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
    run_closed_loop  CC=12  out:18
  src.koru.mcp_provision  [24 funcs]
    _apply_target  CC=5  out:5
    _cursor_project_config  CC=1  out:0
    _koru_mcp_entry  CC=1  out:1
    _koru_mcp_entry_cursor  CC=1  out:1
    _maybe_upgrade_koru_command  CC=5  out:3
    _read_json  CC=3  out:3
    _removal_paths_for_ide  CC=6  out:6
    _render_results  CC=5  out:8
    _resolve_targets  CC=5  out:5
    _resolved_koru_command  CC=2  out:1
  src.koru.queue.koru_queue_argv  [1 funcs]
    build_koru_queue_argv  CC=5  out:7
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=14  out:9
  src.koru.queue.runners  [1 funcs]
    run_process  CC=1  out:2
  src.koru.queue.ticket  [1 funcs]
    planfile_command  CC=4  out:5
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
  src.koru.queue_cli_helpers  [4 funcs]
    emit_queue_run_started  CC=2  out:2
    open_queue_run_log  CC=4  out:2
    run_queue_loop_mode  CC=6  out:21
    run_queue_single_mode  CC=9  out:18
  src.koru.redup_integration  [1 funcs]
    redup_check_command  CC=1  out:3
  src.koru.refactor_planfile_handoff  [1 funcs]
    render_planfile_refactor_handoff  CC=6  out:6
  src.koru.runtime  [4 funcs]
    ensure_runs_dir  CC=2  out:5
    planfile_dir  CC=1  out:1
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=12  out:28
  src.koru.tools  [4 funcs]
    build_tool_task_scaffold  CC=2  out:6
    detect_tools  CC=4  out:8
    find_tool_entry  CC=4  out:6
    load_tool_registry  CC=11  out:13
  src.koru.topology  [5 funcs]
    enabled_components_for_pipeline  CC=9  out:11
    is_component_enabled  CC=3  out:6
    is_pipeline_enabled  CC=3  out:6
    load_topology  CC=1  out:9
    set_component_enabled  CC=1  out:1
  src.koru.topology_cli  [2 funcs]
    apply_topology_mutations  CC=4  out:3
    render_topology_text  CC=2  out:9
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
    _normalize_args  CC=5  out:15
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
  src.koruapi.dashboard_serve  [15 funcs]
    _address_in_use  CC=4  out:4
    _build_handler  CC=1  out:105
    _bulk_waiting_input_action  CC=13  out:14
    _cmdline_suggests_koru_serve  CC=3  out:3
    _cmdline_suggests_koru_serve_from_bytes  CC=3  out:7
    _list_tickets  CC=9  out:6
    _listener_pids_for_tcp_port  CC=7  out:7
    _try_stop_prior_koru_serve_listener  CC=12  out:13
    bind_serve_server  CC=11  out:10
    build_server  CC=1  out:2
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
  src.koruapi.mcp_server  [27 funcs]
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
  src.koruapi.runtime_insights  [6 funcs]
    _active_tools  CC=8  out:13
    _classify_process  CC=5  out:8
    _looks_project_related  CC=1  out:2
    _run_ps  CC=9  out:11
    _top_processes  CC=2  out:9
    collect_runtime_insights  CC=4  out:14
  src.koruapi.server  [8 funcs]
    do_GET  CC=5  out:12
    do_POST  CC=2  out:4
    log_message  CC=1  out:2
    _handle_invoke_post  CC=5  out:13
    _json_response  CC=1  out:9
    _parse_invoke_request  CC=9  out:16
    _read_json_body  CC=5  out:7
    serve  CC=2  out:8
  src.koruapi.topology_post  [1 funcs]
    apply_topology_post_update  CC=14  out:22
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
  src.koruide.audit  [4 funcs]
    __init__  CC=4  out:12
    record  CC=6  out:7
    _isoformat_utc  CC=2  out:5
    default_log_path  CC=2  out:3
  src.koruide.client  [2 funcs]
    __init__  CC=2  out:1
    request  CC=7  out:15
  src.koruide.config  [4 funcs]
    _merge_submit_keys  CC=7  out:5
    cached_config  CC=1  out:2
    default_config_path  CC=1  out:1
    load_config  CC=4  out:10
  src.koruide.daemon  [18 funcs]
    __init__  CC=7  out:9
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=12  out:47
    _handle_ack  CC=10  out:15
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=5  out:15
    _log_rejected_plugin_connection  CC=6  out:8
    _relay_message_sent_ack  CC=3  out:10
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
  src.koruide.ide  [6 funcs]
    detect_focused_ide_id  CC=3  out:2
    detect_terminal_host_ide_id  CC=3  out:3
    normalize_ide_id  CC=6  out:11
    pick_target  CC=13  out:5
    resolve_drive_target  CC=12  out:8
    supported_autopilot_ide_ids  CC=1  out:0
  src.koruide.injector  [9 funcs]
    _candidate_backends  CC=6  out:13
    _type_with_backend  CC=14  out:21
    submit_only  CC=5  out:9
    type_text  CC=8  out:11
    _extra_enter_count  CC=3  out:4
    _forced_injector_backend  CC=2  out:3
    _submit_key_for  CC=1  out:2
    _ydotool_enter_keycode  CC=2  out:3
    _ydotool_submit_mode  CC=3  out:3
  src.koruide.os_injector  [23 funcs]
    _clipboard_backend  CC=3  out:2
    _cmd_timeout_seconds  CC=3  out:4
    _is_wayland_session  CC=1  out:3
    _post_focus_delay_seconds  CC=3  out:5
    _read_json  CC=4  out:5
    _run_cmd  CC=5  out:7
    _set_clipboard  CC=3  out:6
    _tool_pid  CC=4  out:2
    _xdotool  CC=1  out:1
    capture_from_xdotool  CC=1  out:1
  src.koruide.plugin_installer  [21 funcs]
    _configure_socket_path  CC=8  out:12
    _env_reassert_extension_install  CC=1  out:3
    _extension_is_installed  CC=4  out:5
    _ide_from_terminal_env  CC=1  out:1
    _install_extension_vsix  CC=10  out:14
    _parse_extension_version  CC=4  out:6
    _plugin_package_version  CC=4  out:5
    _reassert_extension_extra  CC=9  out:5
    _repo_root  CC=4  out:4
    _resolve_ide_command  CC=3  out:2
  src.koruide.protocol  [4 funcs]
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koruide.socket  [2 funcs]
    _autopilot_socket_basename  CC=7  out:8
    default_socket_path  CC=4  out:15
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
  src.korudsl.library.library_to_dsl → src.korudsl.library._emit_functions
  src.korudsl.library.library_to_dsl → src.korudsl.library._emit_goals
  src.koruapi.runtime_insights._classify_process → src.koruapi.runtime_insights._looks_project_related
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

Closed-loop automation across semcod/* repositories.
