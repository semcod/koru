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
- **version**: `0.1.219`
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
  version: 0.1.219;
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

## Call Graph

*436 nodes · 500 edges · 76 modules · CC̄=4.0*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 475 | 0 | **475** |
| `list` *(in src.koru.wizard.gui.static.wizard)* | 5 | 96 | 9 | **105** |
| `normalize_ide_id` *(in src.koruide.ide)* | 6 | 43 | 11 | **54** |
| `_select_auto_pipeline_profile` *(in src.koru.autonomous_auto_pipeline)* | 7 | 0 | 54 | **54** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 6 | 47 | **53** |
| `_drive_via_keyboard` *(in src.koruide.daemon.AutopilotDaemon)* | 13 ⚠ | 0 | 50 | **50** |
| `activity` *(in src.koru.activity_log)* | 4 | 40 | 8 | **48** |
| `emit_management_event` *(in src.koru.events)* | 8 | 31 | 7 | **38** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.22s
# nodes: 436 | edges: 500 | modules: 76
# CC̄=4.0

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:475  out:0  total:475
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:96  out:9  total:105
  src.koruide.ide.normalize_ide_id
    CC=6  in:43  out:11  total:54
  src.koru.autonomous_auto_pipeline._select_auto_pipeline_profile
    CC=7  in:0  out:54  total:54
  src.koru.context.render_markdown_handoff
    CC=10  in:6  out:47  total:53
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=13  in:0  out:50  total:50
  src.koru.activity_log.activity
    CC=4  in:40  out:8  total:48
  src.koru.events.emit_management_event
    CC=8  in:31  out:7  total:38
  src.koru.tasks.create_nl_task
    CC=13  in:8  out:29  total:37
  src.koruapi.dashboard.dashboard_main
    CC=23  in:3  out:33  total:36
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  koruapi.mcp_server.tool_run_ticket
    CC=12  in:1  out:31  total:32
  src.koruide.ide.detect_running_ides
    CC=13  in:21  out:10  total:31
  src.koruide.plugin_installer.resolve_extension_vsix
    CC=13  in:2  out:28  total:30
  src.koru.autonomous_auto_pipeline._auto_value
    CC=2  in:24  out:4  total:28
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  src.koru.init.init_project
    CC=7  in:2  out:23  total:25
  src.koruide.socket.default_socket_path
    CC=4  in:10  out:15  total:25
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25

MODULES:
  koruapi.mcp_server  [28 funcs]
    _create_job  CC=1  out:4
    _detect_enabled_gates  CC=5  out:6
    _find_ticket  CC=3  out:1
    _gate_commands  CC=1  out:6
    _get_job_store_path  CC=2  out:1
    _get_process_memory_mb  CC=3  out:2
    _get_python_cmd  CC=1  out:1
    _jsonrpc_error  CC=2  out:0
    _jsonrpc_response  CC=1  out:0
    _launch_oom_monitor  CC=3  out:3
  plugins.koru-autopilot-vscode.src.extension  [2 funcs]
    connect  CC=2  out:7
    next  CC=2  out:1
  scripts.koru-soak-monitor  [1 funcs]
    print  CC=0  out:0
  services.healing-webhook.app  [23 funcs]
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
    activity  CC=4  out:8
    activity_info  CC=5  out:11
  src.koru.agent_backends  [5 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.autonomous  [10 funcs]
    _build_parser  CC=1  out:2
    _create_diagnostic_ticket  CC=1  out:1
    _daemon_activity_log  CC=2  out:3
    _ensure_init  CC=4  out:3
    _handle_cycle_exit_conditions  CC=7  out:4
    _is_topology_enabled  CC=4  out:2
    _plugin_status_decision  CC=1  out:1
    _run_idle_diagnostics  CC=1  out:3
    _status_has_autopilot_plugin  CC=1  out:1
    _stdio_info  CC=1  out:1
  src.koru.autonomous_auto_pipeline  [7 funcs]
    _argv_has_option  CC=5  out:2
    _auto_pipeline_has_pressure  CC=9  out:0
    _auto_pipeline_stage  CC=5  out:1
    _auto_value  CC=2  out:4
    _expand_auto_up_defaults  CC=3  out:3
    _select_auto_pipeline_profile  CC=7  out:54
    _user_option  CC=2  out:1
  src.koru.autonomous_diagnostics  [5 funcs]
    _has_redup_module  CC=2  out:2
    build_idle_checks  CC=11  out:20
    create_diagnostic_ticket  CC=2  out:8
    run_idle_check_loop  CC=6  out:8
    run_idle_diagnostics  CC=3  out:9
  src.koru.autonomous_parser  [1 funcs]
    looks_like_autonomous_up_command  CC=2  out:3
  src.koru.autonomous_process_guard  [2 funcs]
    find_existing_autonomous_processes  CC=11  out:16
    find_existing_wup_processes  CC=11  out:15
  src.koru.autonomous_processes  [12 funcs]
    _ancestor_pids  CC=7  out:8
    _as_managed  CC=1  out:1
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _find_existing_autonomous_processes  CC=11  out:16
    _find_existing_wup_processes  CC=11  out:15
    _looks_like_autonomous_up_command  CC=1  out:1
    _process_cwd  CC=2  out:3
    _stdio_info  CC=1  out:1
    _terminate_existing_processes  CC=10  out:10
  src.koru.autonomy.env  [1 funcs]
    env_truthy  CC=3  out:3
  src.koru.autonomy.phases.utils  [1 funcs]
    is_topology_enabled  CC=4  out:2
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
  src.koru.cli_gate  [2 funcs]
    build_gate_parser  CC=1  out:11
    gate_main  CC=5  out:12
  src.koru.configurator  [1 funcs]
    load_project_config  CC=4  out:5
  src.koru.context  [2 funcs]
    build_context  CC=6  out:16
    render_markdown_handoff  CC=10  out:47
  src.koru.dev_sync  [8 funcs]
    _default_semcod_root  CC=1  out:1
    _is_dirty  CC=2  out:3
    _pull_repo  CC=7  out:4
    _run  CC=1  out:2
    _sync_single_package  CC=11  out:12
    _target_python  CC=3  out:3
    _venv_python  CC=3  out:1
    sync_developer_packages  CC=6  out:7
  src.koru.doctor  [1 funcs]
    run_diagnostics  CC=6  out:11
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.gate  [3 funcs]
    to_note  CC=1  out:2
    _resolve_actor  CC=4  out:1
    authorize_gate  CC=9  out:16
  src.koru.gc_cli_helpers  [4 funcs]
    emit_gc_management_event  CC=2  out:3
    gc_result_to_json  CC=3  out:1
    print_gc_report  CC=2  out:4
    print_gc_text_report  CC=12  out:14
  src.koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
  src.koru.ide_router  [2 funcs]
    is_headless_environment  CC=8  out:6
    resolve_ide_route  CC=10  out:10
  src.koru.init  [1 funcs]
    init_project  CC=7  out:23
  src.koru.local_service  [2 funcs]
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:12
  src.koru.loop  [2 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
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
    planfile_command  CC=5  out:7
  src.koru.queue_clean  [12 funcs]
    to_dict  CC=3  out:8
    _build_close_note  CC=1  out:4
    _candidate_from_ticket  CC=6  out:9
    _cleanable_statuses  CC=2  out:1
    _close_ticket  CC=5  out:6
    _list_tickets  CC=11  out:11
    _matched_rules  CC=14  out:16
    _maybe_skip_active_ticket  CC=3  out:3
    _parse_age_days  CC=8  out:10
    _planfile_base  CC=4  out:3
  src.koru.redup_integration  [1 funcs]
    redup_check_command  CC=1  out:3
  src.koru.runtime  [4 funcs]
    ensure_runs_dir  CC=2  out:5
    planfile_dir  CC=1  out:1
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.stdio_events  [2 funcs]
    default_stdio_format_from_env  CC=3  out:3
    write_stdio_event  CC=2  out:4
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=13  out:29
  src.koru.topology  [4 funcs]
    is_component_enabled  CC=3  out:6
    is_pipeline_enabled  CC=3  out:6
    load_topology  CC=1  out:9
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
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koru.wup_testql_compat  [4 funcs]
    _normalize_args  CC=5  out:15
    _normalize_timeout  CC=4  out:7
    _real_testql  CC=5  out:9
    main  CC=2  out:4
  src.koruapi.cli  [2 funcs]
    _build_parser  CC=2  out:15
    main  CC=11  out:20
  src.koruapi.dashboard  [1 funcs]
    dashboard_main  CC=23  out:33
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
  src.koruide.daemon  [26 funcs]
    __init__  CC=7  out:9
    _accept  CC=6  out:13
    _ack_plugin_event_without_handoff  CC=3  out:4
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=13  out:50
    _execute_handoff  CC=5  out:9
    _forward_handoff_to_plugin  CC=3  out:13
    _handle_ack  CC=10  out:15
    _handle_console_log  CC=14  out:17
    _handle_ping  CC=3  out:4
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
  src.koruide.ide  [38 funcs]
    _active_window_pid_x11  CC=7  out:6
    _auto_profile_candidate_ids  CC=3  out:10
    _candidate_score  CC=1  out:3
    _cursor_terminal_env_hint  CC=3  out:3
    _ide_id_from_process  CC=5  out:4
    _iter_proc_pids  CC=4  out:6
    _known_terminal_ide_hint  CC=3  out:0
    _legacy_windsurf_terminal_env_hint  CC=3  out:4
    _log_drive_target_result  CC=2  out:1
    _matches  CC=7  out:5
  src.koruide.injector  [6 funcs]
    _candidate_backends  CC=11  out:18
    _type_with_backend  CC=1  out:1
    submit_only  CC=9  out:13
    type_text  CC=6  out:8
    _forced_injector_backend  CC=2  out:3
    _submit_key_for  CC=1  out:2
  src.koruide.injector_backends  [11 funcs]
    _log  CC=2  out:1
    _ydotool_submit_command  CC=3  out:0
    extra_enter_count  CC=3  out:4
    press_wtype  CC=4  out:6
    type_with_backend  CC=5  out:10
    type_with_wtype  CC=3  out:8
    type_with_xdotool  CC=3  out:8
    type_with_ydotool  CC=5  out:12
    ydotool_ctrl_keycode  CC=2  out:3
    ydotool_enter_keycode  CC=2  out:3
  src.koruide.os_injector  [28 funcs]
    _clipboard_backend  CC=3  out:2
    _cmd_timeout_seconds  CC=3  out:4
    _focus_profile_chat  CC=7  out:10
    _inject_profile_text  CC=7  out:12
    _injection_result  CC=1  out:0
    _is_wayland_session  CC=1  out:3
    _os_injector_skip_reason  CC=6  out:4
    _post_focus_delay_seconds  CC=3  out:5
    _read_json  CC=4  out:5
    _resolve_input_method  CC=7  out:4
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
  src.koruide.plugin_router  [1 funcs]
    plugin_for  CC=6  out:6
  src.koruide.protocol  [5 funcs]
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    chat_send  CC=1  out:1
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koruide.socket  [2 funcs]
    _autopilot_socket_basename  CC=7  out:8
    default_socket_path  CC=4  out:15
  src.koruide.utils  [1 funcs]
    resolve_xdg_path  CC=2  out:3
  src.korumesh.codec  [2 funcs]
    envelope_from_wire  CC=1  out:11
    envelope_to_wire  CC=1  out:3
  src.korumesh.envelope  [3 funcs]
    _canonical_header  CC=1  out:2
    sign_envelope  CC=3  out:8
    verify_envelope  CC=1  out:2
  src.korumesh.transport  [4 funcs]
    _relay_client  CC=9  out:10
    _require_websockets  CC=2  out:1
    publish_envelope  CC=4  out:9
    run_relay  CC=1  out:5

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
  services.healing-webhook.app.get_history → src.koru.wizard.gui.static.wizard.list
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
# generated in 0.22s
# nodes: 436 | edges: 500 | modules: 76
# CC̄=4.0

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:475  out:0  total:475
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:96  out:9  total:105
  src.koruide.ide.normalize_ide_id
    CC=6  in:43  out:11  total:54
  src.koru.autonomous_auto_pipeline._select_auto_pipeline_profile
    CC=7  in:0  out:54  total:54
  src.koru.context.render_markdown_handoff
    CC=10  in:6  out:47  total:53
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=13  in:0  out:50  total:50
  src.koru.activity_log.activity
    CC=4  in:40  out:8  total:48
  src.koru.events.emit_management_event
    CC=8  in:31  out:7  total:38
  src.koru.tasks.create_nl_task
    CC=13  in:8  out:29  total:37
  src.koruapi.dashboard.dashboard_main
    CC=23  in:3  out:33  total:36
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  koruapi.mcp_server.tool_run_ticket
    CC=12  in:1  out:31  total:32
  src.koruide.ide.detect_running_ides
    CC=13  in:21  out:10  total:31
  src.koruide.plugin_installer.resolve_extension_vsix
    CC=13  in:2  out:28  total:30
  src.koru.autonomous_auto_pipeline._auto_value
    CC=2  in:24  out:4  total:28
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  src.koru.init.init_project
    CC=7  in:2  out:23  total:25
  src.koruide.socket.default_socket_path
    CC=4  in:10  out:15  total:25
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25

MODULES:
  koruapi.mcp_server  [28 funcs]
    _create_job  CC=1  out:4
    _detect_enabled_gates  CC=5  out:6
    _find_ticket  CC=3  out:1
    _gate_commands  CC=1  out:6
    _get_job_store_path  CC=2  out:1
    _get_process_memory_mb  CC=3  out:2
    _get_python_cmd  CC=1  out:1
    _jsonrpc_error  CC=2  out:0
    _jsonrpc_response  CC=1  out:0
    _launch_oom_monitor  CC=3  out:3
  plugins.koru-autopilot-vscode.src.extension  [2 funcs]
    connect  CC=2  out:7
    next  CC=2  out:1
  scripts.koru-soak-monitor  [1 funcs]
    print  CC=0  out:0
  services.healing-webhook.app  [23 funcs]
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
    activity  CC=4  out:8
    activity_info  CC=5  out:11
  src.koru.agent_backends  [5 funcs]
    _parse_lane  CC=8  out:14
    get_agent_backend_profile  CC=3  out:1
    load_agent_integration_config  CC=11  out:18
    normalize_agent_backend_id  CC=4  out:3
    validate_agent_integration_config  CC=5  out:4
  src.koru.autonomous  [10 funcs]
    _build_parser  CC=1  out:2
    _create_diagnostic_ticket  CC=1  out:1
    _daemon_activity_log  CC=2  out:3
    _ensure_init  CC=4  out:3
    _handle_cycle_exit_conditions  CC=7  out:4
    _is_topology_enabled  CC=4  out:2
    _plugin_status_decision  CC=1  out:1
    _run_idle_diagnostics  CC=1  out:3
    _status_has_autopilot_plugin  CC=1  out:1
    _stdio_info  CC=1  out:1
  src.koru.autonomous_auto_pipeline  [7 funcs]
    _argv_has_option  CC=5  out:2
    _auto_pipeline_has_pressure  CC=9  out:0
    _auto_pipeline_stage  CC=5  out:1
    _auto_value  CC=2  out:4
    _expand_auto_up_defaults  CC=3  out:3
    _select_auto_pipeline_profile  CC=7  out:54
    _user_option  CC=2  out:1
  src.koru.autonomous_diagnostics  [5 funcs]
    _has_redup_module  CC=2  out:2
    build_idle_checks  CC=11  out:20
    create_diagnostic_ticket  CC=2  out:8
    run_idle_check_loop  CC=6  out:8
    run_idle_diagnostics  CC=3  out:9
  src.koru.autonomous_parser  [1 funcs]
    looks_like_autonomous_up_command  CC=2  out:3
  src.koru.autonomous_process_guard  [2 funcs]
    find_existing_autonomous_processes  CC=11  out:16
    find_existing_wup_processes  CC=11  out:15
  src.koru.autonomous_processes  [12 funcs]
    _ancestor_pids  CC=7  out:8
    _as_managed  CC=1  out:1
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _find_existing_autonomous_processes  CC=11  out:16
    _find_existing_wup_processes  CC=11  out:15
    _looks_like_autonomous_up_command  CC=1  out:1
    _process_cwd  CC=2  out:3
    _stdio_info  CC=1  out:1
    _terminate_existing_processes  CC=10  out:10
  src.koru.autonomy.env  [1 funcs]
    env_truthy  CC=3  out:3
  src.koru.autonomy.phases.utils  [1 funcs]
    is_topology_enabled  CC=4  out:2
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
  src.koru.cli_gate  [2 funcs]
    build_gate_parser  CC=1  out:11
    gate_main  CC=5  out:12
  src.koru.configurator  [1 funcs]
    load_project_config  CC=4  out:5
  src.koru.context  [2 funcs]
    build_context  CC=6  out:16
    render_markdown_handoff  CC=10  out:47
  src.koru.dev_sync  [8 funcs]
    _default_semcod_root  CC=1  out:1
    _is_dirty  CC=2  out:3
    _pull_repo  CC=7  out:4
    _run  CC=1  out:2
    _sync_single_package  CC=11  out:12
    _target_python  CC=3  out:3
    _venv_python  CC=3  out:1
    sync_developer_packages  CC=6  out:7
  src.koru.doctor  [1 funcs]
    run_diagnostics  CC=6  out:11
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.gate  [3 funcs]
    to_note  CC=1  out:2
    _resolve_actor  CC=4  out:1
    authorize_gate  CC=9  out:16
  src.koru.gc_cli_helpers  [4 funcs]
    emit_gc_management_event  CC=2  out:3
    gc_result_to_json  CC=3  out:1
    print_gc_report  CC=2  out:4
    print_gc_text_report  CC=12  out:14
  src.koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
  src.koru.ide_router  [2 funcs]
    is_headless_environment  CC=8  out:6
    resolve_ide_route  CC=10  out:10
  src.koru.init  [1 funcs]
    init_project  CC=7  out:23
  src.koru.local_service  [2 funcs]
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:12
  src.koru.loop  [2 funcs]
    _search_root_for_include  CC=6  out:6
    discover_repositories  CC=5  out:11
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
    planfile_command  CC=5  out:7
  src.koru.queue_clean  [12 funcs]
    to_dict  CC=3  out:8
    _build_close_note  CC=1  out:4
    _candidate_from_ticket  CC=6  out:9
    _cleanable_statuses  CC=2  out:1
    _close_ticket  CC=5  out:6
    _list_tickets  CC=11  out:11
    _matched_rules  CC=14  out:16
    _maybe_skip_active_ticket  CC=3  out:3
    _parse_age_days  CC=8  out:10
    _planfile_base  CC=4  out:3
  src.koru.redup_integration  [1 funcs]
    redup_check_command  CC=1  out:3
  src.koru.runtime  [4 funcs]
    ensure_runs_dir  CC=2  out:5
    planfile_dir  CC=1  out:1
    runs_dir  CC=1  out:1
    runtime_dir  CC=1  out:1
  src.koru.scan  [1 funcs]
    run_scan  CC=10  out:15
  src.koru.stdio_events  [2 funcs]
    default_stdio_format_from_env  CC=3  out:3
    write_stdio_event  CC=2  out:4
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=13  out:29
  src.koru.topology  [4 funcs]
    is_component_enabled  CC=3  out:6
    is_pipeline_enabled  CC=3  out:6
    load_topology  CC=1  out:9
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
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koru.wup_testql_compat  [4 funcs]
    _normalize_args  CC=5  out:15
    _normalize_timeout  CC=4  out:7
    _real_testql  CC=5  out:9
    main  CC=2  out:4
  src.koruapi.cli  [2 funcs]
    _build_parser  CC=2  out:15
    main  CC=11  out:20
  src.koruapi.dashboard  [1 funcs]
    dashboard_main  CC=23  out:33
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
  src.koruide.daemon  [26 funcs]
    __init__  CC=7  out:9
    _accept  CC=6  out:13
    _ack_plugin_event_without_handoff  CC=3  out:4
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=13  out:50
    _execute_handoff  CC=5  out:9
    _forward_handoff_to_plugin  CC=3  out:13
    _handle_ack  CC=10  out:15
    _handle_console_log  CC=14  out:17
    _handle_ping  CC=3  out:4
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
  src.koruide.ide  [38 funcs]
    _active_window_pid_x11  CC=7  out:6
    _auto_profile_candidate_ids  CC=3  out:10
    _candidate_score  CC=1  out:3
    _cursor_terminal_env_hint  CC=3  out:3
    _ide_id_from_process  CC=5  out:4
    _iter_proc_pids  CC=4  out:6
    _known_terminal_ide_hint  CC=3  out:0
    _legacy_windsurf_terminal_env_hint  CC=3  out:4
    _log_drive_target_result  CC=2  out:1
    _matches  CC=7  out:5
  src.koruide.injector  [6 funcs]
    _candidate_backends  CC=11  out:18
    _type_with_backend  CC=1  out:1
    submit_only  CC=9  out:13
    type_text  CC=6  out:8
    _forced_injector_backend  CC=2  out:3
    _submit_key_for  CC=1  out:2
  src.koruide.injector_backends  [11 funcs]
    _log  CC=2  out:1
    _ydotool_submit_command  CC=3  out:0
    extra_enter_count  CC=3  out:4
    press_wtype  CC=4  out:6
    type_with_backend  CC=5  out:10
    type_with_wtype  CC=3  out:8
    type_with_xdotool  CC=3  out:8
    type_with_ydotool  CC=5  out:12
    ydotool_ctrl_keycode  CC=2  out:3
    ydotool_enter_keycode  CC=2  out:3
  src.koruide.os_injector  [28 funcs]
    _clipboard_backend  CC=3  out:2
    _cmd_timeout_seconds  CC=3  out:4
    _focus_profile_chat  CC=7  out:10
    _inject_profile_text  CC=7  out:12
    _injection_result  CC=1  out:0
    _is_wayland_session  CC=1  out:3
    _os_injector_skip_reason  CC=6  out:4
    _post_focus_delay_seconds  CC=3  out:5
    _read_json  CC=4  out:5
    _resolve_input_method  CC=7  out:4
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
  src.koruide.plugin_router  [1 funcs]
    plugin_for  CC=6  out:6
  src.koruide.protocol  [5 funcs]
    _filter_extras  CC=6  out:4
    ack  CC=2  out:2
    chat_send  CC=1  out:1
    decode  CC=12  out:21
    error  CC=1  out:1
  src.koruide.socket  [2 funcs]
    _autopilot_socket_basename  CC=7  out:8
    default_socket_path  CC=4  out:15
  src.koruide.utils  [1 funcs]
    resolve_xdg_path  CC=2  out:3
  src.korumesh.codec  [2 funcs]
    envelope_from_wire  CC=1  out:11
    envelope_to_wire  CC=1  out:3
  src.korumesh.envelope  [3 funcs]
    _canonical_header  CC=1  out:2
    sign_envelope  CC=3  out:8
    verify_envelope  CC=1  out:2
  src.korumesh.transport  [4 funcs]
    _relay_client  CC=9  out:10
    _require_websockets  CC=2  out:1
    publish_envelope  CC=4  out:9
    run_relay  CC=1  out:5

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
  services.healing-webhook.app.get_history → src.koru.wizard.gui.static.wizard.list
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
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 340f 57629L | python:241,shell:44,yaml:15,json:9,yml:8,typescript:8,kotlin:6,txt:2,javascript:1,properties:1,xml:1,toml:1 | 2026-05-22
# generated in 0.13s
# CC̄=4.0 | critical:11/2198 | dups:0 | cycles:0

HEALTH[12]:
  🔴 GOD   src/koru/wizard/cli.py = 815L, 4 classes, 26m, max CC=29
  🟡 CC    dashboard_main CC=23 (limit:15)
  🟡 CC    wizard_main CC=29 (limit:15)
  🟡 CC    load_tree CC=25 (limit:15)
  🟡 CC    submitChat CC=16 (limit:15)
  🟡 CC    doctor_main CC=15 (limit:15)
  🟡 CC    configure_project CC=20 (limit:15)
  🟡 CC    _check_autopilot_plugin_bundle CC=23 (limit:15)
  🟡 CC    _check_autopilot_env CC=17 (limit:15)
  🟡 CC    _check_autopilot_chat_control CC=49 (limit:15)
  🟡 CC    _check_windsurf_chat_column_control CC=25 (limit:15)
  🟡 CC    _check_ide_console_log CC=31 (limit:15)

REFACTOR[2]:
  1. split src/koru/wizard/cli.py  (god module)
  2. split 11 high-CC methods  (CC>15)

PIPELINES[619]:
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
  services/                       CC̄=4.9    ←in:0  →out:0
  │ !! app                        702L  0C   27m  CC=11     ←0
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │
  src/                            CC̄=4.1    ←in:0  →out:0
  │ !! doctor                    1906L  3C   68m  CC=49     ←2
  │ !! autonomous_cycle          1367L  1C   44m  CC=14     ←1
  │ !! context                   1269L  0C   49m  CC=14     ←8
  │ !! daemon                    1149L  3C   49m  CC=14     ←0
  │ !! autonomous                1119L  1C   56m  CC=7      ←2
  │ !! mcp_server                1023L  0C   35m  CC=14     ←4
  │ !! scan                       991L  2C   27m  CC=13     ←4
  │ !! cli_command                886L  0C   22m  CC=14     ←0
  │ !! operator_pipeline          862L  2C   31m  CC=12     ←0
  │ !! cli                        815L  4C   26m  CC=29     ←2
  │ !! ide                        746L  1C   44m  CC=13     ←22
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←0
  │ !! install_manager            653L  2C   30m  CC=13     ←2
  │ !! init                       610L  1C   15m  CC=12     ←2
  │ !! autonomous_wup             585L  3C   30m  CC=12     ←1
  │ !! autonomous_startup         577L  3C   31m  CC=9      ←3
  │ !! cli_cleaned                564L  0C   41m  CC=14     ←0
  │ !! plugin_installer           535L  1C   25m  CC=13     ←3
  │ os_injector                483L  2C   29m  CC=9      ←2
  │ context_render             472L  0C   18m  CC=14     ←0
  │ !! configurator               453L  2C   23m  CC=20     ←6
  │ bootstrap                  452L  2C   19m  CC=10     ←3
  │ install_plugin_cli         451L  0C   18m  CC=10     ←0
  │ mcp_provision              449L  0C   24m  CC=10     ←5
  │ autonomous_parser          449L  0C    3m  CC=14     ←2
  │ topology                   414L  1C   15m  CC=12     ←9
  │ runner                     393L  0C   10m  CC=14     ←2
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ post_run_verify            381L  2C   16m  CC=14     ←3
  │ injector                   376L  3C   20m  CC=11     ←0
  │ gc                         371L  2C   12m  CC=11     ←1
  │ env                        360L  0C   16m  CC=12     ←4
  │ tasks                      338L  1C   20m  CC=13     ←8
  │ dashboard_routes           336L  0C    4m  CC=1      ←2
  │ agents                     335L  1C   16m  CC=14     ←4
  │ !! tree                       323L  5C   16m  CC=25     ←3
  │ autonomous_runtime         322L  1C   12m  CC=13     ←3
  │ capture_mss                322L  1C   21m  CC=13     ←2
  │ tools                      318L  0C   19m  CC=11     ←3
  │ strategies.json            315L  0C    0m  CC=0.0    ←0
  │ autonomous_processes       314L  2C   12m  CC=11     ←1
  │ init_host_environment      314L  0C   17m  CC=9      ←1
  │ local_service              312L  1C    7m  CC=7      ←1
  │ ide_work                   301L  0C   11m  CC=12     ←3
  │ app                        299L  0C    9m  CC=10     ←1
  │ local_manager_state        292L  4C   21m  CC=14     ←0
  │ wizard.js                  292L  0C   38m  CC=13     ←51
  │ queue_cli_helpers          290L  0C   10m  CC=9      ←1
  │ lifecycle                  285L  1C   13m  CC=10     ←1
  │ autonomous_daemon          282L  0C   10m  CC=10     ←1
  │ autonomous_diagnostics     262L  0C    8m  CC=11     ←1
  │ policy                     262L  1C   10m  CC=9      ←2
  │ autonomous_auto_pipeline   253L  2C    9m  CC=9      ←1
  │ protocol                   252L  2C   14m  CC=12     ←3
  │ local_manager_client       252L  2C   15m  CC=7      ←4
  │ git_cli                    249L  0C   13m  CC=11     ←0
  │ runners                    249L  0C   11m  CC=9      ←2
  │ dashboard_serve_utils      246L  1C   18m  CC=7      ←2
  │ drive_orchestrator         245L  1C   12m  CC=14     ←0
  │ environment                245L  3C    6m  CC=14     ←2
  │ dashboard_serve            240L  1C   10m  CC=6      ←1
  │ autonomous_onboarding      231L  1C   11m  CC=10     ←0
  │ dashboard_tickets          229L  0C   10m  CC=13     ←1
  │ host_setup                 226L  0C   12m  CC=14     ←2
  │ ide                        216L  1C    6m  CC=10     ←3
  │ dashboard                  214L  0C    5m  CC=4      ←1
  │ dev_sync                   213L  1C    9m  CC=11     ←0
  │ agent_backends             212L  3C    7m  CC=11     ←4
  │ calibrate_cli              210L  0C    5m  CC=13     ←0
  │ library                    207L  0C   19m  CC=9      ←1
  │ injector_backends          207L  0C   11m  CC=5      ←1
  │ autonomous_process_guard   206L  2C    8m  CC=11     ←1
  │ autonomous_plugin          203L  0C   14m  CC=12     ←2
  │ gate                       202L  1C    5m  CC=12     ←1
  │ invoke_handlers            199L  1C   15m  CC=5      ←0
  │ integrations               198L  1C    2m  CC=4      ←4
  │ autonomous_cycle_config    194L  0C    5m  CC=9      ←0
  │ templates                  194L  1C   12m  CC=9      ←1
  │ runtime_insights           190L  0C    6m  CC=9      ←1
  │ redup_integration          189L  0C   11m  CC=3      ←2
  │ cli_task                   189L  0C    5m  CC=11     ←0
  │ cli_queue                  185L  0C    4m  CC=12     ←0
  │ agent_backend_runtime      180L  5C    6m  CC=9      ←0
  │ server                     175L  1C    8m  CC=9      ←1
  │ ide_client                 171L  2C   12m  CC=3      ←1
  │ queue_phase                170L  0C    6m  CC=11     ←0
  │ activity_log               166L  0C    9m  CC=8      ←19
  │ scan_phase                 166L  0C    2m  CC=9      ←0
  │ ticket                     164L  0C    8m  CC=10     ←6
  │ diagnostics                163L  0C    8m  CC=8      ←1
  │ client                     160L  1C    8m  CC=8      ←1
  │ project                    160L  1C   11m  CC=7      ←3
  │ autonomous_cycle_gate      158L  0C    8m  CC=8      ←2
  │ openapi                    155L  0C    1m  CC=2      ←1
  │ audit                      154L  2C    6m  CC=6      ←1
  │ doctor_cli                 152L  0C    9m  CC=8      ←1
  │ project_pipeline           150L  0C    5m  CC=9      ←5
  │ semcod_tools               148L  1C    4m  CC=7      ←3
  │ git_attribution            147L  1C    6m  CC=9      ←2
  │ autonomous_operator        144L  0C    4m  CC=7      ←0
  │ daemon_cli                 142L  0C    7m  CC=10     ←0
  │ !! cli_doctor                 139L  0C    5m  CC=15     ←0
  │ autonomous_checkpoint      137L  0C    7m  CC=11     ←2
  │ local_manager              136L  1C    6m  CC=5      ←1
  │ !! dashboard                  132L  0C    4m  CC=23     ←3
  │ loop                       131L  3C    4m  CC=12     ←2
  │ cli_scan                   129L  0C    4m  CC=7      ←0
  │ cli                        128L  0C    3m  CC=11     ←0
  │ llx                        128L  1C    4m  CC=14     ←2
  │ config                     123L  1C    6m  CC=7      ←1
  │ run_log                    123L  1C    7m  CC=4      ←5
  │ config                     123L  1C    1m  CC=4      ←0
  │ cli                        123L  0C    9m  CC=3      ←0
  │ cli_topology               122L  0C    3m  CC=12     ←0
  │ cli_init                   120L  0C    3m  CC=7      ←0
  │ portal_capture             118L  1C    2m  CC=8      ←1
  │ capture_fallback           118L  0C    9m  CC=6      ←1
  │ cli_gate                   116L  0C    2m  CC=5      ←0
  │ heal                       116L  1C    3m  CC=5      ←1
  │ dashboard_projects         116L  0C    7m  CC=8      ←2
  │ loop                       115L  0C    1m  CC=14     ←4
  │ session                    112L  2C    8m  CC=4      ←0
  │ ide_router                 105L  1C    2m  CC=10     ←5
  │ runtime                    104L  0C    5m  CC=2      ←7
  │ dotenv_loader              104L  0C    3m  CC=7      ←0
  │ web-app.json               104L  0C    0m  CC=0.0    ←0
  │ systemd_cli                103L  0C    4m  CC=6      ←0
  │ prompts                    101L  1C    1m  CC=10     ←1
  │ capture                     98L  1C    5m  CC=4      ←2
  │ dashboard_config            94L  1C    4m  CC=11     ←1
  │ watch                       93L  0C    6m  CC=9      ←1
  │ events                      90L  0C    2m  CC=8      ←14
  │ autonomous_resources        90L  0C    1m  CC=4      ←0
  │ cli_agent                   90L  0C    3m  CC=3      ←0
  │ dashboard_state             90L  0C    4m  CC=7      ←3
  │ transport                   88L  0C    4m  CC=9      ←2
  │ autoloop_cli                88L  0C    4m  CC=8      ←0
  │ types                       88L  5C    1m  CC=2      ←0
  │ agent_cli_helpers           87L  0C    3m  CC=10     ←2
  │ cli_gc                      87L  0C    2m  CC=1      ←0
  │ plugin_router               86L  3C    5m  CC=6      ←0
  │ locking                     86L  0C    4m  CC=4      ←1
  │ envelope                    85L  1C    4m  CC=3      ←3
  │ cli                         81L  0C    3m  CC=11     ←1
  │ gc_cli_helpers              81L  0C    5m  CC=12     ←1
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ cli_runtime_context         79L  0C    3m  CC=14     ←0
  │ mesh                        77L  0C    5m  CC=8      ←1
  │ cli_auto                    76L  0C    4m  CC=9      ←0
  │ topology_cli                75L  1C    4m  CC=8      ←1
  │ cli                         75L  0C    4m  CC=5      ←0
  │ autonomous_cli_config       74L  0C    4m  CC=5      ←0
  │ tail_cli                    73L  0C    4m  CC=6      ←0
  │ server                      73L  0C    3m  CC=4      ←1
  │ cli_tools                   73L  0C    2m  CC=7      ←0
  │ __init__                    73L  0C    2m  CC=4      ←0
  │ shell_evidence              72L  0C    2m  CC=7      ←1
  │ cli_serve                   72L  0C    2m  CC=1      ←0
  │ transform                   70L  0C    4m  CC=12     ←2
  │ cli_bootstrap               70L  0C    1m  CC=5      ←0
  │ __init__                    69L  0C    0m  CC=0.0    ←0
  │ topology_post               68L  0C    1m  CC=14     ←1
  │ agent                       68L  0C    4m  CC=12     ←1
  │ store_persistence           68L  0C    4m  CC=8      ←1
  │ local_manager               67L  0C    2m  CC=2      ←1
  │ __init__                    67L  0C    0m  CC=0.0    ←0
  │ wup_testql_compat           64L  0C    4m  CC=5      ←0
  │ cli_agent_backends          61L  0C    1m  CC=8      ←0
  │ store                       60L  0C    4m  CC=6      ←1
  │ cli_parser                  58L  0C    4m  CC=3      ←1
  │ client_helpers              57L  0C    2m  CC=4      ←2
  │ cli_commands                56L  0C    3m  CC=3      ←1
  │ planfile_ticket_note        55L  0C    2m  CC=5      ←1
  │ library.json                55L  0C    0m  CC=0.0    ←0
  │ ml-research.json            55L  0C    0m  CC=0.0    ←0
  │ cli-tool.json               55L  0C    0m  CC=0.0    ←0
  │ cli_local_serve             53L  0C    2m  CC=1      ←0
  │ cli_ide_router              53L  0C    1m  CC=3      ←0
  │ scaling                     52L  0C    3m  CC=6      ←2
  │ dashboard_parse             51L  0C    3m  CC=6      ←1
  │ capture_probe               50L  0C    2m  CC=7      ←1
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ protocol                    48L  0C    0m  CC=0.0    ←0
  │ __init__                    47L  0C    0m  CC=0.0    ←0
  │ refactor_planfile_handoff    46L  0C    1m  CC=6      ←2
  │ dashboard_http              46L  1C    5m  CC=4      ←0
  │ verify_phase                45L  0C    1m  CC=5      ←0
  │ socket                      44L  0C    2m  CC=7      ←7
  │ ide_runtime                 44L  0C    2m  CC=5      ←1
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ cli_watch                   41L  0C    1m  CC=2      ←0
  │ cli_parser                  41L  0C    4m  CC=2      ←1
  │ registry.json               41L  0C    0m  CC=0.0    ←0
  │ subprocess_runner           40L  0C    3m  CC=3      ←5
  │ dashboard_runtime           40L  0C    3m  CC=5      ←1
  │ bootstrap                   38L  0C    3m  CC=3      ←1
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ codec                       37L  0C    2m  CC=1      ←2
  │ local                       36L  0C    2m  CC=6      ←3
  │ planfile_queue              36L  0C    0m  CC=0.0    ←0
  │ cli_refactor_planfile_handoff    35L  0C    1m  CC=1      ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ human                       31L  0C    1m  CC=5      ←0
  │ cli_parser                  31L  0C    1m  CC=1      ←1
  │ cli_context                 31L  0C    1m  CC=2      ←0
  │ utils                       30L  0C    2m  CC=4      ←3
  │ cli                         27L  0C    1m  CC=5      ←0
  │ autonomous_env              25L  0C    1m  CC=1      ←0
  │ keys                        25L  0C    2m  CC=3      ←4
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ state                       24L  1C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ dashboard_topology          22L  0C    2m  CC=1      ←1
  │ utils                       21L  0C    1m  CC=2      ←2
  │ paths                       21L  0C    4m  CC=1      ←2
  │ dashboard_context           18L  0C    2m  CC=1      ←1
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←2
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ injector_errors             10L  1C    0m  CC=0.0    ←0
  │ client                      10L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ injector                     9L  0C    0m  CC=0.0    ←0
  │ os_injector                  9L  0C    0m  CC=0.0    ←0
  │ audit                        9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ plugin_version               8L  0C    0m  CC=0.0    ←0
  │ __main__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __main__                     6L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ cli                          0L  0C   16m  CC=11     ←0
  │ commands                     0L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=3.0    ←in:0  →out:0
  │ !! extension.ts              1310L  2C  121m  CC=16     ←13
  │ probe-ladder.ts            271L  3C   23m  CC=9      ←0
  │ package.json               149L  0C    0m  CC=0.0    ←0
  │ KoruAutopilotService.kt    136L  1C    5m  CC=0.0    ←0
  │ probe-ladder.test.ts       122L  0C   15m  CC=2      ←0
  │ dispatch-plan.test.ts      118L  0C   12m  CC=4      ←0
  │ socketPath.ts               61L  0C   14m  CC=9      ←0
  │ build.gradle.kts            49L  0C    4m  CC=0.0    ←0
  │ antigravity-fastpath.test.ts    39L  0C    8m  CC=2      ←0
  │ SocketPath.kt               33L  0C    0m  CC=0.0    ←0
  │ dispatch-plan.ts            26L  1C    1m  CC=7      ←0
  │ plugin.xml                  24L  0C    0m  CC=0.0    ←0
  │ antigravity-fastpath.ts     20L  0C    2m  CC=3      ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │ ChatInjector.kt             11L  1C    0m  CC=0.0    ←0
  │ KoruAutopilotReconnectAction.kt    10L  1C    0m  CC=0.0    ←0
  │ settings.gradle.kts          8L  0C    2m  CC=0.0    ←0
  │ gradle.properties            6L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=2.2    ←in:460  →out:0
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ planfile-sync-todo         260L  0C   12m  CC=14     ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←71
  │ koru-queue-diagnose.sh     124L  0C    0m  CC=0.0    ←0
  │ koru-soak-stop.sh          123L  0C    5m  CC=0.0    ←0
  │ koru-soak-status.sh        100L  0C    6m  CC=0.0    ←0
  │ koru-semcod-gates.sh        99L  0C    2m  CC=0.0    ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ docker-ide-matrix.sh        92L  0C    2m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←0
  │ docker-ide-matrix-entrypoint.sh    74L  0C    1m  CC=0.0    ←0
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │ koru-soak-start.sh          39L  0C    1m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1319L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               912L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  511L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             194L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ wup.yaml                   130L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ project.sh                  54L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
  │ output.txt                   3L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
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
     src/koru/cli.py                           0L
     src/koru/cli/commands.py                  0L

COUPLING:
                                                      src.koru                        scripts                    src.koruide                    src.koruapi                        koruapi                src.koruobserve  plugins.koru-autopilot-vscode                 src.koruvision                   src.korumesh                           koru                    src.korudsl       services.healing-webhook
                       src.koru                             ──                            391                             91                              7                            ←10                             ←8                             14                             ←4                             ←2                             ←6                              1                             ←1  hub
                        scripts                           ←391                             ──                            ←27                            ←15                             ←2                             ←9                                                            ←9                             ←7                                                                                               hub
                    src.koruide                              8                             27                             ──                             ←6                             17                                                             1                                                                                                                                                             hub
                    src.koruapi                             50                             15                              6                             ──                              4                                                             2                                                             1                                                             4                                 hub
                        koruapi                             10                              2                            ←17                             ←4                             ──                                                                                                                                                                                                                           hub
                src.koruobserve                              8                              9                                                                                                                          ──                                                             2                              1                                                                                               !! fan-out
  plugins.koru-autopilot-vscode                            ←14                                                            ←1                             ←2                                                                                           ──                                                                                                                                                         ←1  hub
                 src.koruvision                              4                              9                                                                                                                          ←2                                                            ──                              3                                                                                               !! fan-out
                   src.korumesh                              2                              7                                                            ←1                                                             1                                                            ←3                             ──                                                                                               hub
                           koru                              6                                                                                                                                                                                                                                                                                     ──                                                              
                    src.korudsl                             ←1                                                                                           ←4                                                                                                                                                                                                                       ──                                 hub
       services.healing-webhook                              1                                                                                                                                                                                         1                                                                                                                                                         ──
  CYCLES: none
  HUB: src.korumesh/ (fan-in=5)
  HUB: koruapi/ (fan-in=21)
  HUB: plugins.koru-autopilot-vscode/ (fan-in=18)
  HUB: src.koru/ (fan-in=89)
  HUB: src.korudsl/ (fan-in=5)
  HUB: src.koruapi/ (fan-in=7)
  HUB: src.koruide/ (fan-in=97)
  HUB: scripts/ (fan-in=460)
  SMELL: src.korumesh/ fan-out=10 → split needed
  SMELL: koruapi/ fan-out=12 → split needed
  SMELL: src.koruobserve/ fan-out=20 → split needed
  SMELL: src.koru/ fan-out=504 → split needed
  SMELL: src.koruapi/ fan-out=82 → split needed
  SMELL: src.koruide/ fan-out=53 → split needed
  SMELL: src.koruvision/ fan-out=16 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 86 groups | 239f 46297L | 2026-05-22

SUMMARY:
  files_scanned: 239
  total_lines:   46297
  dup_groups:    86
  dup_fragments: 200
  saved_lines:   1495
  scan_ms:       3807

HOTSPOTS[7] (files with most duplication):
  src/koru/cli_cleaned.py  dup=423L  groups=32  frags=37  (0.9%)
  src/koru/cli.py  dup=390L  groups=12  frags=13  (0.8%)
  src/koru/context.py  dup=350L  groups=15  frags=15  (0.8%)
  src/koru/context_render.py  dup=350L  groups=15  frags=15  (0.8%)
  src/koru/cli_task.py  dup=163L  groups=5  frags=5  (0.4%)
  src/koru/autonomous_cycle.py  dup=70L  groups=7  frags=8  (0.2%)
  src/koru/cli_agent.py  dup=65L  groups=2  frags=2  (0.1%)

DUPLICATES[86] (ranked by impact):
  [579236582ebaa45b] !! STRU  _build_parser  L=231 N=2 saved=231 sim=1.00
      src/koru/cli.py:92-322  (_build_parser)
      src/koru/cli_cleaned.py:67-102  (_build_parser)
  [3116e8f45fd387a5] ! STRU  agent_backends_main  L=57 N=2 saved=57 sim=1.00
      src/koru/cli_agent_backends.py:5-61  (agent_backends_main)
      src/koru/cli_cleaned.py:311-344  (_agent_backends_main)
  [239d5ce19c57d14b] ! STRU  _bootstrap_main  L=52 N=2 saved=52 sim=1.00
      src/koru/cli_bootstrap.py:17-68  (_bootstrap_main)
      src/koru/cli_cleaned.py:472-490  (_bootstrap_main)
  [10c17ef3fe2abcf5] ! STRU  _build_agent_parser  L=49 N=2 saved=49 sim=1.00
      src/koru/cli_agent.py:23-71  (_build_agent_parser)
      src/koru/cli_cleaned.py:163-175  (_build_agent_parser)
  [0533d81be7d5abf8] ! STRU  render_markdown_handoff  L=44 N=2 saved=44 sim=1.00
      src/koru/context.py:1226-1269  (render_markdown_handoff)
      src/koru/context_render.py:429-472  (render_markdown_handoff)
  [58dad341d84a573e] ! STRU  _render_gates  L=40 N=2 saved=40 sim=1.00
      src/koru/context.py:1049-1088  (_render_gates)
      src/koru/context_render.py:252-291  (render_gates)
  [881c2887af3e09d4] ! STRU  _command_loop_main  L=38 N=2 saved=38 sim=1.00
      src/koru/cli.py:505-542  (_command_loop_main)
      src/koru/cli_cleaned.py:492-502  (_command_loop_main)
  [077cfa61a2943c36] ! STRU  _dsl_main  L=4 N=10 saved=36 sim=1.00
      src/koru/cli.py:385-388  (_dsl_main)
      src/koru/cli.py:391-394  (_api_main)
      src/koru/cli_cleaned.py:238-240  (_serve_main)
      src/koru/cli_cleaned.py:242-244  (_local_serve_main)
      src/koru/cli_cleaned.py:307-309  (_mcp_serve_main)
      src/koru/cli_cleaned.py:346-348  (_init_ide_main)
      src/koru/cli_cleaned.py:378-380  (_dsl_main)
      src/koru/cli_cleaned.py:382-384  (_api_main)
      src/koru/cli_local_serve.py:48-51  (_local_serve_main)
      src/koru/cli_serve.py:67-70  (_serve_main)
  [babc6b538274c771]   STRU  _render_semcod_tools  L=30 N=2 saved=30 sim=1.00
      src/koru/context.py:944-973  (_render_semcod_tools)
      src/koru/context_render.py:147-176  (render_semcod_tools)
  [400f9f906a729d1a]   STRU  provision_cursor  L=15 N=3 saved=30 sim=1.00
      src/koru/mcp_provision.py:205-219  (provision_cursor)
      src/koru/mcp_provision.py:222-236  (provision_vscode)
      src/koru/mcp_provision.py:246-260  (provision_zed)
  [c085354dd89d3aee]   STRU  _render_project_pipeline  L=28 N=2 saved=28 sim=1.00
      src/koru/context.py:1091-1118  (_render_project_pipeline)
      src/koru/context_render.py:294-321  (render_project_pipeline)
  [2b391c6e665dff31]   STRU  _render_autonomy_loop_brief  L=28 N=2 saved=28 sim=1.00
      src/koru/context.py:1196-1223  (_render_autonomy_loop_brief)
      src/koru/context_render.py:399-426  (render_autonomy_loop_brief)
  [d1af68a6108ab40a]   STRU  main  L=27 N=2 saved=27 sim=1.00
      src/koru/cli.py:586-612  (main)
      src/koru/cli_cleaned.py:541-562  (main)
  [20b29cce2972cd44]   STRU  _render_agent_lanes  L=23 N=2 saved=23 sim=1.00
      src/koru/context.py:845-867  (_render_agent_lanes)
      src/koru/context_render.py:48-70  (render_agent_lanes)
  [c3d45eea0cd0408e]   STRU  _render_policy  L=23 N=2 saved=23 sim=1.00
      src/koru/context.py:1121-1143  (_render_policy)
      src/koru/context_render.py:324-346  (render_policy)
  [d8e7e2e5ab1cb516]   STRU  _render_ai_tool_support_2026  L=22 N=2 saved=22 sim=1.00
      src/koru/context.py:920-941  (_render_ai_tool_support_2026)
      src/koru/context_render.py:123-144  (render_ai_tool_support_2026)
  [dc9dabf29359a004]   STRU  _maybe_reexec_for_project_venv  L=21 N=2 saved=21 sim=1.00
      src/koru/cli.py:545-565  (_maybe_reexec_for_project_venv)
      src/koru/cli_cleaned.py:504-522  (_maybe_reexec_for_project_venv)
  [e119f82eba171bb2]   STRU  _render_active_ticket  L=21 N=2 saved=21 sim=1.00
      src/koru/context.py:996-1016  (_render_active_ticket)
      src/koru/context_render.py:199-219  (render_active_ticket)
  [d8b6166dd12467a7]   EXAC  _stdio_info  L=5 N=5 saved=20 sim=1.00
      src/koru/autonomous.py:148-152  (_stdio_info)
      src/koru/autonomous_checkpoint.py:16-19  (_stdio_info)
      src/koru/autonomous_cycle.py:46-49  (_stdio_info)
      src/koru/autonomous_daemon.py:27-31  (_stdio_info)
      src/koru/autonomous_processes.py:178-182  (_stdio_info)
  [f7eea25d8bf479d9]   STRU  _render_dashboard  L=19 N=2 saved=19 sim=1.00
      src/koru/context.py:1175-1193  (_render_dashboard)
      src/koru/context_render.py:378-396  (render_dashboard)
  [e29ad3fb5eb111af]   STRU  _is_topology_enabled  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous.py:324-332  (_is_topology_enabled)
      src/koru/autonomous_cycle.py:66-74  (_is_topology_enabled)
      src/koru/autonomy/phases/utils.py:11-19  (is_topology_enabled)
  [fa6206f15e06c491]   STRU  current_head  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous_checkpoint.py:28-36  (current_head)
      src/koru/autonomous_cycle.py:77-85  (_current_head)
      src/koru/autonomy/phases/utils.py:22-30  (current_head)
  [fba62c0a0f651c53]   STRU  _run_queue_loop  L=18 N=2 saved=18 sim=1.00
      src/koru/autonomous_cycle.py:383-400  (_run_queue_loop)
      src/koru/autonomy/phases/queue_phase.py:51-68  (run_queue_loop)
  [50d8c06cd47fbd48]   STRU  _render_setup_required  L=18 N=2 saved=18 sim=1.00
      src/koru/context.py:976-993  (_render_setup_required)
      src/koru/context_render.py:179-196  (render_setup_required)
  [8650f33deb7b92af]   STRU  _render_self_service  L=18 N=2 saved=18 sim=1.00
      src/koru/context.py:1155-1172  (_render_self_service)
      src/koru/context_render.py:358-375  (render_self_service)
  [1fa7be9b2059ed27]   STRU  _load_tool_scaffold  L=17 N=2 saved=17 sim=1.00
      src/koru/cli_cleaned.py:177-193  (_load_tool_scaffold)
      src/koru/cli_task.py:77-100  (_load_tool_scaffold)
  [2523ecfe7a640e25]   STRU  ide_router_main  L=17 N=2 saved=17 sim=1.00
      src/koru/cli_cleaned.py:360-376  (ide_router_main)
      src/koru/cli_ide_router.py:17-51  (ide_router_main)
  [5cfd4fa5645c4ed5]   STRU  _render_no_active_ticket  L=17 N=2 saved=17 sim=1.00
      src/koru/context.py:1030-1046  (_render_no_active_ticket)
      src/koru/context_render.py:233-249  (render_no_active_ticket)
  [c22944c991f2cee7]   STRU  bundled_plugin_vsix_candidates  L=16 N=2 saved=16 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:62-77  (bundled_plugin_vsix_candidates)
      src/koruide/plugin_installer.py:131-146  (_bundled_vsix_candidates)
  [54051ebae1746d54]   STRU  _agent_main  L=16 N=2 saved=16 sim=1.00
      src/koru/cli_agent.py:74-89  (_agent_main)
      src/koru/cli_cleaned.py:246-256  (_agent_main)
  [1d7c20b439cfc40f]   STRU  _koru_package_version  L=5 N=4 saved=15 sim=1.00
      src/koru/agents.py:82-86  (_koru_package_version)
      src/koru/autonomous_startup.py:32-36  (koru_distribution_version)
      src/koru/cli.py:85-89  (_cli_version)
      src/koru/cli_cleaned.py:61-65  (_cli_version)
  [4c788efcc3404bcc]   STRU  _project_cli_reexec_argv  L=15 N=2 saved=15 sim=1.00
      src/koru/cli.py:414-428  (_project_cli_reexec_argv)
      src/koru/cli_cleaned.py:401-413  (_project_cli_reexec_argv)
  [b3be257cd2d0c4bb]   STRU  _build_task_parser  L=15 N=2 saved=15 sim=1.00
      src/koru/cli_cleaned.py:128-142  (_build_task_parser)
      src/koru/cli_task.py:17-74  (_build_task_parser)
  [083964f2a1bf8488]   STRU  _merge_cli_scaffold  L=15 N=2 saved=15 sim=1.00
      src/koru/cli_cleaned.py:195-209  (_merge_cli_scaffold)
      src/koru/cli_task.py:103-128  (_merge_cli_scaffold)
  [ceb2beb8351daf28]   STRU  _task_main  L=15 N=2 saved=15 sim=1.00
      src/koru/cli_cleaned.py:222-236  (_task_main)
      src/koru/cli_task.py:155-187  (_task_main)
  [d86ec1c988a8a137]   STRU  _action_install_plugin  L=7 N=3 saved=14 sim=1.00
      src/koru/autopilot/cli_command.py:776-782  (_action_install_plugin)
      src/koru/autopilot/cli_command.py:785-791  (_action_install_plugin_jetbrains)
      src/koru/autopilot/cli_command.py:852-858  (_action_install_unit)
  [7a47c943e98a3943]   STRU  _peek_project_from_argv  L=7 N=3 saved=14 sim=1.00
      src/koru/cli.py:397-403  (_peek_project_from_argv)
      src/koru/cli_auto.py:23-29  (_peek_project_from_argv)
      src/koru/cli_cleaned.py:386-392  (_peek_project_from_argv)
  [c9dd6c5a9bf91266]   STRU  _maybe_print_project_venv_hint  L=14 N=2 saved=14 sim=1.00
      src/koru/cli.py:431-444  (_maybe_print_project_venv_hint)
      src/koru/cli_cleaned.py:415-425  (_maybe_print_project_venv_hint)
  [5dfaaa92d6a7d057]   STRU  _tools_main  L=14 N=2 saved=14 sim=1.00
      src/koru/cli_cleaned.py:113-126  (_tools_main)
      src/koru/cli_tools.py:41-71  (_tools_main)
  [c128cb85e01d8566]   STRU  _runtime_context_main  L=14 N=2 saved=14 sim=1.00
      src/koru/cli_cleaned.py:287-300  (_runtime_context_main)
      src/koru/cli_runtime_context.py:60-77  (_runtime_context_main)
  [2252dd4ae417456e]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:140-152  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:131-143  (_parse_iso_datetime)
  [5ddec50ead9632f9]   STRU  _should_suggest_wizard  L=13 N=2 saved=13 sim=1.00
      src/koru/cli.py:447-459  (_should_suggest_wizard)
      src/koru/cli_cleaned.py:427-439  (_should_suggest_wizard)
  [6a88d9e54db032d3]   STRU  _render_runtime_context_text  L=13 N=2 saved=13 sim=1.00
      src/koru/cli_cleaned.py:273-285  (_render_runtime_context_text)
      src/koru/cli_runtime_context.py:36-57  (_render_runtime_context_text)
  [ad3918f482428329]   EXAC  _path_is_relative_to  L=6 N=3 saved=12 sim=1.00
      src/koru/autonomous_runtime.py:79-84  (_path_is_relative_to)
      src/koru/cli.py:406-411  (_path_is_relative_to)
      src/koru/cli_cleaned.py:394-399  (_path_is_relative_to)
  [07394d97ab843be1]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:9-21  (resolve_xdg_path)
  [cfa0e91c669b55c5]   STRU  _build_local_serve_parser  L=6 N=3 saved=12 sim=1.00
      src/koru/cli_cleaned.py:156-161  (_build_local_serve_parser)
      src/koru/cli_local_serve.py:17-45  (_build_local_serve_parser)
      src/koruapi/local.py:11-19  (build_local_parser)
  [e0b04a7fae7e1a89]   STRU  _render_header  L=12 N=2 saved=12 sim=1.00
      src/koru/context.py:803-814  (_render_header)
      src/koru/context_render.py:8-19  (render_header)
  [40a7bc5fef2589e9]   STRU  _handle_mcp_list_tickets  L=6 N=3 saved=12 sim=1.00
      src/koruapi/invoke_handlers.py:161-166  (_handle_mcp_list_tickets)
      src/koruapi/invoke_handlers.py:169-172  (_handle_mcp_run_ticket)
      src/koruapi/invoke_handlers.py:175-180  (_handle_mcp_quality_gates)
  [d4d1a15bc8e8affa]   STRU  message_received  L=12 N=2 saved=12 sim=1.00
      src/koruide/protocol.py:203-214  (message_received)
      src/koruide/protocol.py:217-228  (status_error)
  [42883f38a75056c9]   STRU  _warn_autopilot_focus_retry  L=11 N=2 saved=11 sim=1.00
      src/koru/autonomous_cycle.py:873-883  (_warn_autopilot_focus_retry)
      src/koru/autonomous_cycle.py:905-915  (_warn_autopilot_plugin_retry)
  [b79fb4d314048ea0]   STRU  _build_serve_parser  L=11 N=2 saved=11 sim=1.00
      src/koru/cli_cleaned.py:144-154  (_build_serve_parser)
      src/koru/cli_serve.py:17-64  (_build_serve_parser)
  [c8e2ac269d01941f]   STRU  _print_task_result  L=10 N=2 saved=10 sim=1.00
      src/koru/cli_cleaned.py:211-220  (_print_task_result)
      src/koru/cli_task.py:131-152  (_print_task_result)
  [db3e3e3ad621b70e]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:111-120  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve_utils.py:146-155  (read_serve_endpoint)
  [f3473847ca9dbaa4]   STRU  _refactor_planfile_handoff_main  L=9 N=2 saved=9 sim=1.00
      src/koru/cli_cleaned.py:350-358  (_refactor_planfile_handoff_main)
      src/koru/cli_refactor_planfile_handoff.py:17-33  (_refactor_planfile_handoff_main)
  [d3fe48eeadbdaf2c]   STRU  _cursor_project_config  L=3 N=4 saved=9 sim=1.00
      src/koru/mcp_provision.py:43-45  (_cursor_project_config)
      src/koru/mcp_provision.py:48-50  (_vscode_project_config)
      src/koru/mcp_provision.py:53-55  (_windsurf_project_config)
      src/koru/mcp_provision.py:58-60  (_zed_project_settings)
  [823aa4659db9c93d]   STRU  _handle_wait  L=3 N=4 saved=9 sim=1.00
      src/korudsl/library.py:38-40  (_handle_wait)
      src/korudsl/library.py:43-45  (_handle_get)
      src/korudsl/library.py:48-50  (_handle_save)
      src/korudsl/library.py:53-55  (_handle_if)
  [7b90218491b862bb]   STRU  _versioned_plugin_vsix_candidates  L=8 N=2 saved=8 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:52-59  (_versioned_plugin_vsix_candidates)
      src/koruide/plugin_installer.py:121-128  (_versioned_vsix_candidates)
  [276bf4ee1b1c66e1]   STRU  _build_tools_parser  L=8 N=2 saved=8 sim=1.00
      src/koru/cli_cleaned.py:104-111  (_build_tools_parser)
      src/koru/cli_tools.py:17-38  (_build_tools_parser)
  [940e90e95c5d69b3]   STRU  _check_git_commit_policy  L=4 N=3 saved=8 sim=1.00
      src/koru/policy.py:194-197  (_check_git_commit_policy)
      src/koru/policy.py:200-203  (_check_git_push_policy)
      src/koru/policy.py:226-229  (_check_git_tag_policy)
  [c118ff9c11323590]   EXAC  _plugin_package_version  L=7 N=2 saved=7 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:43-49  (_plugin_package_version)
      src/koruide/plugin_installer.py:112-118  (_plugin_package_version)
  [abf90bbbadf601ec]   STRU  as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:153-159  (as_managed)
      src/koru/autonomous_processes.py:169-175  (_as_managed)
  [8e12ae22db3cad29]   STRU  confirm_replace_existing  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:200-206  (confirm_replace_existing)
      src/koru/autonomous_processes.py:229-235  (_confirm_replace_existing)
  [d84b14f17a72b9af]   STRU  _context_main  L=7 N=2 saved=7 sim=1.00
      src/koru/cli_cleaned.py:464-470  (_context_main)
      src/koru/cli_context.py:18-29  (_context_main)
  [2d9c1ad473989a52]   STRU  _render_rules  L=7 N=2 saved=7 sim=1.00
      src/koru/context.py:1146-1152  (_render_rules)
      src/koru/context_render.py:349-355  (render_rules)
  [2d7b9210c1b65241]   STRU  activity_enabled  L=3 N=3 saved=6 sim=1.00
      src/koru/activity_log.py:15-17  (activity_enabled)
      src/koru/autonomy/operator_pipeline.py:268-270  (_operator_autostart_server_enabled)
      src/koruide/plugin_installer.py:304-306  (_env_reassert_extension_install)
  [9b7967c4c573e5f1]   STRU  process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous_process_guard.py:38-43  (process_cwd)
      src/koru/autonomous_processes.py:45-50  (_process_cwd)
  [c7374d52504d8e71]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:353-358  (set_component_enabled)
      src/koru/topology.py:361-366  (set_pipeline_enabled)
  [e29b4e25afe879d2]   STRU  _read_proc_cmdline  L=6 N=2 saved=6 sim=1.00
      src/koru/wizard/project.py:34-39  (_read_proc_cmdline)
      src/koruide/ide.py:141-147  (_read_cmdline)
  [c66988d54f59cb9c]   STRU  ydotool_enter_keycode  L=6 N=2 saved=6 sim=1.00
      src/koruide/injector_backends.py:14-19  (ydotool_enter_keycode)
      src/koruide/injector_backends.py:32-37  (ydotool_ctrl_keycode)
  [cede1a8630b48984]   STRU  os_injector_env_disabled  L=3 N=3 saved=6 sim=1.00
      src/koruide/os_injector.py:63-65  (os_injector_env_disabled)
      src/koruide/os_injector.py:68-70  (os_injector_env_forced)
      src/koruide/os_injector.py:73-75  (dry_run_from_env)
  [965bd49cbae99ad0]   STRU  _current_koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous_daemon.py:34-38  (_current_koru_version)
      src/koruide/daemon.py:63-67  (_daemon_package_version)
  [73cd2b2ecccd25b9]   STRU  _command_value  L=5 N=2 saved=5 sim=1.00
      src/koru/cli.py:78-82  (_command_value)
      src/koru/cli_cleaned.py:55-59  (_command_value)
  [39b742eeea969c7e]   STRU  _build_runtime_context_parser  L=5 N=2 saved=5 sim=1.00
      src/koru/cli_cleaned.py:267-271  (_build_runtime_context_parser)
      src/koru/cli_runtime_context.py:17-33  (_build_runtime_context_parser)
  [dbf8a129ca3f33fb]   STRU  _koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/local_manager_client.py:23-27  (_koru_version)
      src/koru/local_manager_state.py:20-24  (koru_version)
  [e381e420e278e548]   STRU  planfile_dir  L=5 N=2 saved=5 sim=1.00
      src/koru/runtime.py:42-46  (planfile_dir)
      src/koruapi/dashboard_serve_utils.py:158-162  (_build_handler_for)
  [c4200e7110d9ebe1]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [8c85b68869749734]   STRU  status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_checkpoint.py:124-127  (status_in_skip_list)
      src/koru/autonomous_cycle.py:88-91  (_status_in_skip_list)
  [6ab181429cc7b1d7]   STRU  _build_queue_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_cycle.py:377-380  (_build_queue_command)
      src/koru/autonomy/phases/queue_phase.py:45-48  (build_queue_command)
  [db8d6ff4a9df70dc]   STRU  _init_ci_main  L=4 N=2 saved=4 sim=1.00
      src/koru/cli_cleaned.py:302-305  (_init_ci_main)
      src/koru/cli_init.py:104-120  (init_ci_main)
  [93c2d285f0f82504]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      src/koru/local_manager_state.py:57-59  (__init__)
      src/koru/local_manager_state.py:73-75  (__init__)
  [19ffbb44324d5e1e]   STRU  iter_agent_backend_profiles  L=3 N=2 saved=3 sim=1.00
      src/koru/agent_backends.py:105-107  (iter_agent_backend_profiles)
      src/koruide/ide.py:93-95  (autopilot_ide_choices)
  [3e72ce8df48766bc]   STRU  _apply_auto_pipeline_flags  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:1087-1089  (_apply_auto_pipeline_flags)
      src/koru/autonomous.py:1092-1094  (_apply_replace_existing_flags)
  [5d75a9aed94653a0]   STRU  allow_keyboard_autopilot_fallback  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_gate.py:55-57  (allow_keyboard_autopilot_fallback)
      src/koru/autonomous_cycle_gate.py:92-94  (scan_while_waiting_input_enabled)
  [781cd2265323c713]   STRU  systemd_user_dir  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/systemd_cli.py:15-17  (systemd_user_dir)
      src/koruide/config.py:66-68  (default_config_path)
  [60d745664334ec54]   STRU  redup_scan_command  L=3 N=2 saved=3 sim=1.00
      src/koru/redup_integration.py:22-24  (redup_scan_command)
      src/koru/redup_integration.py:27-29  (redup_check_command)
  [3fc8b0d2a83cdbf8]   STRU  supported_autopilot_ide_ids  L=3 N=2 saved=3 sim=1.00
      src/koruide/ide.py:88-90  (supported_autopilot_ide_ids)
      src/koruide/ide.py:98-100  (vscode_extension_plugin_ide_ids)

REFACTOR[86] (ranked by priority):
  [1] ◐ extract_module     → src/koru/utils/_build_parser.py
      WHY: 2 occurrences of 231-line block across 2 files — saves 231 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [2] ◐ extract_module     → src/koru/utils/agent_backends_main.py
      WHY: 2 occurrences of 57-line block across 2 files — saves 57 lines
      FILES: src/koru/cli_agent_backends.py, src/koru/cli_cleaned.py
  [3] ◐ extract_module     → src/koru/utils/_bootstrap_main.py
      WHY: 2 occurrences of 52-line block across 2 files — saves 52 lines
      FILES: src/koru/cli_bootstrap.py, src/koru/cli_cleaned.py
  [4] ◐ extract_function   → src/koru/utils/_build_agent_parser.py
      WHY: 2 occurrences of 49-line block across 2 files — saves 49 lines
      FILES: src/koru/cli_agent.py, src/koru/cli_cleaned.py
  [5] ◐ extract_function   → src/koru/utils/render_markdown_handoff.py
      WHY: 2 occurrences of 44-line block across 2 files — saves 44 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [6] ◐ extract_function   → src/koru/utils/_render_gates.py
      WHY: 2 occurrences of 40-line block across 2 files — saves 40 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [7] ◐ extract_function   → src/koru/utils/_command_loop_main.py
      WHY: 2 occurrences of 38-line block across 2 files — saves 38 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [8] ○ extract_function   → src/koru/utils/_dsl_main.py
      WHY: 10 occurrences of 4-line block across 4 files — saves 36 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py, src/koru/cli_local_serve.py, src/koru/cli_serve.py
  [9] ○ extract_function   → src/koru/utils/_render_semcod_tools.py
      WHY: 2 occurrences of 30-line block across 2 files — saves 30 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [10] ○ extract_function   → src/koru/utils/provision_cursor.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: src/koru/mcp_provision.py
  [11] ○ extract_function   → src/koru/utils/_render_project_pipeline.py
      WHY: 2 occurrences of 28-line block across 2 files — saves 28 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [12] ○ extract_function   → src/koru/utils/_render_autonomy_loop_brief.py
      WHY: 2 occurrences of 28-line block across 2 files — saves 28 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [13] ○ extract_function   → src/koru/utils/main.py
      WHY: 2 occurrences of 27-line block across 2 files — saves 27 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [14] ○ extract_function   → src/koru/utils/_render_agent_lanes.py
      WHY: 2 occurrences of 23-line block across 2 files — saves 23 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [15] ○ extract_function   → src/koru/utils/_render_policy.py
      WHY: 2 occurrences of 23-line block across 2 files — saves 23 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [16] ○ extract_function   → src/koru/utils/_render_ai_tool_support_2026.py
      WHY: 2 occurrences of 22-line block across 2 files — saves 22 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [17] ○ extract_function   → src/koru/utils/_maybe_reexec_for_project_venv.py
      WHY: 2 occurrences of 21-line block across 2 files — saves 21 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [18] ○ extract_function   → src/koru/utils/_render_active_ticket.py
      WHY: 2 occurrences of 21-line block across 2 files — saves 21 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [19] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 5 occurrences of 5-line block across 5 files — saves 20 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomous_daemon.py, src/koru/autonomous_processes.py
  [20] ○ extract_function   → src/koru/utils/_render_dashboard.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [21] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py, src/koru/autonomy/phases/utils.py
  [22] ○ extract_function   → src/koru/utils/current_head.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomy/phases/utils.py
  [23] ○ extract_function   → src/koru/utils/_run_queue_loop.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [24] ○ extract_function   → src/koru/utils/_render_setup_required.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [25] ○ extract_function   → src/koru/utils/_render_self_service.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [26] ○ extract_function   → src/koru/utils/_load_tool_scaffold.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [27] ○ extract_function   → src/koru/utils/ide_router_main.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_ide_router.py
  [28] ○ extract_function   → src/koru/utils/_render_no_active_ticket.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [29] ○ extract_function   → src/utils/bundled_plugin_vsix_candidates.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [30] ○ extract_function   → src/koru/utils/_agent_main.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: src/koru/cli_agent.py, src/koru/cli_cleaned.py
  [31] ○ extract_function   → src/koru/utils/_koru_package_version.py
      WHY: 4 occurrences of 5-line block across 4 files — saves 15 lines
      FILES: src/koru/agents.py, src/koru/autonomous_startup.py, src/koru/cli.py, src/koru/cli_cleaned.py
  [32] ○ extract_function   → src/koru/utils/_project_cli_reexec_argv.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [33] ○ extract_function   → src/koru/utils/_build_task_parser.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [34] ○ extract_function   → src/koru/utils/_merge_cli_scaffold.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [35] ○ extract_function   → src/koru/utils/_task_main.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [36] ○ extract_function   → src/koru/autopilot/utils/_action_install_plugin.py
      WHY: 3 occurrences of 7-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/cli_command.py
  [37] ○ extract_function   → src/koru/utils/_peek_project_from_argv.py
      WHY: 3 occurrences of 7-line block across 3 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_auto.py, src/koru/cli_cleaned.py
  [38] ○ extract_function   → src/koru/utils/_maybe_print_project_venv_hint.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [39] ○ extract_function   → src/koru/utils/_tools_main.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_tools.py
  [40] ○ extract_function   → src/koru/utils/_runtime_context_main.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [41] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [42] ○ extract_function   → src/koru/utils/_should_suggest_wizard.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [43] ○ extract_function   → src/koru/utils/_render_runtime_context_text.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [44] ○ extract_function   → src/koru/utils/_path_is_relative_to.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koru/autonomous_runtime.py, src/koru/cli.py, src/koru/cli_cleaned.py
  [45] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [46] ○ extract_function   → src/utils/_build_local_serve_parser.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_local_serve.py, src/koruapi/local.py
  [47] ○ extract_function   → src/koru/utils/_render_header.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [48] ○ extract_function   → src/koruapi/utils/_handle_mcp_list_tickets.py
      WHY: 3 occurrences of 6-line block across 1 files — saves 12 lines
      FILES: src/koruapi/invoke_handlers.py
  [49] ○ extract_function   → src/koruide/utils/message_received.py
      WHY: 2 occurrences of 12-line block across 1 files — saves 12 lines
      FILES: src/koruide/protocol.py
  [50] ○ extract_function   → src/koru/utils/_warn_autopilot_focus_retry.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: src/koru/autonomous_cycle.py
  [51] ○ extract_function   → src/koru/utils/_build_serve_parser.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_serve.py
  [52] ○ extract_function   → src/koru/utils/_print_task_result.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [53] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve_utils.py
  [54] ○ extract_function   → src/koru/utils/_refactor_planfile_handoff_main.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_refactor_planfile_handoff.py
  [55] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/koru/mcp_provision.py
  [56] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [57] ○ extract_function   → src/utils/_versioned_plugin_vsix_candidates.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [58] ○ extract_function   → src/koru/utils/_build_tools_parser.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_tools.py
  [59] ○ extract_function   → src/koru/utils/_check_git_commit_policy.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: src/koru/policy.py
  [60] ○ extract_function   → src/utils/_plugin_package_version.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [61] ○ extract_function   → src/koru/utils/as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [62] ○ extract_function   → src/koru/utils/confirm_replace_existing.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [63] ○ extract_function   → src/koru/utils/_context_main.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_context.py
  [64] ○ extract_function   → src/koru/utils/_render_rules.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/context.py, src/koru/context_render.py
  [65] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/activity_log.py, src/koru/autonomy/operator_pipeline.py, src/koruide/plugin_installer.py
  [66] ○ extract_function   → src/koru/utils/process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [67] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [68] ○ extract_function   → src/utils/_read_proc_cmdline.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/wizard/project.py, src/koruide/ide.py
  [69] ○ extract_function   → src/koruide/utils/ydotool_enter_keycode.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koruide/injector_backends.py
  [70] ○ extract_function   → src/koruide/utils/os_injector_env_disabled.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koruide/os_injector.py
  [71] ○ extract_function   → src/utils/_current_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous_daemon.py, src/koruide/daemon.py
  [72] ○ extract_function   → src/koru/utils/_command_value.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [73] ○ extract_function   → src/koru/utils/_build_runtime_context_parser.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [74] ○ extract_function   → src/koru/utils/_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/local_manager_client.py, src/koru/local_manager_state.py
  [75] ○ extract_function   → src/utils/planfile_dir.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/runtime.py, src/koruapi/dashboard_serve_utils.py
  [76] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [77] ○ extract_function   → src/koru/utils/status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py
  [78] ○ extract_function   → src/koru/utils/_build_queue_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [79] ○ extract_function   → src/koru/utils/_init_ci_main.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_init.py
  [80] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/local_manager_state.py
  [81] ○ extract_function   → src/utils/iter_agent_backend_profiles.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/agent_backends.py, src/koruide/ide.py
  [82] ○ extract_function   → src/koru/utils/_apply_auto_pipeline_flags.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous.py
  [83] ○ extract_function   → src/koru/utils/allow_keyboard_autopilot_fallback.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_gate.py
  [84] ○ extract_function   → src/utils/systemd_user_dir.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autopilot/systemd_cli.py, src/koruide/config.py
  [85] ○ extract_function   → src/koru/utils/redup_scan_command.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/redup_integration.py
  [86] ○ extract_function   → src/koruide/utils/supported_autopilot_ide_ids.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruide/ide.py

QUICK_WINS[63] (low risk, high savings — do first):
  [8] extract_function   saved=36L  → src/koru/utils/_dsl_main.py
      FILES: cli.py, cli_cleaned.py, cli_local_serve.py +1
  [9] extract_function   saved=30L  → src/koru/utils/_render_semcod_tools.py
      FILES: context.py, context_render.py
  [10] extract_function   saved=30L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [11] extract_function   saved=28L  → src/koru/utils/_render_project_pipeline.py
      FILES: context.py, context_render.py
  [12] extract_function   saved=28L  → src/koru/utils/_render_autonomy_loop_brief.py
      FILES: context.py, context_render.py
  [13] extract_function   saved=27L  → src/koru/utils/main.py
      FILES: cli.py, cli_cleaned.py
  [14] extract_function   saved=23L  → src/koru/utils/_render_agent_lanes.py
      FILES: context.py, context_render.py
  [15] extract_function   saved=23L  → src/koru/utils/_render_policy.py
      FILES: context.py, context_render.py
  [16] extract_function   saved=22L  → src/koru/utils/_render_ai_tool_support_2026.py
      FILES: context.py, context_render.py
  [17] extract_function   saved=21L  → src/koru/utils/_maybe_reexec_for_project_venv.py
      FILES: cli.py, cli_cleaned.py

EFFORT_ESTIMATE (total ≈ 58.4h):
  hard   _build_parser                       saved=231L  ~693min
  hard   agent_backends_main                 saved=57L  ~171min
  hard   _bootstrap_main                     saved=52L  ~156min
  hard   _build_agent_parser                 saved=49L  ~147min
  hard   render_markdown_handoff             saved=44L  ~132min
  hard   _render_gates                       saved=40L  ~120min
  hard   _command_loop_main                  saved=38L  ~114min
  medium _dsl_main                           saved=36L  ~72min
  medium _render_semcod_tools                saved=30L  ~60min
  medium provision_cursor                    saved=30L  ~60min
  ... +76 more (~1776min)

METRICS-TARGET:
  dup_groups:  86 → 0
  saved_lines: 1495 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 2124 func | 215f | 2026-05-22
# generated in 0.01s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           src/koru/doctor.py
      WHY: 1906L, 3 classes, max CC=49
      EFFORT: ~4h  IMPACT: 93394

  [2] !! SPLIT           src/koru/autonomous_cycle.py
      WHY: 1367L, 1 classes, max CC=14
      EFFORT: ~4h  IMPACT: 19138

  [3] !! SPLIT-FUNC      load_tree  CC=25  fan=24
      WHY: CC=25 exceeds 15
      EFFORT: ~1h  IMPACT: 600

  [4] !! SPLIT-FUNC      _check_autopilot_chat_control  CC=49  fan=12
      WHY: CC=49 exceeds 15
      EFFORT: ~1h  IMPACT: 588

  [5] !! SPLIT-FUNC      wizard_main  CC=29  fan=20
      WHY: CC=29 exceeds 15
      EFFORT: ~1h  IMPACT: 580

  [6] !! SPLIT-FUNC      _check_ide_console_log  CC=31  fan=17
      WHY: CC=31 exceeds 15
      EFFORT: ~1h  IMPACT: 527

  [7] !  SPLIT-FUNC      dashboard_main  CC=23  fan=19
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 437

  [8] !  SPLIT-FUNC      configure_project  CC=20  fan=21
      WHY: CC=20 exceeds 15
      EFFORT: ~1h  IMPACT: 420

  [9] !  SPLIT-FUNC      AutopilotBridge.submitChat  CC=16  fan=18
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 288

  [10] !  SPLIT-FUNC      _check_autopilot_plugin_bundle  CC=23  fan=12
      WHY: CC=23 exceeds 15
      EFFORT: ~1h  IMPACT: 276


RISKS[3]:
  ⚠ Splitting src/koru/doctor.py may break 68 import paths
  ⚠ Splitting src/koru/autonomous_cycle.py may break 44 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          4.1 → ≤2.9
  max-CC:      49 → ≤20
  god-modules: 21 → 0
  high-CC(≥15): 11 → ≤5
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
  prev CC̄=4.1 → now CC̄=4.1
```

## Intent

Closed-loop automation across semcod/* repositories.
