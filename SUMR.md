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
- **version**: `0.1.168`
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
  version: 0.1.168;
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

*433 nodes · 500 edges · 73 modules · CC̄=4.0*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 312 | 0 | **312** |
| `_build_handler` *(in src.koruapi.dashboard_serve)* | 1 | 1 | 105 | **106** |
| `render_markdown_handoff` *(in src.koru.context)* | 10 ⚠ | 5 | 47 | **52** |
| `_drive_via_keyboard` *(in src.koruide.daemon.AutopilotDaemon)* | 12 ⚠ | 0 | 47 | **47** |
| `activity` *(in src.koru.activity_log)* | 4 | 34 | 7 | **41** |
| `_build_parser` *(in src.koru.cli)* | 1 | 3 | 36 | **39** |
| `create_nl_task` *(in src.koru.tasks)* | 12 ⚠ | 7 | 28 | **35** |
| `tool_run_ticket` *(in src.koruapi.mcp_server)* | 14 ⚠ | 1 | 33 | **34** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.20s
# nodes: 433 | edges: 500 | modules: 73
# CC̄=4.0

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:312  out:0  total:312
  src.koruapi.dashboard_serve._build_handler
    CC=1  in:1  out:105  total:106
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:47  total:52
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=12  in:0  out:47  total:47
  src.koru.activity_log.activity
    CC=4  in:34  out:7  total:41
  src.koru.cli._build_parser
    CC=1  in:3  out:36  total:39
  src.koru.tasks.create_nl_task
    CC=12  in:7  out:28  total:35
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.autonomous._stdio_info
    CC=1  in:32  out:1  total:33
  src.koru.cli._topology_main
    CC=12  in:0  out:32  total:32
  src.koru.events.emit_management_event
    CC=8  in:25  out:7  total:32
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  src.koruide.ide.detect_running_ides
    CC=13  in:20  out:10  total:30
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.cli._task_main
    CC=11  in:0  out:27  total:27
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koru.init.init_project
    CC=7  in:2  out:23  total:25
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25
  src.koru.cli._render_runtime_context_text
    CC=14  in:1  out:23  total:24

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
  src.koru.autonomous  [17 funcs]
    _ancestor_pids  CC=7  out:8
    _apply_agent_lane_environ  CC=3  out:3
    _as_managed  CC=1  out:1
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _daemon_activity_log  CC=2  out:3
    _find_existing_autonomous_processes  CC=11  out:16
    _find_existing_wup_processes  CC=11  out:15
    _guard_existing_autonomous_processes  CC=11  out:14
    _looks_like_autonomous_up_command  CC=1  out:1
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
  src.koru.cli  [41 funcs]
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
    resolve_ide_route  CC=8  out:9
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
  src.koru.queue.koru_queue_argv  [1 funcs]
    build_koru_queue_argv  CC=5  out:7
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=14  out:9
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
  src.koru.queue_cli_helpers  [4 funcs]
    emit_queue_run_started  CC=2  out:2
    open_queue_run_log  CC=4  out:2
    run_queue_loop_mode  CC=6  out:19
    run_queue_single_mode  CC=9  out:16
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
  src.koru.topology  [3 funcs]
    enabled_components_for_pipeline  CC=9  out:11
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
  src.koruide.daemon  [15 funcs]
    __init__  CC=7  out:9
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=12  out:47
    _handle_ack  CC=10  out:15
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=5  out:11
    _relay_message_sent_ack  CC=2  out:8
    _relay_os_fallback_ack  CC=3  out:8
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
    _candidate_backends  CC=6  out:13
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
  src.koruide.plugin_installer  [19 funcs]
    _configure_socket_path  CC=8  out:12
    _env_reassert_extension_install  CC=1  out:3
    _extension_is_installed  CC=4  out:5
    _ide_from_terminal_env  CC=1  out:1
    _install_extension_vsix  CC=10  out:14
    _parse_extension_version  CC=4  out:6
    _reassert_extension_extra  CC=9  out:5
    _repo_root  CC=4  out:4
    _resolve_ide_command  CC=7  out:4
    _result_already_installed  CC=2  out:3
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

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.20s
# nodes: 433 | edges: 500 | modules: 73
# CC̄=4.0

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:312  out:0  total:312
  src.koruapi.dashboard_serve._build_handler
    CC=1  in:1  out:105  total:106
  src.koru.context.render_markdown_handoff
    CC=10  in:5  out:47  total:52
  src.koruide.daemon.AutopilotDaemon._drive_via_keyboard
    CC=12  in:0  out:47  total:47
  src.koru.activity_log.activity
    CC=4  in:34  out:7  total:41
  src.koru.cli._build_parser
    CC=1  in:3  out:36  total:39
  src.koru.tasks.create_nl_task
    CC=12  in:7  out:28  total:35
  src.koruapi.mcp_server.tool_run_ticket
    CC=14  in:1  out:33  total:34
  src.koru.autonomous._stdio_info
    CC=1  in:32  out:1  total:33
  src.koru.cli._topology_main
    CC=12  in:0  out:32  total:32
  src.koru.events.emit_management_event
    CC=8  in:25  out:7  total:32
  src.koru.autonomy.env.env_truthy
    CC=3  in:29  out:3  total:32
  src.koruide.ide.detect_running_ides
    CC=13  in:20  out:10  total:30
  src.koru.cli._render_clean_report_text
    CC=12  in:1  out:28  total:29
  src.koru.cli._task_main
    CC=11  in:0  out:27  total:27
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koru.init.init_project
    CC=7  in:2  out:23  total:25
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25
  src.koru.cli._render_runtime_context_text
    CC=14  in:1  out:23  total:24

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
  src.koru.autonomous  [17 funcs]
    _ancestor_pids  CC=7  out:8
    _apply_agent_lane_environ  CC=3  out:3
    _as_managed  CC=1  out:1
    _command_project  CC=5  out:11
    _confirm_replace_existing  CC=3  out:5
    _daemon_activity_log  CC=2  out:3
    _find_existing_autonomous_processes  CC=11  out:16
    _find_existing_wup_processes  CC=11  out:15
    _guard_existing_autonomous_processes  CC=11  out:14
    _looks_like_autonomous_up_command  CC=1  out:1
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
  src.koru.cli  [41 funcs]
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
    resolve_ide_route  CC=8  out:9
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
  src.koru.queue.koru_queue_argv  [1 funcs]
    build_koru_queue_argv  CC=5  out:7
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=14  out:9
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
  src.koru.queue_cli_helpers  [4 funcs]
    emit_queue_run_started  CC=2  out:2
    open_queue_run_log  CC=4  out:2
    run_queue_loop_mode  CC=6  out:19
    run_queue_single_mode  CC=9  out:16
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
  src.koru.topology  [3 funcs]
    enabled_components_for_pipeline  CC=9  out:11
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
  src.koruide.daemon  [15 funcs]
    __init__  CC=7  out:9
    _accept  CC=6  out:12
    _dispatch  CC=3  out:9
    _drive_via_keyboard  CC=12  out:47
    _handle_ack  CC=10  out:15
    _handle_ping  CC=2  out:3
    _handle_shutdown  CC=2  out:6
    _handle_status  CC=5  out:11
    _relay_message_sent_ack  CC=2  out:8
    _relay_os_fallback_ack  CC=3  out:8
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
    _candidate_backends  CC=6  out:13
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
  src.koruide.plugin_installer  [19 funcs]
    _configure_socket_path  CC=8  out:12
    _env_reassert_extension_install  CC=1  out:3
    _extension_is_installed  CC=4  out:5
    _ide_from_terminal_env  CC=1  out:1
    _install_extension_vsix  CC=10  out:14
    _parse_extension_version  CC=4  out:6
    _reassert_extension_extra  CC=9  out:5
    _repo_root  CC=4  out:4
    _resolve_ide_command  CC=7  out:4
    _result_already_installed  CC=2  out:3
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

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 222f 40320L | python:135,shell:42,yaml:15,yml:8,typescript:6,kotlin:6,json:3,txt:1,properties:1,xml:1,toml:1 | 2026-05-21
# generated in 0.07s
# CC̄=4.0 | critical:5/1380 | dups:0 | cycles:0

HEALTH[6]:
  🔴 GOD   src/koru/local_service.py = 577L, 5 classes, 28m, max CC=14
  🟡 CC    _handle_plugin_event CC=15 (limit:15)
  🟡 CC    _compose_service_ready CC=15 (limit:15)
  🟡 CC    pasteText CC=18 (limit:15)
  🟡 CC    _action_daemon CC=15 (limit:15)
  🟡 CC    _action_install_plugin_jetbrains CC=16 (limit:15)

REFACTOR[2]:
  1. split src/koru/local_service.py  (god module)
  2. split 5 high-CC methods  (CC>15)

PIPELINES[375]:
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
  src/                            CC̄=4.2    ←in:0  →out:0
  │ !! autonomous                1745L  2C   48m  CC=12     ←1
  │ !! cli_command               1678L  0C   53m  CC=16     ←0
  │ !! dashboard_serve           1400L  1C   15m  CC=13     ←1
  │ !! autonomous_cycle          1250L  2C   38m  CC=14     ←0
  │ !! context                   1241L  0C   48m  CC=12     ←7
  │ !! mcp_server                1040L  0C   34m  CC=14     ←2
  │ !! scan                       932L  2C   24m  CC=13     ←3
  │ !! daemon                     801L  2C   32m  CC=15     ←0
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←0
  │ !! operator_pipeline          624L  2C   21m  CC=14     ←1
  │ !! init                       610L  1C   15m  CC=12     ←2
  │ !! local_service              577L  5C   28m  CC=14     ←2
  │ !! ide                        547L  1C   29m  CC=13     ←9
  │ !! autonomous_wup             538L  3C   25m  CC=15     ←1
  │ !! doctor                     513L  2C   21m  CC=11     ←2
  │ !! install_manager            504L  2C   25m  CC=13     ←1
  │ plugin_installer           469L  1C   22m  CC=10     ←2
  │ bootstrap                  452L  2C   19m  CC=10     ←2
  │ topology                   414L  1C   15m  CC=12     ←8
  │ injector                   406L  4C   20m  CC=14     ←0
  │ mcp_provision              398L  0C   21m  CC=10     ←3
  │ autonomous_parser          398L  0C    3m  CC=14     ←2
  │ runner                     393L  0C   10m  CC=14     ←2
  │ os_injector                391L  2C   24m  CC=14     ←2
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ post_run_verify            381L  2C   16m  CC=14     ←1
  │ gc                         371L  2C   12m  CC=11     ←1
  │ queue_cli_helpers          369L  0C   15m  CC=9      ←1
  │ agents                     321L  1C   15m  CC=14     ←4
  │ tools                      318L  0C   19m  CC=11     ←1
  │ init_host_environment      314L  0C   17m  CC=9      ←1
  │ env                        304L  0C   11m  CC=12     ←3
  │ ide_work                   301L  0C   11m  CC=12     ←2
  │ autonomous_startup         291L  1C    9m  CC=13     ←2
  │ policy                     262L  1C   10m  CC=9      ←2
  │ autonomous_diagnostics     258L  0C    8m  CC=11     ←1
  │ local_manager_client       252L  2C   15m  CC=7      ←2
  │ runners                    249L  0C   11m  CC=9      ←1
  │ environment                245L  3C    6m  CC=14     ←1
  │ protocol                   231L  2C   14m  CC=12     ←3
  │ tasks                      227L  1C   10m  CC=12     ←7
  │ host_setup                 226L  0C   12m  CC=14     ←3
  │ agent_backends             214L  3C    7m  CC=11     ←2
  │ library                    207L  0C   19m  CC=9      ←1
  │ autonomous_process_guard   206L  2C    8m  CC=11     ←1
  │ gate                       202L  1C    5m  CC=12     ←1
  │ invoke_handlers            199L  1C   15m  CC=5      ←0
  │ integrations               198L  1C    2m  CC=4      ←4
  │ drive_orchestrator         191L  1C   12m  CC=8      ←0
  │ redup_integration          189L  0C   11m  CC=3      ←2
  │ agent_backend_runtime      180L  5C    6m  CC=9      ←0
  │ runtime_insights           179L  0C    6m  CC=9      ←1
  │ server                     175L  1C    8m  CC=9      ←1
  │ openapi                    155L  0C    1m  CC=2      ←1
  │ audit                      154L  2C    6m  CC=6      ←1
  │ ide_client                 152L  2C   12m  CC=3      ←2
  │ project_pipeline           150L  0C    5m  CC=9      ←5
  │ semcod_tools               148L  1C    4m  CC=7      ←3
  │ ticket                     137L  0C    6m  CC=10     ←5
  │ dev_sync                   133L  1C    6m  CC=9      ←0
  │ loop                       131L  3C    4m  CC=12     ←1
  │ cli                        128L  0C    3m  CC=11     ←0
  │ client                     128L  1C    8m  CC=7      ←0
  │ run_log                    123L  1C    7m  CC=4      ←2
  │ config                     123L  1C    1m  CC=4      ←0
  │ config                     119L  1C    6m  CC=7      ←1
  │ heal                       116L  1C    3m  CC=5      ←1
  │ loop                       115L  0C    1m  CC=14     ←3
  │ runtime                    104L  0C    5m  CC=2      ←6
  │ dotenv_loader              104L  0C    3m  CC=7      ←0
  │ prompts                    101L  1C    1m  CC=10     ←1
  │ ide_router                  97L  1C    2m  CC=8      ←4
  │ watch                       93L  0C    6m  CC=9      ←1
  │ dashboard                   90L  0C    3m  CC=5      ←2
  │ events                      90L  0C    2m  CC=8      ←5
  │ autoloop_cli                90L  0C    4m  CC=8      ←0
  │ types                       88L  5C    1m  CC=2      ←0
  │ agent_cli_helpers           87L  0C    3m  CC=10     ←1
  │ locking                     86L  0C    4m  CC=4      ←1
  │ cli                         81L  0C    3m  CC=11     ←0
  │ gc_cli_helpers              81L  0C    5m  CC=12     ←1
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ topology_cli                75L  1C    4m  CC=8      ←1
  │ plugin_router               74L  3C    5m  CC=6      ←0
  │ shell_evidence              72L  0C    2m  CC=7      ←1
  │ transform                   70L  0C    4m  CC=12     ←2
  │ __init__                    69L  0C    0m  CC=0.0    ←0
  │ topology_post               68L  0C    1m  CC=14     ←1
  │ activity_log                67L  0C    5m  CC=5      ←13
  │ __init__                    67L  0C    0m  CC=0.0    ←0
  │ wup_testql_compat           64L  0C    4m  CC=5      ←0
  │ client_helpers              57L  0C    2m  CC=4      ←1
  │ __init__                    55L  0C    2m  CC=4      ←0
  │ planfile_ticket_note        55L  0C    2m  CC=5      ←1
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ protocol                    48L  0C    0m  CC=0.0    ←0
  │ refactor_planfile_handoff    46L  0C    1m  CC=6      ←1
  │ socket                      44L  0C    2m  CC=7      ←7
  │ ide_runtime                 44L  0C    2m  CC=5      ←1
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ subprocess_runner           40L  0C    3m  CC=3      ←5
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ local                       36L  0C    2m  CC=6      ←2
  │ planfile_queue              36L  0C    0m  CC=0.0    ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ human                       31L  0C    1m  CC=5      ←0
  │ autonomous_env              25L  0C    1m  CC=1      ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ utils                       21L  0C    1m  CC=2      ←2
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←2
  │ client                      10L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ injector                     9L  0C    0m  CC=0.0    ←0
  │ os_injector                  9L  0C    0m  CC=0.0    ←0
  │ audit                        9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ __main__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ cli                          0L  0C   53m  CC=14     ←0
  │ commands                     0L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=3.0    ←in:0  →out:0
  │ !! extension.ts               628L  2C   69m  CC=18     ←6
  │ probe-ladder.ts            251L  3C   24m  CC=9      ←0
  │ KoruAutopilotService.kt    136L  1C    5m  CC=0.0    ←0
  │ package.json               112L  0C    0m  CC=0.0    ←0
  │ dispatch-plan.test.ts       94L  0C   11m  CC=4      ←0
  │ probe-ladder.test.ts        78L  0C   10m  CC=2      ←0
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
  scripts/                        CC̄=2.3    ←in:297  →out:0
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ planfile-sync-todo         260L  0C   12m  CC=14     ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←33
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
  │ !! planfile.yaml             1306L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               901L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  511L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             173L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ wup.yaml                    56L  0C    0m  CC=0.0    ←0
  │ project.sh                  54L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
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
                                                      src.koru                        scripts                    src.koruapi                    src.koruide  plugins.koru-autopilot-vscode                    src.korudsl       services.healing-webhook
                       src.koru                             ──                            250                              5                             41                              5                                                                hub
                        scripts                           ←250                             ──                            ←20                            ←27                                                                                               hub
                    src.koruapi                             42                             20                             ──                              1                              1                              4                                 hub
                    src.koruide                              3                             27                             ←1                             ──                                                                                               hub
  plugins.koru-autopilot-vscode                             ←5                                                            ←1                                                            ──                                                            ←1  hub
                    src.korudsl                                                                                           ←4                                                                                           ──                               
       services.healing-webhook                                                                                                                                                          1                                                            ──
  CYCLES: none
  HUB: src.koruide/ (fan-in=42)
  HUB: plugins.koru-autopilot-vscode/ (fan-in=7)
  HUB: src.koru/ (fan-in=45)
  HUB: src.koruapi/ (fan-in=5)
  HUB: scripts/ (fan-in=297)
  SMELL: src.koruide/ fan-out=30 → split needed
  SMELL: src.koru/ fan-out=301 → split needed
  SMELL: src.koruapi/ fan-out=68 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 36 groups | 134f 32445L | 2026-05-21

SUMMARY:
  files_scanned: 134
  total_lines:   32445
  dup_groups:    36
  dup_fragments: 83
  saved_lines:   371
  scan_ms:       3084

HOTSPOTS[7] (files with most duplication):
  src/koru/autonomous.py  dup=119L  groups=12  frags=12  (0.4%)
  src/koru/cli.py  dup=106L  groups=4  frags=9  (0.3%)
  src/koru/autonomous_cycle.py  dup=97L  groups=9  frags=9  (0.3%)
  src/koruapi/dashboard.py  dup=45L  groups=1  frags=1  (0.1%)
  src/koru/mcp_provision.py  dup=39L  groups=2  frags=5  (0.1%)
  src/koruide/protocol.py  dup=24L  groups=1  frags=2  (0.1%)
  src/korudsl/library.py  dup=22L  groups=2  frags=6  (0.1%)

DUPLICATES[36] (ranked by impact):
  [b79fb4d314048ea0] ! STRU  _build_serve_parser  L=48 N=2 saved=48 sim=1.00
      src/koru/cli.py:397-444  (_build_serve_parser)
      src/koruapi/dashboard.py:17-61  (build_serve_parser)
  [2ae726bfafded9cc] ! EXAC  _run_idle_diagnostics  L=36 N=2 saved=36 sim=1.00
      src/koru/autonomous.py:1092-1127  (_run_idle_diagnostics)
      src/koru/autonomous_cycle.py:200-235  (_run_idle_diagnostics)
  [cfa0e91c669b55c5]   STRU  _build_local_serve_parser  L=29 N=2 saved=29 sim=1.00
      src/koru/cli.py:447-475  (_build_local_serve_parser)
      src/koruapi/local.py:11-19  (build_local_parser)
  [077cfa61a2943c36]   STRU  _serve_main  L=4 N=6 saved=20 sim=1.00
      src/koru/cli.py:1055-1058  (_serve_main)
      src/koru/cli.py:1061-1064  (_local_serve_main)
      src/koru/cli.py:1300-1303  (_mcp_serve_main)
      src/koru/cli.py:1365-1368  (_init_ide_main)
      src/koru/cli.py:1427-1430  (_dsl_main)
      src/koru/cli.py:1433-1436  (_api_main)
  [13996a2247a97ed8]   EXAC  _read_wup_health  L=16 N=2 saved=16 sim=1.00
      src/koru/autonomous.py:1074-1089  (_read_wup_health)
      src/koru/autonomous_cycle.py:182-197  (_read_wup_health)
  [400f9f906a729d1a]   STRU  provision_cursor  L=15 N=2 saved=15 sim=1.00
      src/koru/mcp_provision.py:194-208  (provision_cursor)
      src/koru/mcp_provision.py:211-225  (provision_vscode)
  [b060ed239d7cc6c9]   EXAC  _run_command_check  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomous.py:1017-1029  (_run_command_check)
      src/koru/autonomous_cycle.py:129-141  (_run_command_check)
  [d69cbedeb6dc8f2f]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:140-152  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:131-143  (_parse_iso_datetime)
  [07394d97ab843be1]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:9-21  (resolve_xdg_path)
  [40a7bc5fef2589e9]   STRU  _handle_mcp_list_tickets  L=6 N=3 saved=12 sim=1.00
      src/koruapi/invoke_handlers.py:161-166  (_handle_mcp_list_tickets)
      src/koruapi/invoke_handlers.py:169-172  (_handle_mcp_run_ticket)
      src/koruapi/invoke_handlers.py:175-180  (_handle_mcp_quality_gates)
  [d4d1a15bc8e8affa]   STRU  message_received  L=12 N=2 saved=12 sim=1.00
      src/koruide/protocol.py:184-195  (message_received)
      src/koruide/protocol.py:198-209  (status_error)
  [db3e3e3ad621b70e]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:111-120  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve.py:240-249  (read_serve_endpoint)
  [c66988d54f59cb9c]   STRU  _ydotool_enter_keycode  L=10 N=2 saved=10 sim=1.00
      src/koruide/injector.py:59-68  (_ydotool_enter_keycode)
      src/koruide/injector.py:81-86  (_ydotool_ctrl_keycode)
  [30376722d90c4f75]   EXAC  _is_topology_enabled  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:904-912  (_is_topology_enabled)
      src/koru/autonomous_cycle.py:74-82  (_is_topology_enabled)
  [0a213b0b7ddbf9fc]   EXAC  _current_head  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:915-923  (_current_head)
      src/koru/autonomous_cycle.py:85-93  (_current_head)
  [823aa4659db9c93d]   STRU  _handle_wait  L=3 N=4 saved=9 sim=1.00
      src/korudsl/library.py:38-40  (_handle_wait)
      src/korudsl/library.py:43-45  (_handle_get)
      src/korudsl/library.py:48-50  (_handle_save)
      src/korudsl/library.py:53-55  (_handle_if)
  [940e90e95c5d69b3]   STRU  _check_git_commit_policy  L=4 N=3 saved=8 sim=1.00
      src/koru/policy.py:194-197  (_check_git_commit_policy)
      src/koru/policy.py:200-203  (_check_git_push_policy)
      src/koru/policy.py:226-229  (_check_git_tag_policy)
  [abf90bbbadf601ec]   STRU  _as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous.py:333-339  (_as_managed)
      src/koru/autonomous_process_guard.py:153-159  (as_managed)
  [8e12ae22db3cad29]   STRU  _confirm_replace_existing  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous.py:386-392  (_confirm_replace_existing)
      src/koru/autonomous_process_guard.py:200-206  (confirm_replace_existing)
  [2d7b9210c1b65241]   STRU  activity_enabled  L=3 N=3 saved=6 sim=1.00
      src/koru/activity_log.py:11-13  (activity_enabled)
      src/koru/autonomy/operator_pipeline.py:171-173  (_operator_autostart_server_enabled)
      src/koruide/plugin_installer.py:239-241  (_env_reassert_extension_install)
  [9b7967c4c573e5f1]   STRU  _process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous.py:185-190  (_process_cwd)
      src/koru/autonomous_process_guard.py:38-43  (process_cwd)
  [d3fe48eeadbdaf2c]   STRU  _cursor_project_config  L=3 N=3 saved=6 sim=1.00
      src/koru/mcp_provision.py:39-41  (_cursor_project_config)
      src/koru/mcp_provision.py:44-46  (_vscode_project_config)
      src/koru/mcp_provision.py:49-51  (_windsurf_project_config)
  [c7374d52504d8e71]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:353-358  (set_component_enabled)
      src/koru/topology.py:361-366  (set_pipeline_enabled)
  [cede1a8630b48984]   STRU  os_injector_env_disabled  L=3 N=3 saved=6 sim=1.00
      src/koruide/os_injector.py:61-63  (os_injector_env_disabled)
      src/koruide/os_injector.py:66-68  (os_injector_env_forced)
      src/koruide/os_injector.py:71-73  (dry_run_from_env)
  [d8b6166dd12467a7]   EXAC  _stdio_info  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous.py:119-123  (_stdio_info)
      src/koru/autonomous_cycle.py:40-43  (_stdio_info)
  [c1924f9f20af4f46]   EXAC  _koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/local_manager_client.py:23-27  (_koru_version)
      src/koru/local_service.py:35-39  (_koru_version)
  [1d7c20b439cfc40f]   STRU  koru_distribution_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous_startup.py:28-32  (koru_distribution_version)
      src/koru/cli.py:72-76  (_cli_version)
  [c4200e7110d9ebe1]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [774459a6d92b5dbd]   EXAC  _queue_loop_waiting_ticket_label  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous.py:898-901  (_queue_loop_waiting_ticket_label)
      src/koru/autonomous_cycle.py:69-71  (_queue_loop_waiting_ticket_label)
  [a7174a018322bcf8]   EXAC  _status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous.py:1011-1014  (_status_in_skip_list)
      src/koru/autonomous_cycle.py:96-99  (_status_in_skip_list)
  [fdccb72b1fbbe81c]   EXAC  _allow_keyboard_autopilot_fallback  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:135-137  (_allow_keyboard_autopilot_fallback)
      src/koru/autonomous_cycle.py:102-104  (_allow_keyboard_autopilot_fallback)
  [93c2d285f0f82504]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      src/koru/local_service.py:64-66  (__init__)
      src/koru/local_service.py:107-109  (__init__)
  [0f8d5f341099fa34]   EXAC  _open_later  L=3 N=2 saved=3 sim=1.00
      src/koruapi/dashboard_serve.py:1338-1340  (_open_later)
      src/koruapi/dashboard_serve.py:1387-1389  (_open_later)
  [be027ff698a2786c]   STRU  _action_status  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/cli_command.py:947-949  (_action_status)
      src/koru/autopilot/cli_command.py:952-959  (_action_shutdown)
  [781cd2265323c713]   STRU  _systemd_user_dir  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/cli_command.py:1559-1561  (_systemd_user_dir)
      src/koruide/config.py:62-64  (default_config_path)
  [60d745664334ec54]   STRU  redup_scan_command  L=3 N=2 saved=3 sim=1.00
      src/koru/redup_integration.py:22-24  (redup_scan_command)
      src/koru/redup_integration.py:27-29  (redup_check_command)

REFACTOR[36] (ranked by priority):
  [1] ◐ extract_function   → src/utils/_build_serve_parser.py
      WHY: 2 occurrences of 48-line block across 2 files — saves 48 lines
      FILES: src/koru/cli.py, src/koruapi/dashboard.py
  [2] ◐ extract_function   → src/koru/utils/_run_idle_diagnostics.py
      WHY: 2 occurrences of 36-line block across 2 files — saves 36 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
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
  [7] ○ extract_function   → src/koru/utils/_run_command_check.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [8] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [9] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [10] ○ extract_function   → src/koruapi/utils/_handle_mcp_list_tickets.py
      WHY: 3 occurrences of 6-line block across 1 files — saves 12 lines
      FILES: src/koruapi/invoke_handlers.py
  [11] ○ extract_function   → src/koruide/utils/message_received.py
      WHY: 2 occurrences of 12-line block across 1 files — saves 12 lines
      FILES: src/koruide/protocol.py
  [12] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve.py
  [13] ○ extract_function   → src/koruide/utils/_ydotool_enter_keycode.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/koruide/injector.py
  [14] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [15] ○ extract_function   → src/koru/utils/_current_head.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [16] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [17] ○ extract_function   → src/koru/utils/_check_git_commit_policy.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: src/koru/policy.py
  [18] ○ extract_function   → src/koru/utils/_as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [19] ○ extract_function   → src/koru/utils/_confirm_replace_existing.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [20] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/activity_log.py, src/koru/autonomy/operator_pipeline.py, src/koruide/plugin_installer.py
  [21] ○ extract_function   → src/koru/utils/_process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_process_guard.py
  [22] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koru/mcp_provision.py
  [23] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [24] ○ extract_function   → src/koruide/utils/os_injector_env_disabled.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koruide/os_injector.py
  [25] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [26] ○ extract_function   → src/koru/utils/_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/local_manager_client.py, src/koru/local_service.py
  [27] ○ extract_function   → src/koru/utils/koru_distribution_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous_startup.py, src/koru/cli.py
  [28] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [29] ○ extract_function   → src/koru/utils/_queue_loop_waiting_ticket_label.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [30] ○ extract_function   → src/koru/utils/_status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [31] ○ extract_function   → src/koru/utils/_allow_keyboard_autopilot_fallback.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle.py
  [32] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/local_service.py
  [33] ○ extract_function   → src/koruapi/utils/_open_later.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruapi/dashboard_serve.py
  [34] ○ extract_function   → src/koru/autopilot/utils/_action_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autopilot/cli_command.py
  [35] ○ extract_function   → src/utils/_systemd_user_dir.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autopilot/cli_command.py, src/koruide/config.py
  [36] ○ extract_function   → src/koru/utils/redup_scan_command.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/redup_integration.py

QUICK_WINS[22] (low risk, high savings — do first):
  [3] extract_function   saved=29L  → src/utils/_build_local_serve_parser.py
      FILES: cli.py, local.py
  [4] extract_function   saved=20L  → src/koru/utils/_serve_main.py
      FILES: cli.py
  [5] extract_function   saved=16L  → src/koru/utils/_read_wup_health.py
      FILES: autonomous.py, autonomous_cycle.py
  [6] extract_function   saved=15L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [7] extract_function   saved=13L  → src/koru/utils/_run_command_check.py
      FILES: autonomous.py, autonomous_cycle.py
  [8] extract_function   saved=13L  → src/koru/autonomy/utils/_parse_iso_datetime.py
      FILES: ide_work.py, post_run_verify.py
  [9] extract_function   saved=12L  → src/utils/resolve_xdg_path.py
      FILES: client_helpers.py, utils.py
  [10] extract_function   saved=12L  → src/koruapi/utils/_handle_mcp_list_tickets.py
      FILES: invoke_handlers.py
  [11] extract_function   saved=12L  → src/koruide/utils/message_received.py
      FILES: protocol.py
  [12] extract_function   saved=10L  → src/utils/load_koru_project_pipeline.py
      FILES: project_pipeline.py, dashboard_serve.py

EFFORT_ESTIMATE (total ≈ 13.8h):
  hard   _build_serve_parser                 saved=48L  ~144min
  hard   _run_idle_diagnostics               saved=36L  ~108min
  medium _build_local_serve_parser           saved=29L  ~58min
  medium _serve_main                         saved=20L  ~40min
  medium _read_wup_health                    saved=16L  ~32min
  medium provision_cursor                    saved=15L  ~30min
  easy   _run_command_check                  saved=13L  ~26min
  easy   _parse_iso_datetime                 saved=13L  ~26min
  easy   resolve_xdg_path                    saved=12L  ~24min
  easy   _handle_mcp_list_tickets            saved=12L  ~24min
  ... +26 more (~314min)

METRICS-TARGET:
  dup_groups:  36 → 0
  saved_lines: 371 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 1309 func | 115f | 2026-05-21
# generated in 0.00s

NEXT[7] (ranked by impact):
  [1] !! SPLIT           src/koru/autopilot/cli_command.py
      WHY: 1678L, 0 classes, max CC=16
      EFFORT: ~4h  IMPACT: 26848

  [2] !! SPLIT           src/koru/autonomous.py
      WHY: 1745L, 2 classes, max CC=12
      EFFORT: ~4h  IMPACT: 20940

  [3] !! SPLIT           src/koruapi/dashboard_serve.py
      WHY: 1400L, 1 classes, max CC=13
      EFFORT: ~4h  IMPACT: 18200

  [4] !  SPLIT-FUNC      AutopilotBridge.pasteText  CC=18  fan=18
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 324

  [5] !  SPLIT-FUNC      _action_daemon  CC=15  fan=19
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 285

  [6] !  SPLIT-FUNC      AutopilotDaemon._handle_plugin_event  CC=15  fan=14
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 210

  [7] !  SPLIT-FUNC      _action_install_plugin_jetbrains  CC=16  fan=11
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 176


RISKS[3]:
  ⚠ Splitting src/koru/autonomous.py may break 48 import paths
  ⚠ Splitting src/koru/autopilot/cli_command.py may break 53 import paths
  ⚠ Splitting src/koruapi/dashboard_serve.py may break 15 import paths

METRICS-TARGET:
  CC̄:          4.2 → ≤2.9
  max-CC:      18 → ≤9
  god-modules: 20 → 0
  high-CC(≥15): 5 → ≤2
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
  prev CC̄=4.2 → now CC̄=4.2
```

## Intent

Closed-loop automation across semcod/* repositories.
