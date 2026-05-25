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
- **version**: `0.1.280`
- **python_requires**: `>=3.12`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, testql(8), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, package.json, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.280;
}

dependencies {
  runtime: "pyyaml>=6.0,<7.0";
  dev: "pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, ruff>=0.11,<0.16, mypy>=1.11,<3.0, pyright>=1.1.390,<2.0, hypothesis>=6.112,<7.0, pre-commit>=3.8,<5.0, types-PyYAML>=6.0,<7.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60";
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

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS);
}

workflow[name="test-fast"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --quick $(PYTEST_ARGS);
}

workflow[name="test-parallel"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 $(PYTEST_ARGS);
}

workflow[name="test-python-parallel"] {
  trigger: manual;
  step-1: depend target=test-parallel;
}

workflow[name="test-api-parallel"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 \;
  step-2: run cmd=tests/test_koruapi.py \;
  step-3: run cmd=tests/test_koruapi_transports.py \;
  step-4: run cmd=tests/test_dashboard_projects_by_ide.py \;
  step-5: run cmd=tests/test_dashboard_topology_post.py \;
  step-6: run cmd=tests/test_mcp_server.py \;
  step-7: run cmd=$(PYTEST_ARGS);
}

workflow[name="sync-plugin-version"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/sync-plugin-version.py --ide vscode;
  step-2: run cmd=python3 scripts/sync-plugin-version.py --ide cursor;
}

workflow[name="sync-plugin-shared"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/sync-plugin-shared.py;
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

workflow[name="test:all"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --serial --all --verbose {{.CLI_ARGS}};
}

workflow[name="test:docker"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}};
}

workflow[name="test:docker:ide-matrix"] {
  trigger: manual;
  step-1: run cmd=KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh;
}

workflow[name="test:fast"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --fast {{.CLI_ARGS}};
}

workflow[name="test:quick"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --quick {{.CLI_ARGS}};
}

workflow[name="test:parallel"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --fast --maxfail=1 {{.CLI_ARGS}};
}

workflow[name="test:changed"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --changed --quick {{.CLI_ARGS}};
}

workflow[name="test:profile"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --fast --profile {{.CLI_ARGS}};
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
    desc: Run default koru tests in parallel when pytest-xdist is installed (slow Docker/integration tests are deselected by pytest addopts)
    cmds:
      - scripts/koru-pytest.sh --verbose {{.CLI_ARGS}}

  test:all:
    desc: Run every koru test, including slow Docker/integration tests, serially
    cmds:
      - scripts/koru-pytest.sh --serial --all --verbose {{.CLI_ARGS}}

  test:docker:
    desc: Run Docker E2E tests only (slow; deselected by default addopts)
    cmds:
      - scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}}

  test:docker:ide-matrix:
    desc: 'Run Docker OS x IDE smoke matrix. Vars: SYSTEMS, IDES (defaults cover Debian/Ubuntu/Fedora/Alpine and VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed)'
    cmds:
      - KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh
    vars:
      SYSTEMS: '{{.SYSTEMS | default ""}}'
      IDES: '{{.IDES | default ""}}'

  test:fast:
    desc: Run default tests quietly in parallel when pytest-xdist is installed
    cmds:
      - scripts/koru-pytest.sh --fast {{.CLI_ARGS}}

  test:quick:
    desc: Fastest feedback loop (parallel, fail fast, failed tests first)
    cmds:
      - scripts/koru-pytest.sh --quick {{.CLI_ARGS}}

  test:parallel:
    desc: Run tests in parallel with configurable workers (KORU_PYTEST_WORKERS=4)
    cmds:
      - scripts/koru-pytest.sh --fast --maxfail=1 {{.CLI_ARGS}}

  test:changed:
    desc: Run changed pytest files under tests/; falls back to default tests when none changed
    cmds:
      - scripts/koru-pytest.sh --changed --quick {{.CLI_ARGS}}

  test:profile:
    desc: Run default tests and show the slowest test durations
    cmds:
      - scripts/koru-pytest.sh --fast --profile {{.CLI_ARGS}}

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
pytest>=8.0,<10.0
pytest-cov>=5.0,<8.0
pytest-rerunfailures>=14.0,<17.0
pytest-timeout>=2.3,<3.0
pytest-xdist>=3.0,<4.0
ruff>=0.11,<0.16
mypy>=1.11,<3.0
pyright>=1.1.390,<2.0
hypothesis>=6.112,<7.0
pre-commit>=3.8,<5.0
types-PyYAML>=6.0,<7.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
```

## Call Graph

*427 nodes · 500 edges · 100 modules · CC̄=3.5*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in scripts.koru-soak-monitor)* | 0 | 593 | 0 | **593** |
| `list` *(in src.koru.wizard.gui.static.wizard)* | 5 | 141 | 9 | **150** |
| `normalize_ide_id` *(in src.koruide.ide)* | 6 | 64 | 11 | **75** |
| `validate_ide_command_scenario` *(in src.koruide.command_scenario)* | 37 ⚠ | 3 | 67 | **70** |
| `activity` *(in koru.activity_log)* | 6 | 47 | 13 | **60** |
| `render_markdown_handoff` *(in src.koru.context_render)* | 10 ⚠ | 6 | 47 | **53** |
| `emit_management_event` *(in src.koru.events)* | 8 | 31 | 7 | **38** |
| `detect_running_ides` *(in src.koruide.ide)* | 13 ⚠ | 24 | 10 | **34** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.56s
# nodes: 427 | edges: 500 | modules: 100
# CC̄=3.5

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:593  out:0  total:593
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:141  out:9  total:150
  src.koruide.ide.normalize_ide_id
    CC=6  in:64  out:11  total:75
  src.koruide.command_scenario.validate_ide_command_scenario
    CC=37  in:3  out:67  total:70
  koru.activity_log.activity
    CC=6  in:47  out:13  total:60
  src.koru.context_render.render_markdown_handoff
    CC=10  in:6  out:47  total:53
  src.koru.events.emit_management_event
    CC=8  in:31  out:7  total:38
  src.koruide.ide.detect_running_ides
    CC=13  in:24  out:10  total:34
  src.koruobserve.lifecycle.observe_up
    CC=4  in:1  out:32  total:33
  src.koruapi.mcp_server.tool_run_ticket
    CC=12  in:1  out:31  total:32
  src.koruide.socket.default_socket_path
    CC=4  in:16  out:15  total:31
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25
  plugins.koru-autopilot-shared.src.ack-payload.type
    CC=3  in:25  out:0  total:25
  src.koruapi.dashboard_config._dashboard_config_request_kwargs
    CC=10  in:1  out:23  total:24
  src.koru.queue.ticket.planfile_command
    CC=5  in:17  out:7  total:24
  src.koruapi.dashboard_tickets.create_ticket_from_dashboard
    CC=8  in:2  out:22  total:24
  examples.remote_orchestration_demo.run_multi_node_orchestration
    CC=9  in:0  out:24  total:24
  src.koruapi.dashboard_routes._post_remote_drive
    CC=9  in:0  out:24  total:24

MODULES:
  examples.remote_orchestration_demo  [1 funcs]
    run_multi_node_orchestration  CC=9  out:24
  koru.activity_log  [1 funcs]
    activity  CC=6  out:13
  koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
  plugins.koru-autopilot-shared.src.ack-payload  [2 funcs]
    bytes  CC=2  out:0
    type  CC=3  out:0
  plugins.koru-autopilot-vscode.src.extension  [1 funcs]
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
  src.koru.autonomous_process_guard  [2 funcs]
    find_existing_autonomous_processes  CC=11  out:16
    find_existing_wup_processes  CC=11  out:15
  src.koru.autonomy.decision_trace  [1 funcs]
    load_recent_decisions  CC=9  out:8
  src.koru.configurator  [4 funcs]
    configure_project  CC=2  out:9
    load_project_config  CC=4  out:5
    migrate_project_config  CC=2  out:9
    toggle_feature_sections  CC=6  out:13
  src.koru.context  [1 funcs]
    build_context  CC=6  out:16
  src.koru.context_render  [1 funcs]
    render_markdown_handoff  CC=10  out:47
  src.koru.control_commands  [1 funcs]
    api_command  CC=4  out:4
  src.koru.doctor  [1 funcs]
    run_diagnostics  CC=6  out:11
  src.koru.dotenv_loader  [1 funcs]
    load_dotenv  CC=7  out:5
  src.koru.env_config  [3 funcs]
    apply_env_updates  CC=1  out:6
    env_config_payload  CC=1  out:3
    write_env_config  CC=1  out:4
  src.koru.environment_profile  [1 funcs]
    environment_profile_payload  CC=1  out:2
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.interface_registry  [3 funcs]
    blocker_interface_payload  CC=2  out:2
    iter_interfaces  CC=1  out:1
    summarize_interfaces_by_family  CC=2  out:2
  src.koru.local_service  [2 funcs]
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:12
  src.koru.observability_dsl  [3 funcs]
    render_observability_path  CC=5  out:3
    stored_event_to_compact_line  CC=1  out:2
    stored_event_to_dsl  CC=1  out:2
  src.koru.observability_writer  [1 funcs]
    observability_event_store_path  CC=1  out:1
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=14  out:9
  src.koru.queue.runners  [1 funcs]
    run_process  CC=1  out:4
  src.koru.queue.ticket  [1 funcs]
    planfile_command  CC=5  out:7
  src.koru.scan  [1 funcs]
    run_scan  CC=5  out:9
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=1  out:4
  src.koru.topology  [2 funcs]
    load_topology  CC=1  out:9
    set_component_enabled  CC=1  out:1
  src.koru.wizard.cli  [1 funcs]
    propose_projects  CC=1  out:1
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koru.wizard.project  [1 funcs]
    _candidates_from_running_ide  CC=7  out:10
  src.koruapi.cli  [8 funcs]
    _action_dashboard  CC=1  out:1
    _action_invoke  CC=3  out:9
    _action_list  CC=2  out:4
    _action_local  CC=1  out:1
    _action_mcp  CC=1  out:1
    _build_parser  CC=2  out:17
    _parse_body  CC=3  out:5
    main  CC=3  out:6
  src.koruapi.dashboard  [11 funcs]
    _argv_has_flag  CC=4  out:2
    _env_truthy  CC=1  out:3
    _resolve_serve_auto_port  CC=4  out:5
    _resolve_serve_config  CC=3  out:11
    _resolve_serve_host  CC=5  out:3
    _resolve_serve_lan  CC=3  out:4
    _resolve_serve_port  CC=3  out:3
    _resolve_serve_queue_name  CC=4  out:2
    _resolve_serve_workspace  CC=3  out:3
    build_serve_parser  CC=1  out:12
  src.koruapi.dashboard_config  [13 funcs]
    _dashboard_config_path_payload  CC=1  out:3
    _dashboard_config_request_kwargs  CC=10  out:23
    _dotenv_path  CC=1  out:1
    _dotenv_payload  CC=3  out:4
    _effective_dashboard_config  CC=7  out:11
    _effective_serve_config  CC=4  out:10
    _save_dashboard_dotenv_from_body  CC=4  out:5
    _saved_serve_config  CC=2  out:2
    bool_from_dashboard  CC=3  out:4
    dashboard_config_payload  CC=1  out:6
  src.koruapi.dashboard_context  [2 funcs]
    dashboard_context_payload  CC=3  out:6
    dashboard_handoff_markdown  CC=1  out:2
  src.koruapi.dashboard_html  [3 funcs]
    render_action_error_html  CC=1  out:4
    render_action_success_html  CC=1  out:5
    render_create_ticket_success_html  CC=4  out:6
  src.koruapi.dashboard_http  [1 funcs]
    _safe_respond_json  CC=3  out:7
  src.koruapi.dashboard_observability  [3 funcs]
    _stored_event_payload  CC=1  out:0
    _trace_event_matches  CC=7  out:4
    dashboard_observability_trace_payload  CC=7  out:10
  src.koruapi.dashboard_plugin_logs  [5 funcs]
    _daemon_plugin_logs  CC=3  out:5
    _debug_log_row  CC=3  out:3
    _file_plugin_logs  CC=5  out:5
    _plugin_debug_log_path  CC=1  out:1
    dashboard_plugin_logs_payload  CC=2  out:3
  src.koruapi.dashboard_projects  [20 funcs]
    _collect_projects_for_ide  CC=8  out:16
    _dedupe_project_entries  CC=3  out:3
    _looks_like_real_project  CC=3  out:6
    _project_entry_from_terminal_cwd  CC=6  out:5
    _read_proc_children  CC=6  out:9
    _read_proc_comm  CC=2  out:3
    _read_proc_cwd_path  CC=4  out:4
    _read_workspace_folder  CC=8  out:12
    _running_ide_to_detected  CC=1  out:1
    _walk_descendant_pids  CC=6  out:8
  src.koruapi.dashboard_routes  [30 funcs]
    _build_dashboard_handler_impl  CC=1  out:9
    _config_defaults  CC=1  out:4
    _first_query_value  CC=4  out:3
    _get_autonomy_trace  CC=8  out:17
    _get_config  CC=1  out:4
    _get_context  CC=1  out:3
    _get_create_project_ticket_action  CC=2  out:8
    _get_dashboard  CC=1  out:2
    _get_env_config  CC=1  out:3
    _get_environment  CC=1  out:3
  src.koruapi.dashboard_runtime  [4 funcs]
    _interface_runtime_payload  CC=5  out:3
    runtime_context_error_payload  CC=1  out:5
    runtime_context_payload  CC=1  out:5
    save_runtime_context_config  CC=5  out:7
  src.koruapi.dashboard_serve  [10 funcs]
    _announce_bound_dashboard  CC=2  out:3
    _bind_or_print  CC=3  out:4
    _build_handler  CC=1  out:1
    _dashboard_urls  CC=1  out:1
    _emit_serve_event  CC=2  out:2
    _log_bind_summary  CC=6  out:6
    _prepare_bound_dashboard  CC=1  out:4
    _schedule_browser_open  CC=1  out:4
    serve  CC=3  out:7
    start_serve_background  CC=1  out:5
  src.koruapi.dashboard_serve_utils  [18 funcs]
    _address_in_use  CC=4  out:4
    _bind_auto_port  CC=7  out:5
    _bind_fixed_port  CC=4  out:4
    _bind_single  CC=1  out:2
    _build_handler_for  CC=1  out:1
    _cmdline_suggests_koru_serve  CC=3  out:3
    _cmdline_suggests_koru_serve_from_bytes  CC=3  out:7
    _dashboard_urls_for  CC=1  out:1
    _kill_prior_listeners  CC=5  out:5
    _listener_pids_for_tcp_port  CC=7  out:7
  src.koruapi.dashboard_state  [4 funcs]
    dashboard_ide_rows  CC=7  out:7
    dashboard_state  CC=3  out:8
    dashboard_urls  CC=3  out:3
    local_lan_addresses  CC=2  out:13
  src.koruapi.dashboard_tickets  [11 funcs]
    _append_dashboard_history  CC=2  out:7
    _build_ticket_scaffold  CC=8  out:9
    _find_ticket_in_sprints  CC=5  out:10
    _load_sprint_file  CC=3  out:3
    _write_sprint_file  CC=1  out:2
    bulk_waiting_input_action  CC=14  out:15
    create_ticket_from_dashboard  CC=8  out:22
    list_tickets  CC=9  out:6
    reorder_ticket_from_dashboard  CC=9  out:15
    run_planfile  CC=1  out:2
  src.koruapi.dashboard_topology  [2 funcs]
    apply_dashboard_topology_update  CC=1  out:1
    dashboard_topology_payload  CC=1  out:2
  src.koruapi.integrations  [2 funcs]
    get_integration  CC=1  out:1
    list_integrations  CC=4  out:2
  src.koruapi.invoke  [1 funcs]
    invoke_integration  CC=4  out:6
  src.koruapi.invoke_handlers  [18 funcs]
    _handle_autopilot_drive  CC=5  out:17
    _handle_autopilot_status  CC=2  out:3
    _handle_context_build  CC=1  out:3
    _handle_doctor_run  CC=1  out:2
    _handle_dsl_roundtrip  CC=3  out:6
    _handle_dsl_to_dsl  CC=2  out:3
    _handle_dsl_to_library  CC=3  out:4
    _handle_gate_regix  CC=3  out:5
    _handle_ide_commands  CC=3  out:6
    _handle_ide_scenario_schema  CC=1  out:1
  src.koruapi.local  [2 funcs]
    build_local_parser  CC=1  out:4
    local_main  CC=6  out:9
  src.koruapi.mcp  [1 funcs]
    mcp_main  CC=2  out:2
  src.koruapi.mcp_server  [4 funcs]
    mcp_serve_main  CC=2  out:10
    tool_list_tickets  CC=3  out:9
    tool_run_quality_gates  CC=6  out:13
    tool_run_ticket  CC=12  out:31
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
    do_GET  CC=9  out:21
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
    _build_parser  CC=1  out:13
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
  src.koruide.command_catalog  [2 funcs]
    build_ide_command_catalog  CC=4  out:4
    command_catalog_for_llm  CC=4  out:4
  src.koruide.command_scenario  [2 funcs]
    ide_command_scenario_schema  CC=1  out:0
    validate_ide_command_scenario  CC=37  out:67
  src.koruide.ide  [3 funcs]
    autopilot_ide_choices  CC=1  out:0
    detect_running_ides  CC=13  out:10
    normalize_ide_id  CC=6  out:11
  src.koruide.socket  [1 funcs]
    default_socket_path  CC=4  out:15
  src.korullm.strategies.base  [1 funcs]
    __repr__  CC=1  out:1
  src.korullm.strategies.registry  [4 funcs]
    _fallback_strategy  CC=3  out:2
    get_llm_strategy  CC=3  out:3
    resolve_active_llm_strategy  CC=1  out:1
    resolve_llm_strategy_from_environment  CC=9  out:17
  src.korumesh.browser_capture  [1 funcs]
    serve_browser_capture_http  CC=10  out:14
  src.korumesh.dashboard  [1 funcs]
    serve_mesh_http  CC=2  out:2
  src.korumesh.envelope  [1 funcs]
    sign_envelope  CC=3  out:8
  src.korumesh.keys  [2 funcs]
    load_mesh_key  CC=2  out:6
    write_mesh_key  CC=3  out:6
  src.korumesh.transport  [1 funcs]
    publish_envelope  CC=4  out:9
  src.koruobserve.bootstrap  [3 funcs]
    _config_has_v2_sections  CC=2  out:1
    ensure_mesh_key  CC=3  out:6
    ensure_observe_config  CC=3  out:9
  src.koruobserve.cli  [11 funcs]
    _cmd_down  CC=2  out:4
    _cmd_grid  CC=2  out:8
    _cmd_install  CC=2  out:2
    _cmd_providers  CC=5  out:11
    _cmd_status  CC=3  out:6
    _cmd_trace  CC=12  out:16
    _cmd_up  CC=2  out:6
    _missing_observe_packages  CC=3  out:1
    _pip_install  CC=2  out:4
    _require_observe_runtime  CC=5  out:6
  src.koruobserve.cli_parser  [4 funcs]
    _add_subproject  CC=1  out:1
    _register_up_arguments  CC=1  out:5
    build_observe_parser  CC=7  out:17
    project_path  CC=3  out:6
  src.koruobserve.diagnostics  [8 funcs]
    _last_failure_line  CC=3  out:4
    _monitors_from_mss  CC=8  out:9
    _monitors_from_xrandr  CC=6  out:10
    _read_log_tail  CC=3  out:5
    _session_type  CC=4  out:3
    _wayland_hint  CC=2  out:0
    capture_diagnostics  CC=7  out:7
    detect_monitors  CC=3  out:2
  src.koruobserve.lifecycle  [11 funcs]
    _is_alive  CC=2  out:1
    _pick_free_port  CC=3  out:6
    _pids_matching_koru_cmdline  CC=10  out:11
    _read_pid  CC=3  out:5
    _resolve_serve_settings  CC=4  out:7
    _spawn  CC=1  out:11
    _stop_orphan_observe_processes  CC=3  out:6
    _stop_pid  CC=3  out:5
    observe_down  CC=2  out:6
    observe_status  CC=3  out:7
  src.koruobserve.paths  [4 funcs]
    logfile  CC=1  out:1
    pidfile  CC=1  out:1
    runtime_dir  CC=1  out:1
    state_file  CC=1  out:1
  src.koruobserve.providers_cli  [10 funcs]
    cmd_providers_list  CC=2  out:5
    cmd_providers_reset  CC=2  out:5
    cmd_providers_test  CC=3  out:6
    providers_list_payload  CC=1  out:1
    providers_list_text  CC=13  out:16
    providers_reset_consent  CC=5  out:9
    providers_reset_text  CC=3  out:2
    providers_test_payload  CC=6  out:5
    providers_test_text  CC=13  out:20
    screencast_session_path  CC=1  out:1
  src.koruos.strategies.base  [1 funcs]
    __repr__  CC=1  out:1
  src.koruos.strategies.darwin  [1 funcs]
    focus_window  CC=4  out:5
  src.koruos.strategies.wayland_linux  [8 funcs]
    _focus_via_wmctrl  CC=4  out:3
    _inject_via_wtype  CC=9  out:7
    _inject_via_ydotool  CC=7  out:10
    inject_keys  CC=9  out:8
    _gnome_compositor  CC=4  out:3
    _prefer_ydotool  CC=3  out:4
    _run  CC=1  out:1
    _scan_for_key  CC=5  out:1
  src.koruos.strategies.x11_linux  [3 funcs]
    _focus_via_wmctrl  CC=4  out:3
    _focus_via_xdotool  CC=11  out:10
    _inject_via_xdotool  CC=3  out:4
  src.koruvision.agent  [5 funcs]
    _capture_cycle  CC=2  out:2
    capture_all_once  CC=1  out:1
    capture_once  CC=1  out:1
    normalize_capture_interval  CC=2  out:2
    run_capture_loop  CC=11  out:6
  src.koruvision.capture  [4 funcs]
    _frame  CC=1  out:1
    capture_all_monitors  CC=2  out:3
    capture_monitor_png  CC=1  out:3
    list_monitors  CC=2  out:2
  src.koruvision.capture_mss  [12 funcs]
    _grab_all_mss_raw  CC=5  out:6
    _grab_single_mss_raw  CC=6  out:10
    command_candidates  CC=3  out:1
    command_capture_dict  CC=4  out:6
    frame_from_shot  CC=2  out:12
    grab_target  CC=2  out:4
    is_wayland  CC=2  out:6
    ordered_monitor_indices  CC=5  out:4
    png_dimensions  CC=4  out:5
    png_payload_descriptor  CC=2  out:6
  src.koruvision.capture_probe  [2 funcs]
    python_can_capture  CC=2  out:2
    resolve_observe_python  CC=7  out:7
  src.koruvision.cli  [4 funcs]
    _maybe_publish_mesh  CC=2  out:7
    _mesh_publish_enabled  CC=5  out:11
    _vision_interval  CC=4  out:8
    vision_main  CC=4  out:13
  src.koruvision.cli_parser  [4 funcs]
    _add_agent_subparser  CC=1  out:5
    _add_capture_subparser  CC=1  out:3
    build_vision_parser  CC=1  out:6
    register_mesh_publish_args  CC=2  out:6
  src.koruvision.mesh  [4 funcs]
    _vision_mime  CC=5  out:3
    publish_vision_frame  CC=1  out:3
    resolve_mesh_publish  CC=8  out:12
    vision_frame_envelope  CC=1  out:2
  src.koruvision.portal_capture  [2 funcs]
    _portal_python  CC=6  out:4
    capture_portal_png  CC=8  out:11
  src.koruvision.providers.base  [2 funcs]
    frame_from_png  CC=5  out:12
    png_dimensions  CC=4  out:5
  src.koruvision.providers.browser_getdisplay  [1 funcs]
    browser_capture_requested  CC=2  out:2
  src.koruvision.providers.cli_tools  [4 funcs]
    availability  CC=3  out:4
    capture_all  CC=1  out:1
    list_monitors  CC=1  out:1
    _tool_available  CC=1  out:2
  src.koruvision.providers.detector  [12 funcs]
    _auto_failure_message  CC=3  out:2
    _auto_provider_order  CC=11  out:18
    _available_ranked_providers  CC=5  out:5
    _forced_provider_rank  CC=3  out:3
    _should_report_auto_portal  CC=4  out:2
    capture_all_with_providers  CC=8  out:14
    capture_one_with_providers  CC=6  out:13
    list_provider_status  CC=2  out:3
    monitors_via_xrandr  CC=6  out:10
    probe_capture_providers  CC=10  out:19
  src.koruvision.providers.env  [3 funcs]
    capture_provider_pref  CC=4  out:6
    looks_headless  CC=3  out:4
    portal_possible  CC=3  out:5
  src.koruvision.providers.obs_websocket  [1 funcs]
    probe_obs_reachable  CC=6  out:5
  src.koruvision.providers.registry  [2 funcs]
    all_providers  CC=1  out:1
    provider_by_name  CC=1  out:3
  src.koruvision.providers.screencast_session  [2 funcs]
    clear_session_file  CC=3  out:3
    session_file_for_project  CC=1  out:1
  src.koruvision.scaling  [3 funcs]
    downscale_rgb_nearest  CC=6  out:5
    resolve_scale  CC=4  out:5
    rgb_mostly_black  CC=5  out:4

EDGES:
  examples.remote_orchestration_demo.run_multi_node_orchestration → scripts.koru-soak-monitor.print
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
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.logfile
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.runtime_dir
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._read_pid → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._stop_pid → src.koruobserve.lifecycle._read_pid
  src.koruobserve.lifecycle._stop_pid → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._pids_matching_koru_cmdline → src.koru.wizard.gui.static.wizard.list
  src.koruobserve.lifecycle._stop_orphan_observe_processes → src.koruobserve.lifecycle._pids_matching_koru_cmdline
  src.koruobserve.lifecycle._stop_orphan_observe_processes → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle.observe_down
  src.koruobserve.lifecycle.observe_up → src.koruobserve.bootstrap.ensure_observe_config
  src.koruobserve.lifecycle.observe_up → src.koruobserve.bootstrap.ensure_mesh_key
  src.koruobserve.lifecycle.observe_up → src.koruvision.capture_probe.resolve_observe_python
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._resolve_serve_settings
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._pick_free_port
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._spawn
  src.koruobserve.lifecycle.observe_down → src.koruobserve.lifecycle._stop_orphan_observe_processes
  src.koruobserve.lifecycle.observe_down → src.koruobserve.lifecycle._stop_pid
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (7)

**`koru Command Tests (live — not for WUP --dry-run quick probes)`**

**`koru Command Tests (WUP quick / dry-run safe)`**

**`koru-api Command Tests (WUP quick / dry-run safe)`**

**`koru-dsl Command Tests (WUP quick / dry-run safe)`**

**`koru-wup-testql Command Tests (WUP quick / dry-run safe)`**

**`CLI Smoke Tests`**

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.56s
# nodes: 427 | edges: 500 | modules: 100
# CC̄=3.5

HUBS[20]:
  scripts.koru-soak-monitor.print
    CC=0  in:593  out:0  total:593
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:141  out:9  total:150
  src.koruide.ide.normalize_ide_id
    CC=6  in:64  out:11  total:75
  src.koruide.command_scenario.validate_ide_command_scenario
    CC=37  in:3  out:67  total:70
  koru.activity_log.activity
    CC=6  in:47  out:13  total:60
  src.koru.context_render.render_markdown_handoff
    CC=10  in:6  out:47  total:53
  src.koru.events.emit_management_event
    CC=8  in:31  out:7  total:38
  src.koruide.ide.detect_running_ides
    CC=13  in:24  out:10  total:34
  src.koruobserve.lifecycle.observe_up
    CC=4  in:1  out:32  total:33
  src.koruapi.mcp_server.tool_run_ticket
    CC=12  in:1  out:31  total:32
  src.koruide.socket.default_socket_path
    CC=4  in:16  out:15  total:31
  services.healing-webhook.app._resolve_affected_files
    CC=11  in:2  out:24  total:26
  services.healing-webhook.ticket_builder.build_ticket_payload
    CC=11  in:1  out:25  total:26
  src.koru.context.build_context
    CC=6  in:9  out:16  total:25
  plugins.koru-autopilot-shared.src.ack-payload.type
    CC=3  in:25  out:0  total:25
  src.koruapi.dashboard_config._dashboard_config_request_kwargs
    CC=10  in:1  out:23  total:24
  src.koru.queue.ticket.planfile_command
    CC=5  in:17  out:7  total:24
  src.koruapi.dashboard_tickets.create_ticket_from_dashboard
    CC=8  in:2  out:22  total:24
  examples.remote_orchestration_demo.run_multi_node_orchestration
    CC=9  in:0  out:24  total:24
  src.koruapi.dashboard_routes._post_remote_drive
    CC=9  in:0  out:24  total:24

MODULES:
  examples.remote_orchestration_demo  [1 funcs]
    run_multi_node_orchestration  CC=9  out:24
  koru.activity_log  [1 funcs]
    activity  CC=6  out:13
  koru.ide_client  [1 funcs]
    build_ide_client  CC=3  out:5
  plugins.koru-autopilot-shared.src.ack-payload  [2 funcs]
    bytes  CC=2  out:0
    type  CC=3  out:0
  plugins.koru-autopilot-vscode.src.extension  [1 funcs]
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
  src.koru.autonomous_process_guard  [2 funcs]
    find_existing_autonomous_processes  CC=11  out:16
    find_existing_wup_processes  CC=11  out:15
  src.koru.autonomy.decision_trace  [1 funcs]
    load_recent_decisions  CC=9  out:8
  src.koru.configurator  [4 funcs]
    configure_project  CC=2  out:9
    load_project_config  CC=4  out:5
    migrate_project_config  CC=2  out:9
    toggle_feature_sections  CC=6  out:13
  src.koru.context  [1 funcs]
    build_context  CC=6  out:16
  src.koru.context_render  [1 funcs]
    render_markdown_handoff  CC=10  out:47
  src.koru.control_commands  [1 funcs]
    api_command  CC=4  out:4
  src.koru.doctor  [1 funcs]
    run_diagnostics  CC=6  out:11
  src.koru.dotenv_loader  [1 funcs]
    load_dotenv  CC=7  out:5
  src.koru.env_config  [3 funcs]
    apply_env_updates  CC=1  out:6
    env_config_payload  CC=1  out:3
    write_env_config  CC=1  out:4
  src.koru.environment_profile  [1 funcs]
    environment_profile_payload  CC=1  out:2
  src.koru.events  [1 funcs]
    emit_management_event  CC=8  out:7
  src.koru.interface_registry  [3 funcs]
    blocker_interface_payload  CC=2  out:2
    iter_interfaces  CC=1  out:1
    summarize_interfaces_by_family  CC=2  out:2
  src.koru.local_service  [2 funcs]
    default_local_service_config  CC=2  out:7
    run_local_service  CC=3  out:12
  src.koru.observability_dsl  [3 funcs]
    render_observability_path  CC=5  out:3
    stored_event_to_compact_line  CC=1  out:2
    stored_event_to_dsl  CC=1  out:2
  src.koru.observability_writer  [1 funcs]
    observability_event_store_path  CC=1  out:1
  src.koru.queue.loop  [1 funcs]
    run_planfile_queue_loop  CC=14  out:9
  src.koru.queue.runners  [1 funcs]
    run_process  CC=1  out:4
  src.koru.queue.ticket  [1 funcs]
    planfile_command  CC=5  out:7
  src.koru.scan  [1 funcs]
    run_scan  CC=5  out:9
  src.koru.tasks  [1 funcs]
    create_nl_task  CC=1  out:4
  src.koru.topology  [2 funcs]
    load_topology  CC=1  out:9
    set_component_enabled  CC=1  out:1
  src.koru.wizard.cli  [1 funcs]
    propose_projects  CC=1  out:1
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koru.wizard.project  [1 funcs]
    _candidates_from_running_ide  CC=7  out:10
  src.koruapi.cli  [8 funcs]
    _action_dashboard  CC=1  out:1
    _action_invoke  CC=3  out:9
    _action_list  CC=2  out:4
    _action_local  CC=1  out:1
    _action_mcp  CC=1  out:1
    _build_parser  CC=2  out:17
    _parse_body  CC=3  out:5
    main  CC=3  out:6
  src.koruapi.dashboard  [11 funcs]
    _argv_has_flag  CC=4  out:2
    _env_truthy  CC=1  out:3
    _resolve_serve_auto_port  CC=4  out:5
    _resolve_serve_config  CC=3  out:11
    _resolve_serve_host  CC=5  out:3
    _resolve_serve_lan  CC=3  out:4
    _resolve_serve_port  CC=3  out:3
    _resolve_serve_queue_name  CC=4  out:2
    _resolve_serve_workspace  CC=3  out:3
    build_serve_parser  CC=1  out:12
  src.koruapi.dashboard_config  [13 funcs]
    _dashboard_config_path_payload  CC=1  out:3
    _dashboard_config_request_kwargs  CC=10  out:23
    _dotenv_path  CC=1  out:1
    _dotenv_payload  CC=3  out:4
    _effective_dashboard_config  CC=7  out:11
    _effective_serve_config  CC=4  out:10
    _save_dashboard_dotenv_from_body  CC=4  out:5
    _saved_serve_config  CC=2  out:2
    bool_from_dashboard  CC=3  out:4
    dashboard_config_payload  CC=1  out:6
  src.koruapi.dashboard_context  [2 funcs]
    dashboard_context_payload  CC=3  out:6
    dashboard_handoff_markdown  CC=1  out:2
  src.koruapi.dashboard_html  [3 funcs]
    render_action_error_html  CC=1  out:4
    render_action_success_html  CC=1  out:5
    render_create_ticket_success_html  CC=4  out:6
  src.koruapi.dashboard_http  [1 funcs]
    _safe_respond_json  CC=3  out:7
  src.koruapi.dashboard_observability  [3 funcs]
    _stored_event_payload  CC=1  out:0
    _trace_event_matches  CC=7  out:4
    dashboard_observability_trace_payload  CC=7  out:10
  src.koruapi.dashboard_plugin_logs  [5 funcs]
    _daemon_plugin_logs  CC=3  out:5
    _debug_log_row  CC=3  out:3
    _file_plugin_logs  CC=5  out:5
    _plugin_debug_log_path  CC=1  out:1
    dashboard_plugin_logs_payload  CC=2  out:3
  src.koruapi.dashboard_projects  [20 funcs]
    _collect_projects_for_ide  CC=8  out:16
    _dedupe_project_entries  CC=3  out:3
    _looks_like_real_project  CC=3  out:6
    _project_entry_from_terminal_cwd  CC=6  out:5
    _read_proc_children  CC=6  out:9
    _read_proc_comm  CC=2  out:3
    _read_proc_cwd_path  CC=4  out:4
    _read_workspace_folder  CC=8  out:12
    _running_ide_to_detected  CC=1  out:1
    _walk_descendant_pids  CC=6  out:8
  src.koruapi.dashboard_routes  [30 funcs]
    _build_dashboard_handler_impl  CC=1  out:9
    _config_defaults  CC=1  out:4
    _first_query_value  CC=4  out:3
    _get_autonomy_trace  CC=8  out:17
    _get_config  CC=1  out:4
    _get_context  CC=1  out:3
    _get_create_project_ticket_action  CC=2  out:8
    _get_dashboard  CC=1  out:2
    _get_env_config  CC=1  out:3
    _get_environment  CC=1  out:3
  src.koruapi.dashboard_runtime  [4 funcs]
    _interface_runtime_payload  CC=5  out:3
    runtime_context_error_payload  CC=1  out:5
    runtime_context_payload  CC=1  out:5
    save_runtime_context_config  CC=5  out:7
  src.koruapi.dashboard_serve  [10 funcs]
    _announce_bound_dashboard  CC=2  out:3
    _bind_or_print  CC=3  out:4
    _build_handler  CC=1  out:1
    _dashboard_urls  CC=1  out:1
    _emit_serve_event  CC=2  out:2
    _log_bind_summary  CC=6  out:6
    _prepare_bound_dashboard  CC=1  out:4
    _schedule_browser_open  CC=1  out:4
    serve  CC=3  out:7
    start_serve_background  CC=1  out:5
  src.koruapi.dashboard_serve_utils  [18 funcs]
    _address_in_use  CC=4  out:4
    _bind_auto_port  CC=7  out:5
    _bind_fixed_port  CC=4  out:4
    _bind_single  CC=1  out:2
    _build_handler_for  CC=1  out:1
    _cmdline_suggests_koru_serve  CC=3  out:3
    _cmdline_suggests_koru_serve_from_bytes  CC=3  out:7
    _dashboard_urls_for  CC=1  out:1
    _kill_prior_listeners  CC=5  out:5
    _listener_pids_for_tcp_port  CC=7  out:7
  src.koruapi.dashboard_state  [4 funcs]
    dashboard_ide_rows  CC=7  out:7
    dashboard_state  CC=3  out:8
    dashboard_urls  CC=3  out:3
    local_lan_addresses  CC=2  out:13
  src.koruapi.dashboard_tickets  [11 funcs]
    _append_dashboard_history  CC=2  out:7
    _build_ticket_scaffold  CC=8  out:9
    _find_ticket_in_sprints  CC=5  out:10
    _load_sprint_file  CC=3  out:3
    _write_sprint_file  CC=1  out:2
    bulk_waiting_input_action  CC=14  out:15
    create_ticket_from_dashboard  CC=8  out:22
    list_tickets  CC=9  out:6
    reorder_ticket_from_dashboard  CC=9  out:15
    run_planfile  CC=1  out:2
  src.koruapi.dashboard_topology  [2 funcs]
    apply_dashboard_topology_update  CC=1  out:1
    dashboard_topology_payload  CC=1  out:2
  src.koruapi.integrations  [2 funcs]
    get_integration  CC=1  out:1
    list_integrations  CC=4  out:2
  src.koruapi.invoke  [1 funcs]
    invoke_integration  CC=4  out:6
  src.koruapi.invoke_handlers  [18 funcs]
    _handle_autopilot_drive  CC=5  out:17
    _handle_autopilot_status  CC=2  out:3
    _handle_context_build  CC=1  out:3
    _handle_doctor_run  CC=1  out:2
    _handle_dsl_roundtrip  CC=3  out:6
    _handle_dsl_to_dsl  CC=2  out:3
    _handle_dsl_to_library  CC=3  out:4
    _handle_gate_regix  CC=3  out:5
    _handle_ide_commands  CC=3  out:6
    _handle_ide_scenario_schema  CC=1  out:1
  src.koruapi.local  [2 funcs]
    build_local_parser  CC=1  out:4
    local_main  CC=6  out:9
  src.koruapi.mcp  [1 funcs]
    mcp_main  CC=2  out:2
  src.koruapi.mcp_server  [4 funcs]
    mcp_serve_main  CC=2  out:10
    tool_list_tickets  CC=3  out:9
    tool_run_quality_gates  CC=6  out:13
    tool_run_ticket  CC=12  out:31
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
    do_GET  CC=9  out:21
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
    _build_parser  CC=1  out:13
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
  src.koruide.command_catalog  [2 funcs]
    build_ide_command_catalog  CC=4  out:4
    command_catalog_for_llm  CC=4  out:4
  src.koruide.command_scenario  [2 funcs]
    ide_command_scenario_schema  CC=1  out:0
    validate_ide_command_scenario  CC=37  out:67
  src.koruide.ide  [3 funcs]
    autopilot_ide_choices  CC=1  out:0
    detect_running_ides  CC=13  out:10
    normalize_ide_id  CC=6  out:11
  src.koruide.socket  [1 funcs]
    default_socket_path  CC=4  out:15
  src.korullm.strategies.base  [1 funcs]
    __repr__  CC=1  out:1
  src.korullm.strategies.registry  [4 funcs]
    _fallback_strategy  CC=3  out:2
    get_llm_strategy  CC=3  out:3
    resolve_active_llm_strategy  CC=1  out:1
    resolve_llm_strategy_from_environment  CC=9  out:17
  src.korumesh.browser_capture  [1 funcs]
    serve_browser_capture_http  CC=10  out:14
  src.korumesh.dashboard  [1 funcs]
    serve_mesh_http  CC=2  out:2
  src.korumesh.envelope  [1 funcs]
    sign_envelope  CC=3  out:8
  src.korumesh.keys  [2 funcs]
    load_mesh_key  CC=2  out:6
    write_mesh_key  CC=3  out:6
  src.korumesh.transport  [1 funcs]
    publish_envelope  CC=4  out:9
  src.koruobserve.bootstrap  [3 funcs]
    _config_has_v2_sections  CC=2  out:1
    ensure_mesh_key  CC=3  out:6
    ensure_observe_config  CC=3  out:9
  src.koruobserve.cli  [11 funcs]
    _cmd_down  CC=2  out:4
    _cmd_grid  CC=2  out:8
    _cmd_install  CC=2  out:2
    _cmd_providers  CC=5  out:11
    _cmd_status  CC=3  out:6
    _cmd_trace  CC=12  out:16
    _cmd_up  CC=2  out:6
    _missing_observe_packages  CC=3  out:1
    _pip_install  CC=2  out:4
    _require_observe_runtime  CC=5  out:6
  src.koruobserve.cli_parser  [4 funcs]
    _add_subproject  CC=1  out:1
    _register_up_arguments  CC=1  out:5
    build_observe_parser  CC=7  out:17
    project_path  CC=3  out:6
  src.koruobserve.diagnostics  [8 funcs]
    _last_failure_line  CC=3  out:4
    _monitors_from_mss  CC=8  out:9
    _monitors_from_xrandr  CC=6  out:10
    _read_log_tail  CC=3  out:5
    _session_type  CC=4  out:3
    _wayland_hint  CC=2  out:0
    capture_diagnostics  CC=7  out:7
    detect_monitors  CC=3  out:2
  src.koruobserve.lifecycle  [11 funcs]
    _is_alive  CC=2  out:1
    _pick_free_port  CC=3  out:6
    _pids_matching_koru_cmdline  CC=10  out:11
    _read_pid  CC=3  out:5
    _resolve_serve_settings  CC=4  out:7
    _spawn  CC=1  out:11
    _stop_orphan_observe_processes  CC=3  out:6
    _stop_pid  CC=3  out:5
    observe_down  CC=2  out:6
    observe_status  CC=3  out:7
  src.koruobserve.paths  [4 funcs]
    logfile  CC=1  out:1
    pidfile  CC=1  out:1
    runtime_dir  CC=1  out:1
    state_file  CC=1  out:1
  src.koruobserve.providers_cli  [10 funcs]
    cmd_providers_list  CC=2  out:5
    cmd_providers_reset  CC=2  out:5
    cmd_providers_test  CC=3  out:6
    providers_list_payload  CC=1  out:1
    providers_list_text  CC=13  out:16
    providers_reset_consent  CC=5  out:9
    providers_reset_text  CC=3  out:2
    providers_test_payload  CC=6  out:5
    providers_test_text  CC=13  out:20
    screencast_session_path  CC=1  out:1
  src.koruos.strategies.base  [1 funcs]
    __repr__  CC=1  out:1
  src.koruos.strategies.darwin  [1 funcs]
    focus_window  CC=4  out:5
  src.koruos.strategies.wayland_linux  [8 funcs]
    _focus_via_wmctrl  CC=4  out:3
    _inject_via_wtype  CC=9  out:7
    _inject_via_ydotool  CC=7  out:10
    inject_keys  CC=9  out:8
    _gnome_compositor  CC=4  out:3
    _prefer_ydotool  CC=3  out:4
    _run  CC=1  out:1
    _scan_for_key  CC=5  out:1
  src.koruos.strategies.x11_linux  [3 funcs]
    _focus_via_wmctrl  CC=4  out:3
    _focus_via_xdotool  CC=11  out:10
    _inject_via_xdotool  CC=3  out:4
  src.koruvision.agent  [5 funcs]
    _capture_cycle  CC=2  out:2
    capture_all_once  CC=1  out:1
    capture_once  CC=1  out:1
    normalize_capture_interval  CC=2  out:2
    run_capture_loop  CC=11  out:6
  src.koruvision.capture  [4 funcs]
    _frame  CC=1  out:1
    capture_all_monitors  CC=2  out:3
    capture_monitor_png  CC=1  out:3
    list_monitors  CC=2  out:2
  src.koruvision.capture_mss  [12 funcs]
    _grab_all_mss_raw  CC=5  out:6
    _grab_single_mss_raw  CC=6  out:10
    command_candidates  CC=3  out:1
    command_capture_dict  CC=4  out:6
    frame_from_shot  CC=2  out:12
    grab_target  CC=2  out:4
    is_wayland  CC=2  out:6
    ordered_monitor_indices  CC=5  out:4
    png_dimensions  CC=4  out:5
    png_payload_descriptor  CC=2  out:6
  src.koruvision.capture_probe  [2 funcs]
    python_can_capture  CC=2  out:2
    resolve_observe_python  CC=7  out:7
  src.koruvision.cli  [4 funcs]
    _maybe_publish_mesh  CC=2  out:7
    _mesh_publish_enabled  CC=5  out:11
    _vision_interval  CC=4  out:8
    vision_main  CC=4  out:13
  src.koruvision.cli_parser  [4 funcs]
    _add_agent_subparser  CC=1  out:5
    _add_capture_subparser  CC=1  out:3
    build_vision_parser  CC=1  out:6
    register_mesh_publish_args  CC=2  out:6
  src.koruvision.mesh  [4 funcs]
    _vision_mime  CC=5  out:3
    publish_vision_frame  CC=1  out:3
    resolve_mesh_publish  CC=8  out:12
    vision_frame_envelope  CC=1  out:2
  src.koruvision.portal_capture  [2 funcs]
    _portal_python  CC=6  out:4
    capture_portal_png  CC=8  out:11
  src.koruvision.providers.base  [2 funcs]
    frame_from_png  CC=5  out:12
    png_dimensions  CC=4  out:5
  src.koruvision.providers.browser_getdisplay  [1 funcs]
    browser_capture_requested  CC=2  out:2
  src.koruvision.providers.cli_tools  [4 funcs]
    availability  CC=3  out:4
    capture_all  CC=1  out:1
    list_monitors  CC=1  out:1
    _tool_available  CC=1  out:2
  src.koruvision.providers.detector  [12 funcs]
    _auto_failure_message  CC=3  out:2
    _auto_provider_order  CC=11  out:18
    _available_ranked_providers  CC=5  out:5
    _forced_provider_rank  CC=3  out:3
    _should_report_auto_portal  CC=4  out:2
    capture_all_with_providers  CC=8  out:14
    capture_one_with_providers  CC=6  out:13
    list_provider_status  CC=2  out:3
    monitors_via_xrandr  CC=6  out:10
    probe_capture_providers  CC=10  out:19
  src.koruvision.providers.env  [3 funcs]
    capture_provider_pref  CC=4  out:6
    looks_headless  CC=3  out:4
    portal_possible  CC=3  out:5
  src.koruvision.providers.obs_websocket  [1 funcs]
    probe_obs_reachable  CC=6  out:5
  src.koruvision.providers.registry  [2 funcs]
    all_providers  CC=1  out:1
    provider_by_name  CC=1  out:3
  src.koruvision.providers.screencast_session  [2 funcs]
    clear_session_file  CC=3  out:3
    session_file_for_project  CC=1  out:1
  src.koruvision.scaling  [3 funcs]
    downscale_rgb_nearest  CC=6  out:5
    resolve_scale  CC=4  out:5
    rgb_mostly_black  CC=5  out:4

EDGES:
  examples.remote_orchestration_demo.run_multi_node_orchestration → scripts.koru-soak-monitor.print
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
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.logfile
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.runtime_dir
  src.koruobserve.lifecycle._spawn → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._read_pid → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._stop_pid → src.koruobserve.lifecycle._read_pid
  src.koruobserve.lifecycle._stop_pid → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle._pids_matching_koru_cmdline → src.koru.wizard.gui.static.wizard.list
  src.koruobserve.lifecycle._stop_orphan_observe_processes → src.koruobserve.lifecycle._pids_matching_koru_cmdline
  src.koruobserve.lifecycle._stop_orphan_observe_processes → src.koruobserve.paths.pidfile
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle.observe_down
  src.koruobserve.lifecycle.observe_up → src.koruobserve.bootstrap.ensure_observe_config
  src.koruobserve.lifecycle.observe_up → src.koruobserve.bootstrap.ensure_mesh_key
  src.koruobserve.lifecycle.observe_up → src.koruvision.capture_probe.resolve_observe_python
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._resolve_serve_settings
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._pick_free_port
  src.koruobserve.lifecycle.observe_up → src.koruobserve.lifecycle._spawn
  src.koruobserve.lifecycle.observe_down → src.koruobserve.lifecycle._stop_orphan_observe_processes
  src.koruobserve.lifecycle.observe_down → src.koruobserve.lifecycle._stop_pid
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 621f 106277L | python:439,typescript:65,shell:49,yaml:24,json:16,yml:10,kotlin:6,txt:2,toml:1,md:1,javascript:1,properties:1,xml:1 | 2026-05-25
# generated in 1.30s
# CC̅=3.5 | critical:6/4926 | dups:10 | cycles:0

HEALTH[7]:
  🔴 DUP   10 classes duplicated
  🟡 CC    handle_console_log CC=18 (limit:15)
  🟡 CC    _path_step CC=32 (limit:15)
  🟡 CC    _compact_data CC=15 (limit:15)
  🟡 CC    retry_plugin_wait_after_reload CC=15 (limit:15)
  🟡 CC    validate_ide_command_scenario CC=37 (limit:15)
  🟡 CC    _performInject CC=15 (limit:15)

REFACTOR[2]:
  1. rm duplicates  (-10 dup classes)
  2. split 6 high-CC methods  (CC>15)

PIPELINES[1770]:
  [1] Src [run_multi_node_orchestration]: run_multi_node_orchestration → print
      PURITY: 100% pure
  [2] Src [heal_rebuild_restore]: heal_rebuild_restore → _run_docker
      PURITY: 100% pure
  [3] Src [heal_annotate]: heal_annotate → _record_action
      PURITY: 100% pure
  [4] Src [_run_vallm_validate]: _run_vallm_validate
      PURITY: 100% pure
  [5] Src [heal_vallm_validate]: heal_vallm_validate → _resolve_affected_files → _infer_paths
      PURITY: 100% pure
  [6] Src [heal_redup_check]: heal_redup_check → _run_redup_check → _update_redup_metrics
      PURITY: 100% pure
  [7] Src [healthz]: healthz
      PURITY: 100% pure
  [8] Src [metrics]: metrics
      PURITY: 100% pure
  [9] Src [get_history]: get_history → list → escapeHtml
      PURITY: 100% pure
  [10] Src [alertmanager_webhook]: alertmanager_webhook → _resolve_strategy
      PURITY: 100% pure
  [11] Src [probe_failure]: probe_failure → create_planfile_ticket → _enrich_ticket_with_vallm → _resolve_affected_files → ...(1 more)
      PURITY: 100% pure
  [12] Src [get_tickets]: get_tickets
      PURITY: 100% pure
  [13] Src [to_json]: to_json
      PURITY: 100% pure
  [14] Src [_cmd_install]: _cmd_install → _missing_observe_packages
      PURITY: 100% pure
  [15] Src [_cmd_up]: _cmd_up → _require_observe_runtime → _missing_observe_packages
      PURITY: 100% pure
  [16] Src [_cmd_down]: _cmd_down → observe_down → _stop_orphan_observe_processes → _pids_matching_koru_cmdline → ...(2 more)
      PURITY: 100% pure
  [17] Src [_cmd_status]: _cmd_status → observe_status → _read_pid → pidfile → ...(1 more)
      PURITY: 100% pure
  [18] Src [_cmd_grid]: _cmd_grid → state_file → runtime_dir
      PURITY: 100% pure
  [19] Src [_cmd_trace]: _cmd_trace → project_path
      PURITY: 100% pure
  [20] Src [_cmd_providers]: _cmd_providers → project_path
      PURITY: 100% pure
  [21] Src [observe_main]: observe_main → print
      PURITY: 100% pure
  [22] Src [__post_init__]: __post_init__
      PURITY: 100% pure
  [23] Src [_term_program_is_vscode_family]: _term_program_is_vscode_family
      PURITY: 100% pure
  [24] Src [__repr__]: __repr__ → type
      PURITY: 100% pure
  [25] Src [register_os_strategy]: register_os_strategy
      PURITY: 100% pure
  [26] Src [list_os_strategy_ids]: list_os_strategy_ids
      PURITY: 100% pure
  [27] Src [matches_current_environment]: matches_current_environment
      PURITY: 100% pure
  [28] Src [capabilities]: capabilities
      PURITY: 100% pure
  [29] Src [focus_window]: focus_window
      PURITY: 100% pure
  [30] Src [inject_keys]: inject_keys → _prefer_ydotool → _gnome_compositor
      PURITY: 100% pure
  [31] Src [_focus_via_wmctrl]: _focus_via_wmctrl → _run
      PURITY: 100% pure
  [32] Src [_inject_via_wtype]: _inject_via_wtype → _run
      PURITY: 100% pure
  [33] Src [_inject_via_ydotool]: _inject_via_ydotool → _scan_for_key
      PURITY: 100% pure
  [34] Src [_run]: _run
      PURITY: 100% pure
  [35] Src [matches_current_environment]: matches_current_environment
      PURITY: 100% pure
  [36] Src [capabilities]: capabilities
      PURITY: 100% pure
  [37] Src [focus_window]: focus_window
      PURITY: 100% pure
  [38] Src [inject_keys]: inject_keys
      PURITY: 100% pure
  [39] Src [_focus_via_xdotool]: _focus_via_xdotool → _run
      PURITY: 100% pure
  [40] Src [_focus_via_wmctrl]: _focus_via_wmctrl → _run
      PURITY: 100% pure
  [41] Src [_inject_via_xdotool]: _inject_via_xdotool → list → escapeHtml
      PURITY: 100% pure
  [42] Src [_run]: _run
      PURITY: 100% pure
  [43] Src [capabilities]: capabilities
      PURITY: 100% pure
  [44] Src [focus_window]: focus_window → _run
      PURITY: 100% pure
  [45] Src [matches_current_environment]: matches_current_environment
      PURITY: 100% pure
  [46] Src [capabilities]: capabilities
      PURITY: 100% pure
  [47] Src [focus_window]: focus_window
      PURITY: 100% pure
  [48] Src [main]: main → _read_input
      PURITY: 100% pure
  [49] Src [_handle_set]: _handle_set
      PURITY: 100% pure
  [50] Src [_handle_wait]: _handle_wait
      PURITY: 100% pure

LAYERS:
  examples/                       CC̄=9.0    ←in:0  →out:12  !! split
  │ bootstrap.planfile.yaml    425L  0C    0m  CC=0.0    ←0
  │ remote_orchestration_demo    69L  0C    1m  CC=9      ←0
  │ run-e2e.sh                  43L  0C    0m  CC=0.0    ←0
  │ gitlab-ci.example.yml       41L  0C    0m  CC=0.0    ←0
  │ docker-compose-remote-mesh.yml    38L  0C    0m  CC=0.0    ←0
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
  services/                       CC̄=4.9    ←in:0  →out:0
  │ !! app                        702L  0C   27m  CC=11     ←0
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │
  src/                            CC̄=3.9    ←in:0  →out:0
  │ !! doctor                    1887L  2C   88m  CC=13     ←2
  │ !! mcp_server                1277L  0C   41m  CC=14     ←2
  │ !! scan                      1183L  0C   37m  CC=13     ←3
  │ !! operator_pipeline         1016L  2C   44m  CC=14     ←0
  │ !! autonomous_loop_runner    1008L  1C   48m  CC=10     ←2
  │ !! autonomous                 987L  0C   62m  CC=4      ←4
  │ !! autonomous_cycle           975L  0C   29m  CC=11     ←1
  │ !! plugin_installer           927L  1C   43m  CC=12     ←8
  │ !! context                    822L  0C   31m  CC=12     ←8
  │ !! autonomous_wup             808L  3C   39m  CC=12     ←2
  │ !! ide                        755L  1C   46m  CC=13     ←27
  │ !! decision_trace             677L  1C   24m  CC=11     ←3
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←0
  │ !! autonomous_startup         673L  3C   32m  CC=11     ←4
  │ !! init                       610L  1C   15m  CC=12     ←2
  │ !! dashboard_routes           585L  0C   34m  CC=9      ←2
  │ !! cli_cleaned                564L  0C   41m  CC=14     ←1
  │ !! command_catalog            557L  1C    8m  CC=9      ←8
  │ !! cli_parser                 556L  0C   15m  CC=1      ←0
  │ !! configurator               552L  3C   29m  CC=12     ←6
  │ !! ide_reload                 550L  1C   23m  CC=9      ←2
  │ !! autonomous_cycle_drive_retry   542L  0C   27m  CC=11     ←1
  │ !! os_injector                535L  2C   32m  CC=9      ←2
  │ handlers_drive             496L  0C    8m  CC=14     ←0
  │ install_plugin_cli         485L  0C   19m  CC=10     ←0
  │ autonomous_cycle_chat_activity   478L  0C   11m  CC=12     ←2
  │ scan_phase                 478L  0C   17m  CC=14     ←0
  │ context_render             472L  0C   18m  CC=14     ←6
  │ drive_orchestrator         471L  1C   22m  CC=14     ←0
  │ autonomous_cycle_skip_conditions   466L  0C   21m  CC=14     ←3
  │ install_manager            466L  1C   18m  CC=13     ←3
  │ ide_work                   465L  0C   17m  CC=12     ←4
  │ runner                     463L  0C   14m  CC=9      ←3
  │ shared                     463L  0C   24m  CC=9      ←1
  │ bootstrap                  459L  2C   21m  CC=10     ←3
  │ autonomous_parser          454L  0C    4m  CC=14     ←2
  │ code2llm_discovery         451L  1C   20m  CC=13     ←4
  │ mcp_provision              449L  0C   24m  CC=10     ←5
  │ topology                   425L  1C   18m  CC=9      ←9
  │ !! autonomous_plugin_wait     414L  0C    5m  CC=15     ←0
  │ tasks                      410L  1C   26m  CC=12     ←11
  │ injector                   393L  3C   24m  CC=10     ←1
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ handlers_ack               390L  0C   10m  CC=13     ←1
  │ !! observability_dsl          384L  1C   23m  CC=32     ←5
  │ portal_screencast          383L  1C    7m  CC=10     ←0
  │ ide_doctor_cli             383L  0C   11m  CC=11     ←0
  │ install_checks             382L  1C   15m  CC=12     ←0
  │ post_run_verify            381L  2C   16m  CC=14     ←3
  │ local_service              380L  1C   15m  CC=10     ←1
  │ env                        380L  0C   17m  CC=12     ←3
  │ gc                         371L  2C   12m  CC=11     ←1
  │ autonomous_cycle_orchestrator   357L  0C    7m  CC=12     ←1
  │ autonomous_processes       355L  3C   16m  CC=11     ←2
  │ self_control               351L  2C   18m  CC=12     ←2
  │ autonomous_cycle_chat_activity_tickets   344L  0C    9m  CC=12     ←1
  │ tree                       342L  5C   19m  CC=10     ←4
  │ agents                     335L  1C   16m  CC=14     ←4
  │ dashboard_projects         334L  0C   20m  CC=10     ←2
  │ cli_command                333L  0C   20m  CC=9      ←0
  │ init_host_environment      329L  0C   17m  CC=14     ←1
  │ activity_log               327L  0C   15m  CC=10     ←24
  │ server                     326L  1C   16m  CC=8      ←0
  │ autonomous_runtime         325L  1C   12m  CC=14     ←4
  │ tools                      318L  0C   19m  CC=11     ←3
  │ strategies.json            315L  0C    0m  CC=0.0    ←0
  │ app                        312L  0C   17m  CC=10     ←1
  │ host_setup                 309L  0C   14m  CC=14     ←2
  │ detector                   306L  0C   14m  CC=11     ←8
  │ autonomous_diagnostics     305L  0C    9m  CC=13     ←1
  │ autonomous_operator        304L  0C   18m  CC=3      ←1
  │ autonomous_cycle_chat_activity_analyzer   301L  0C   18m  CC=11     ←1
  │ local_manager_state        292L  4C   21m  CC=14     ←0
  │ wizard.js                  292L  0C   38m  CC=13     ←80
  │ queue_cli_helpers          290L  0C   10m  CC=9      ←1
  │ control_commands           286L  0C   12m  CC=12     ←7
  │ runners                    286L  0C   12m  CC=12     ←2
  │ lifecycle                  285L  1C   13m  CC=10     ←1
  │ autonomous_daemon          282L  0C   10m  CC=10     ←2
  │ !! handlers                   281L  0C   11m  CC=18     ←3
  │ cli_main                   281L  0C    6m  CC=14     ←0
  │ protocol                   279L  2C   14m  CC=12     ←7
  │ autonomous_plugin          278L  0C   19m  CC=12     ←4
  │ wayland_linux              274L  1C   11m  CC=9      ←2
  │ cli_parser                 274L  0C    8m  CC=2      ←0
  │ cli_direct_drive           273L  0C   12m  CC=7      ←0
  │ browser_getdisplay         266L  1C   14m  CC=8      ←2
  │ environment_profile        265L  5C   11m  CC=9      ←4
  │ !! command_scenario           264L  1C    7m  CC=37     ←4
  │ policy                     262L  1C   10m  CC=9      ←3
  │ git_cli                    262L  0C   16m  CC=9      ←0
  │ command_picker             260L  2C    9m  CC=14     ←1
  │ orchestrator               259L  1C    9m  CC=10     ←2
  │ autonomous_auto_pipeline   255L  2C    9m  CC=9      ←0
  │ dashboard_tickets          253L  0C   11m  CC=14     ←1
  │ local_manager_client       252L  2C   15m  CC=7      ←4
  │ client                     252L  1C   10m  CC=10     ←1
  │ decision_engine            251L  4C   10m  CC=11     ←2
  │ environment                250L  3C    6m  CC=14     ←1
  │ capture_mss                248L  1C   12m  CC=14     ←4
  │ dashboard_serve_utils      246L  1C   18m  CC=7      ←3
  │ ide_install                241L  1C    6m  CC=9      ←1
  │ dashboard_serve            240L  1C   10m  CC=6      ←1
  │ cli                        232L  0C   12m  CC=12     ←0
  │ invoke_handlers            232L  1C   18m  CC=5      ←0
  │ obs_websocket              231L  1C   15m  CC=11     ←1
  │ autonomous_onboarding      231L  1C   11m  CC=10     ←0
  │ integrations               228L  1C    2m  CC=4      ←4
  │ base                       226L  7C   10m  CC=2      ←0
  │ autonomous_up              226L  2C    5m  CC=5      ←0
  │ calibrate_cli              225L  0C    7m  CC=9      ←0
  │ handlers_hello             222L  0C    6m  CC=11     ←0
  │ event_store                220L  4C   17m  CC=10     ←3
  │ autonomous_cycle_config    218L  0C    6m  CC=9      ←1
  │ autonomous_drive_retry_policy   216L  0C    8m  CC=13     ←1
  │ ide                        216L  1C    6m  CC=10     ←1
  │ doctor_constants           215L  1C    0m  CC=0.0    ←0
  │ dev_sync                   213L  1C    9m  CC=11     ←0
  │ agent_backends             212L  3C    7m  CC=11     ←3
  │ interface_registry         212L  3C   12m  CC=9      ←7
  │ command_telemetry          210L  1C   11m  CC=13     ←0
  │ library                    207L  0C   19m  CC=9      ←1
  │ injector_backends          207L  0C   11m  CC=5      ←3
  │ autonomous_process_guard   206L  2C    8m  CC=11     ←1
  │ autonomous_checkpoint      205L  0C   11m  CC=9      ←4
  │ gate                       202L  1C    5m  CC=12     ←1
  │ templates                  194L  1C   12m  CC=9      ←1
  │ cli_queue                  192L  0C    4m  CC=12     ←0
  │ dashboard                  191L  0C   11m  CC=5      ←4
  │ handlers_plugin_event      191L  1C    9m  CC=7      ←0
  │ ide_client                 191L  2C   12m  CC=7      ←1
  │ autonomous_plugin_runtime   191L  0C   10m  CC=11     ←1
  │ runtime_insights           190L  0C    6m  CC=9      ←1
  │ server                     190L  1C    8m  CC=9      ←1
  │ models                     190L  2C    6m  CC=8      ←0
  │ redup_integration          189L  0C   11m  CC=3      ←2
  │ cli_task                   189L  0C    5m  CC=11     ←0
  │ openapi                    183L  0C    1m  CC=2      ←1
  │ bridge                     183L  0C    6m  CC=14     ←5
  │ agent_backend_runtime      180L  5C    6m  CC=9      ←0
  │ diagnostics                175L  0C    8m  CC=8      ←2
  │ events                     174L  1C   11m  CC=7      ←1
  │ llm_reflect                173L  1C    5m  CC=8      ←2
  │ cli                        173L  0C    5m  CC=2      ←6
  │ queue_phase                170L  0C    6m  CC=11     ←0
  │ command_catalog_store      169L  1C   13m  CC=10     ←3
  │ chat_history               166L  1C    6m  CC=13     ←2
  │ dashboard_config           164L  1C   13m  CC=10     ←1
  │ application                164L  2C   11m  CC=3      ←0
  │ ticket                     164L  0C    8m  CC=10     ←7
  │ project                    160L  1C   11m  CC=7      ←1
  │ cli                        159L  0C   10m  CC=3      ←0
  │ project_pipeline           158L  0C    5m  CC=11     ←7
  │ audit                      154L  2C    6m  CC=6      ←1
  │ analyzer                   154L  1C   12m  CC=12     ←0
  │ ide_chat                   153L  1C    6m  CC=9      ←0
  │ doctor_cli                 152L  0C    9m  CC=8      ←1
  │ semcod_tools               149L  1C    4m  CC=7      ←5
  │ providers_cli              148L  0C   10m  CC=13     ←1
  │ cli_topology               148L  0C    3m  CC=9      ←0
  │ git_attribution            147L  1C    6m  CC=9      ←1
  │ autonomous_cycle_gate      147L  0C    8m  CC=7      ←2
  │ daemon_cli                 146L  0C    7m  CC=11     ←0
  │ cli_doctor                 143L  0C    6m  CC=11     ←0
  │ x11_linux                  139L  1C    8m  CC=11     ←0
  │ autonomous_cycle_chat_activity_text   138L  0C    6m  CC=12     ←0
  │ vscode_family              137L  1C    4m  CC=8      ←0
  │ local_manager              136L  1C    6m  CC=5      ←1
  │ integration_ledger         135L  0C    4m  CC=5      ←3
  │ loop                       131L  3C    4m  CC=12     ←2
  │ observability_writer       131L  0C    9m  CC=8      ←8
  │ base                       130L  4C    7m  CC=5      ←0
  │ llx                        128L  1C    4m  CC=14     ←3
  │ cli_parser                 125L  0C    4m  CC=7      ←1
  │ scan_render                125L  0C    5m  CC=8      ←1
  │ drive                      125L  0C    2m  CC=11     ←0
  │ config                     123L  1C    6m  CC=7      ←1
  │ run_log                    123L  1C    7m  CC=4      ←5
  │ config                     123L  1C    1m  CC=4      ←0
  │ doctor_plugin_bundle       123L  0C    6m  CC=8      ←0
  │ observability_events       122L  0C   10m  CC=3      ←5
  │ cli_events                 121L  0C    3m  CC=7      ←0
  │ application                120L  2C    4m  CC=12     ←0
  │ prompters                  120L  2C    9m  CC=11     ←0
  │ cli_init                   119L  0C    3m  CC=7      ←0
  │ prompts                    119L  1C    2m  CC=10     ←0
  │ application                119L  2C    6m  CC=5      ←0
  │ portal_capture             118L  1C    2m  CC=8      ←3
  │ ports                      118L  5C    4m  CC=1      ←0
  │ base                       117L  3C   10m  CC=4      ←0
  │ registry                   116L  1C    6m  CC=9      ←3
  │ cli_gate                   116L  0C    2m  CC=5      ←0
  │ heal                       116L  1C    3m  CC=5      ←0
  │ cycle_trace                116L  0C    3m  CC=8      ←1
  │ dashboard_html             115L  0C    3m  CC=4      ←1
  │ loop                       115L  0C    1m  CC=14     ←4
  │ session                    112L  2C    8m  CC=4      ←0
  │ doctor_project_checks      108L  0C    4m  CC=7      ←0
  │ dashboard_state            106L  0C    4m  CC=7      ←3
  │ ide_router                 105L  1C    2m  CC=10     ←5
  │ autonomous_cycle_chat_activity_config   105L  0C    8m  CC=3      ←0
  │ runtime                    104L  0C    5m  CC=2      ←5
  │ dotenv_loader              104L  0C    3m  CC=7      ←2
  │ cycle_finalize             104L  0C    1m  CC=4      ←0
  │ web-app.json               104L  0C    0m  CC=0.0    ←0
  │ systemd_cli                103L  0C    4m  CC=6      ←0
  │ storage                    100L  0C    5m  CC=6      ←2
  │ fallback                   100L  1C    1m  CC=1      ←0
  │ cli_auto                    99L  0C    5m  CC=14     ←1
  │ __init__                    97L  0C    2m  CC=2      ←0
  │ ide_control                 95L  1C    2m  CC=3      ←1
  │ __init__                    95L  2C    5m  CC=3      ←4
  │ __init__                    94L  0C    3m  CC=9      ←0
  │ locking                     94L  0C    5m  CC=5      ←2
  │ config                      94L  1C    3m  CC=4      ←3
  │ plugin_router               93L  3C    5m  CC=6      ←0
  │ cursor                      93L  1C    3m  CC=1      ←0
  │ watch                       93L  0C    6m  CC=9      ←1
  │ application                 92L  2C    4m  CC=5      ←0
  │ cli                         90L  0C    4m  CC=11     ←2
  │ base                        90L  4C    6m  CC=5      ←4
  │ events                      90L  0C    2m  CC=8      ←14
  │ autonomous_resources        90L  0C    1m  CC=4      ←0
  │ openrouter                  89L  1C    2m  CC=5      ←2
  │ codex                       88L  1C    5m  CC=6      ←0
  │ transport                   88L  0C    4m  CC=9      ←2
  │ autoloop_cli                88L  0C    4m  CC=8      ←0
  │ types                       88L  5C    1m  CC=2      ←0
  │ defaults                    88L  0C    2m  CC=1      ←2
  │ agent_cli_helpers           87L  0C    3m  CC=10     ←2
  │ cli_gc                      87L  0C    2m  CC=1      ←0
  │ dashboard                   86L  0C    8m  CC=3      ←1
  │ browser_capture             86L  0C    5m  CC=10     ←1
  │ darwin                      85L  1C    5m  CC=4      ←0
  │ envelope                    85L  1C    4m  CC=3      ←4
  │ cli_agent                   85L  0C    3m  CC=3      ←0
  │ registry                    82L  0C    5m  CC=4      ←1
  │ jetbrains                   82L  1C    0m  CC=0.0    ←0
  │ gc_cli_helpers              81L  0C    5m  CC=12     ←1
  │ cli_scan                    81L  0C    2m  CC=3      ←0
  │ __init__                    80L  0C    0m  CC=0.0    ←0
  │ mesh                        79L  0C    5m  CC=8      ←2
  │ cli_runtime_context         79L  0C    3m  CC=14     ←0
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ cli_trace                   78L  0C    2m  CC=10     ←0
  │ enums                       78L  3C    0m  CC=0.0    ←0
  │ base                        77L  5C    3m  CC=4      ←0
  │ status                      77L  0C    2m  CC=10     ←0
  │ agent                       76L  0C    5m  CC=11     ←1
  │ scan_types                  76L  3C    3m  CC=2      ←0
  │ autonomous_plugin_lifecycle    76L  1C    1m  CC=9      ←1
  │ application                 76L  2C    4m  CC=3      ←0
  │ dashboard_observability     75L  0C    3m  CC=7      ←1
  │ cli                         75L  0C    4m  CC=5      ←0
  │ antigravity                 75L  1C    3m  CC=1      ←0
  │ topology_cli                75L  1C    4m  CC=8      ←1
  │ autonomous_cli_config       74L  0C    4m  CC=5      ←0
  │ application                 74L  2C    4m  CC=3      ←0
  │ vscode                      73L  1C    3m  CC=1      ←0
  │ cli_tools                   73L  0C    2m  CC=7      ←0
  │ cli_strategy                73L  0C    1m  CC=9      ←0
  │ tail_cli                    73L  0C    4m  CC=6      ←0
  │ server                      73L  0C    3m  CC=4      ←1
  │ windsurf                    72L  1C    3m  CC=1      ←0
  │ cli_serve                   72L  0C    2m  CC=1      ←0
  │ shell_evidence              72L  0C    2m  CC=7      ←1
  │ transform                   70L  0C    4m  CC=12     ←2
  │ emitter                     70L  1C    5m  CC=6      ←2
  │ event_log_projection        70L  2C    5m  CC=6      ←0
  │ capture                     69L  1C    4m  CC=2      ←3
  │ __init__                    69L  5C    0m  CC=0.0    ←0
  │ topology_post               68L  0C    1m  CC=14     ←1
  │ ollama                      68L  1C    4m  CC=2      ←0
  │ store_persistence           68L  0C    4m  CC=8      ←1
  │ cli_self                    68L  0C    3m  CC=8      ←0
  │ application                 68L  2C    3m  CC=4      ←0
  │ local_manager               67L  0C    2m  CC=2      ←1
  │ heuristics                  67L  0C    3m  CC=6      ←2
  │ env_config                  65L  0C    3m  CC=1      ←1
  │ cli_bootstrap               65L  0C    2m  CC=5      ←0
  │ wup_testql_compat           64L  0C    4m  CC=5      ←0
  │ __init__                    64L  5C    0m  CC=0.0    ←0
  │ registry                    63L  0C    4m  CC=5      ←5
  │ dashboard_http              63L  1C    6m  CC=4      ←0
  │ zed                         63L  1C    0m  CC=0.0    ←0
  │ doctor_render               62L  0C    3m  CC=8      ←1
  │ cli_agent_backends          61L  0C    1m  CC=8      ←0
  │ screencast_session          60L  0C    5m  CC=7      ←2
  │ store                       60L  0C    4m  CC=6      ←2
  │ dashboard_runtime           59L  0C    4m  CC=5      ←1
  │ vscodium                    59L  1C    3m  CC=1      ←0
  │ env                         58L  0C    7m  CC=5      ←8
  │ client                      58L  1C    7m  CC=6      ←0
  │ client_helpers              57L  0C    2m  CC=4      ←1
  │ protocol                    57L  2C    2m  CC=3      ←2
  │ dashboard_plugin_logs       56L  0C    5m  CC=5      ←0
  │ cli_commands                56L  0C    3m  CC=3      ←1
  │ gpt                         55L  1C    4m  CC=1      ←0
  │ claude                      55L  1C    4m  CC=1      ←0
  │ planfile_ticket_note        55L  0C    2m  CC=5      ←2
  │ library.json                55L  0C    0m  CC=0.0    ←0
  │ ml-research.json            55L  0C    0m  CC=0.0    ←0
  │ cli-tool.json               55L  0C    0m  CC=0.0    ←0
  │ windows                     54L  1C    4m  CC=1      ←0
  │ mss                         54L  1C    4m  CC=8      ←0
  │ batch                       54L  1C    5m  CC=2      ←0
  │ registry                    54L  0C    4m  CC=3      ←2
  │ cli_local_serve             53L  0C    2m  CC=1      ←0
  │ cli_ide_router              53L  0C    1m  CC=3      ←0
  │ scaling                     52L  0C    3m  CC=6      ←5
  │ dashboard_parse             52L  0C    3m  CC=6      ←2
  │ capture_probe               50L  0C    2m  CC=7      ←1
  │ __init__                    50L  0C    0m  CC=0.0    ←0
  │ cli_loop                    49L  0C    1m  CC=7      ←0
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ prompts                     49L  0C    1m  CC=2      ←1
  │ __init__                    48L  5C    0m  CC=0.0    ←0
  │ protocol                    48L  0C    0m  CC=0.0    ←0
  │ __init__                    47L  0C    0m  CC=0.0    ←0
  │ refactor_planfile_handoff    46L  0C    1m  CC=6      ←2
  │ plugin_version              46L  0C    1m  CC=2      ←2
  │ __init__                    46L  3C    0m  CC=0.0    ←0
  │ cli_tools                   45L  1C    5m  CC=3      ←0
  │ verify_phase                45L  0C    1m  CC=5      ←0
  │ portal_screenshot           44L  1C    4m  CC=2      ←0
  │ grim                        44L  1C    5m  CC=4      ←0
  │ socket                      44L  0C    2m  CC=7      ←12
  │ ide_runtime                 44L  0C    2m  CC=5      ←1
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ event_log_query             43L  1C    2m  CC=5      ←0
  │ planfile_handoff            42L  0C    2m  CC=2      ←2
  │ cli_parser                  41L  0C    4m  CC=2      ←1
  │ cli_watch                   41L  0C    1m  CC=2      ←0
  │ registry.json               41L  0C    0m  CC=0.0    ←0
  │ reflection_policy           40L  1C    2m  CC=9      ←1
  │ subprocess_runner           40L  0C    3m  CC=3      ←5
  │ __init__                    40L  0C    0m  CC=0.0    ←0
  │ __init__                    39L  2C    0m  CC=0.0    ←0
  │ bootstrap                   38L  0C    3m  CC=3      ←2
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ codec                       37L  0C    2m  CC=1      ←2
  │ event_bus                   37L  1C    3m  CC=2      ←0
  │ __init__                    37L  2C    0m  CC=0.0    ←0
  │ __init__                    37L  0C    0m  CC=0.0    ←0
  │ local                       36L  0C    2m  CC=6      ←3
  │ state                       36L  1C    0m  CC=0.0    ←0
  │ __init__                    36L  3C    0m  CC=0.0    ←0
  │ planfile_queue              36L  0C    0m  CC=0.0    ←0
  │ cli_refactor_planfile_handoff    35L  0C    1m  CC=1      ←0
  │ __init__                    34L  2C    0m  CC=0.0    ←0
  │ dashboard_context           33L  0C    2m  CC=3      ←1
  │ __init__                    33L  0C    1m  CC=4      ←0
  │ __init__                    33L  4C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    0m  CC=0.0    ←0
  │ registry                    32L  0C    2m  CC=1      ←1
  │ shutdown                    32L  0C    1m  CC=1      ←0
  │ __init__                    32L  1C    0m  CC=0.0    ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ cli_parser                  31L  0C    1m  CC=1      ←1
  │ cli_context                 31L  0C    1m  CC=2      ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ utils                       30L  0C    2m  CC=4      ←3
  │ __init__                    30L  3C    0m  CC=0.0    ←0
  │ __init__                    29L  1C    0m  CC=0.0    ←0
  │ __init__                    29L  2C    0m  CC=0.0    ←0
  │ cli                         27L  0C    1m  CC=5      ←0
  │ __init__                    27L  3C    0m  CC=0.0    ←0
  │ keys                        25L  0C    2m  CC=3      ←5
  │ autonomous_env              25L  0C    1m  CC=1      ←0
  │ __init__                    25L  2C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ daemon_storage              24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ dashboard_topology          22L  0C    2m  CC=1      ←1
  │ __init__                    22L  2C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ paths                       21L  0C    4m  CC=1      ←6
  │ utils                       21L  0C    1m  CC=2      ←2
  │ __init__                    21L  1C    0m  CC=0.0    ←0
  │ __init__                    21L  2C    0m  CC=0.0    ←0
  │ autonomous_cycle_bridge     20L  0C    1m  CC=2      ←0
  │ autonomous_cycle_common     20L  1C    2m  CC=3      ←7
  │ __init__                    20L  1C    0m  CC=0.0    ←0
  │ __init__                    20L  2C    0m  CC=0.0    ←0
  │ domain_event                19L  1C    1m  CC=2      ←0
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ autonomous_diag_markers     16L  0C    1m  CC=1      ←3
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ __init__                    16L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←2
  │ __init__                    14L  1C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    11L  0C    0m  CC=0.0    ←0
  │ injector_errors             10L  1C    0m  CC=0.0    ←0
  │ client                      10L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ injector                     9L  0C    0m  CC=0.0    ←0
  │ os_injector                  9L  0C    0m  CC=0.0    ←0
  │ audit                        9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ cli_ide                      7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     6L  0C    0m  CC=0.0    ←0
  │ __init__                     6L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ cli                          0L  0C   17m  CC=8      ←0
  │
  plugins/                        CC̄=2.8    ←in:0  →out:0  ×DUP
  │ !! extension.ts              3013L  2C  210m  CC=15     ←0  ×DUP
  │ !! extension.ts              2757L  2C  207m  CC=14     ←19  ×DUP
  │ !! extension.ts              2753L  2C  207m  CC=14     ←0  ×DUP
  │ !! extension.ts              2704L  2C  202m  CC=14     ←0  ×DUP
  │ !! extension.ts              2704L  2C  202m  CC=14     ←0  ×DUP
  │ probe-ladder.ts            419L  3C   41m  CC=10     ←1
  │ chat-history-watcher.test.ts   363L  0C   30m  CC=5      ←0
  │ chat-history-watcher.test.ts   355L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←1
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ probe-ladder.test.ts       296L  0C   37m  CC=5      ←0
  │ ack-payload.ts             260L  0C   31m  CC=12     ←18
  │ cursor.test.ts             254L  0C   27m  CC=5      ←1
  │ package.json               199L  0C    0m  CC=0.0    ←0
  │ chat-history-watcher.ts    197L  2C   11m  CC=10     ←0
  │ package.json               194L  0C    0m  CC=0.0    ←0
  │ package.json               190L  0C    0m  CC=0.0    ←0
  │ package.json               189L  0C    0m  CC=0.0    ←0
  │ KoruAutopilotService.kt    186L  1C    6m  CC=0.0    ←0
  │ package.json               174L  0C    0m  CC=0.0    ←0
  │ cursor-bubble-adapter.ts   159L  1C   21m  CC=11     ←0
  │ step-decisions.test.ts     148L  0C   12m  CC=2      ←0
  │ vscode-chat-session-adapter.ts   146L  2C   22m  CC=10     ←0
  │ step-decisions.ts          145L  1C   14m  CC=7      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ dispatch-plan.test.ts      118L  0C   12m  CC=4      ←0
  │ ide-strategy.ts            108L  2C    0m  CC=0.0    ←0
  │ probe-ladder.test.ts        93L  0C   14m  CC=3      ←0
  │ vscodium.ts                 82L  0C   10m  CC=4      ←0
  │ vscode.ts                   81L  0C   11m  CC=7      ←0
  │ probe-ladder.test.ts        77L  0C   10m  CC=2      ←0
  │ ChatInjector.kt             74L  0C    2m  CC=0.0    ←0
  │ probe-ladder.test.ts        70L  0C   10m  CC=2      ←0
  │ socketPath.ts               67L  0C   14m  CC=9      ←0
  │ ide-control-strategy.ts     64L  1C    2m  CC=4      ←0
  │ probe-ladder.test.ts        63L  0C    8m  CC=2      ←0
  │ registry.ts                 63L  0C    7m  CC=6      ←0
  │ socketPath.ts               61L  0C   14m  CC=9      ←0
  │ vscodium.test.ts            60L  0C   11m  CC=3      ←0
  │ command-catalog.test.ts     55L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     55L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     55L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     55L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     55L  0C    9m  CC=2      ←0
  │ ack-payload.test.ts         52L  0C    7m  CC=4      ←0
  │ build.gradle.kts            49L  0C    4m  CC=0.0    ←0
  │ registry.ts                 45L  0C    7m  CC=6      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←1
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ antigravity-fastpath.test.ts    39L  0C    8m  CC=2      ←0
  │ host-click-submit.test.ts    39L  0C    6m  CC=2      ←0
  │ index.ts                    37L  0C    0m  CC=0.0    ←0
  │ host-click-submit.ts        35L  0C    7m  CC=6      ←0
  │ SocketPath.kt               33L  0C    0m  CC=0.0    ←0
  │ chat-history-types.ts       32L  3C    0m  CC=0.0    ←0
  │ chat-history-adapters.ts    31L  0C    1m  CC=2      ←0
  │ chat-history-paths.ts       29L  0C    5m  CC=4      ←0
  │ dispatch-plan.ts            26L  1C    1m  CC=7      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ plugin.xml                  24L  0C    0m  CC=0.0    ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=3      ←0
  │ antigravity-fastpath.ts     20L  0C    2m  CC=3      ←0
  │ unsupported-chat-adapter.ts    19L  1C    2m  CC=1      ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │ KoruAutopilotReconnectAction.kt    10L  1C    0m  CC=0.0    ←0
  │ package.json                10L  0C    0m  CC=0.0    ←0
  │ settings.gradle.kts          8L  0C    2m  CC=0.0    ←0
  │ index.ts                     8L  0C    0m  CC=0.0    ←0
  │ gradle.properties            6L  0C    0m  CC=0.0    ←0
  │ antigravity.ts               0L  0C    8m  CC=2      ←0
  │ cursor.ts                    0L  0C   13m  CC=5      ←0
  │ windsurf.ts                  0L  0C    8m  CC=6      ←0
  │
  scripts/                        CC̄=2.3    ←in:554  →out:1
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ scaffold-ide-plugin        298L  0C    7m  CC=7      ←0
  │ write-ide-plugin-tests     261L  0C    3m  CC=3      ←0
  │ planfile-sync-todo         260L  0C   12m  CC=14     ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ sync-plugin-version        149L  0C    4m  CC=7      ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←96
  │ sync-vscode-plugin-version   125L  0C    6m  CC=2      ←0
  │ koru-queue-diagnose.sh     124L  0C    0m  CC=0.0    ←0
  │ koru-soak-stop.sh          123L  0C    5m  CC=0.0    ←0
  │ koru-soak-status.sh        100L  0C    6m  CC=0.0    ←0
  │ koru-semcod-gates.sh        99L  0C    2m  CC=0.0    ←0
  │ sync-plugin-shared          97L  0C    2m  CC=7      ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ koru-pytest.sh              93L  0C    0m  CC=0.0    ←0
  │ docker-ide-matrix.sh        92L  0C    2m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←0
  │ docker-ide-matrix-entrypoint.sh    75L  0C    1m  CC=0.0    ←0
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │ koru-soak-start.sh          39L  0C    1m  CC=0.0    ←0
  │ activate-koru-dev.sh        18L  0C    0m  CC=0.0    ←0
  │ koru-from-repo.sh           10L  0C    0m  CC=0.0    ←0
  │
  docker/                         CC̄=2.2    ←in:0  →out:0
  │ smoke                      141L  0C    8m  CC=4      ←0
  │ Dockerfile                  61L  0C    0m  CC=0.0    ←0
  │ run.sh                      58L  0C    0m  CC=0.0    ←0
  │ entrypoint-x11.sh           35L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ !! planfile.yaml             1357L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               922L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  518L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             198L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ koru.yaml                  129L  0C    0m  CC=0.0    ←0
  │ wup-shell-only.yaml        110L  0C    0m  CC=0.0    ←0
  │ wup.yaml                   110L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ project.sh                  59L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
  │ Makefile                    36L  0C    0m  CC=0.0    ←0
  │ package.json                24L  0C    0m  CC=0.0    ←0
  │ .pretest.yml                17L  0C    0m  CC=0.0    ←0
  │ output.txt                   3L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │ coverage.json                1L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
  │
  schemas/                        CC̄=0.0    ←in:0  →out:0
  │ koru-stdio-event.schema.json    16L  0C    0m  CC=0.0    ←0
  │
  docs/                           CC̄=0.0    ←in:0  →out:0
  │ ide-command-api-map.yaml   425L  0C    0m  CC=0.0    ←0
  │ ai-tool-registry-2026.yaml   290L  0C    0m  CC=0.0    ←0
  │ koru-interface-registry.yaml   270L  0C    0m  CC=0.0    ←0
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
  │ pipeline-design.md           0L  0C    0m  CC=0.0    ←0
  │
  redeploy/                       CC̄=0.0    ←in:0  →out:0
  │ manifest.yaml              125L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ cli-smoke.testql.toon.yaml    44L  0C    0m  CC=0.0    ←0
  │ generated-cli-tests.testql.toon.yaml    19L  0C    0m  CC=0.0    ←0
  │ cli-koru-live.testql.toon.yaml    16L  0C    0m  CC=0.0    ←0
  │ cli-koru.testql.toon.yaml    15L  0C    0m  CC=0.0    ←0
  │ cli-koru_api.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_dsl.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_wup_testql.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │
  testql-testing/                 CC̄=0.0    ←in:0  →out:0
  │ realtime-health.testql.toon.yaml    11L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     docs/pipeline-design.md                   0L
     plugins/koru-autopilot-vscode/src/ides/antigravity.ts  0L
     plugins/koru-autopilot-vscode/src/ides/cursor.ts  0L
     plugins/koru-autopilot-vscode/src/ides/windsurf.ts  0L
     src/koru/cli.py                           0L

COUPLING:
                                                                src.koru                             scripts                         src.koruide                         src.koruapi                                koru                      src.koruvision                     src.koruobserve       plugins.koru-autopilot-shared                        src.korumesh       plugins.koru-autopilot-vscode                            examples  plugins.koru-autopilot-antigravity                         src.korudsl                          src.koruos                      docker.capture
                            src.koru                                  ──                                 421                                 137                                   8                                  59                                  16                                  10                                   7                                  ←2                                  18                                                                                                           3                                   6                                      hub
                             scripts                                   1                                  ──                                 ←27                                 ←17                                 ←35                                 ←12                                 ←22                                                                      ←7                                                                     ←12                                                                                                                                              ←1  hub
                         src.koruide                                  24                                  27                                  ──                                   2                                   9                                                                                                           8                                                                       1                                                                      10                                                                                                              hub
                         src.koruapi                                  77                                  17                                  24                                  ──                                  10                                                                                                          11                                   3                                   2                                                                                                           4                                                                          hub
                                koru                                   6                                  35                                  ←9                                 ←10                                  ──                                                                                                           1                                                                                                                                                                                                                                                              hub
                      src.koruvision                                   5                                  12                                                                                                                                              ──                                   1                                   1                                   8                                   1                                                                                                                                                                                  ←4  hub
                     src.koruobserve                                   8                                  22                                                                                                                                               7                                  ──                                                                       1                                                                                                                                                                                                                      ←1  hub
       plugins.koru-autopilot-shared                                  ←7                                                                      ←8                                 ←11                                  ←1                                  ←1                                                                      ──                                  ←1                                                                                                                                              ←1                                  ←1                                      hub
                        src.korumesh                                   2                                   7                                                                      ←3                                                                       2                                   1                                   1                                  ──                                   1                                                                                                                                                                                      hub
       plugins.koru-autopilot-vscode                                 ←18                                                                      ←1                                  ←2                                                                      ←1                                                                                                          ←1                                  ──                                                                                                                                                                                      hub
                            examples                                                                      12                                                                                                                                                                                                                                                                                                                                  ──                                                                                                                                                  !! fan-out
  plugins.koru-autopilot-antigravity                                                                                                         ←10                                                                                                                                                                                                                                                                                                                                  ──                                                                                                              hub
                         src.korudsl                                  ←3                                                                                                          ←4                                                                                                                                               1                                                                                                                                                                                  ──                                                                          hub
                          src.koruos                                   1                                                                                                                                                                                                                                                           1                                                                                                                                                                                                                      ──                                      hub
                      docker.capture                                                                       1                                                                                                                                               4                                   1                                                                                                                                                                                                                                                                                              ──
  CYCLES: none
  HUB: src.koruapi/ (fan-in=10)
  HUB: koru/ (fan-in=78)
  HUB: src.korudsl/ (fan-in=7)
  HUB: src.koruobserve/ (fan-in=13)
  HUB: plugins.koru-autopilot-antigravity/ (fan-in=10)
  HUB: src.koru/ (fan-in=125)
  HUB: src.koruos/ (fan-in=6)
  HUB: src.korumesh/ (fan-in=12)
  HUB: plugins.koru-autopilot-shared/ (fan-in=32)
  HUB: plugins.koru-autopilot-vscode/ (fan-in=25)
  HUB: src.koruvision/ (fan-in=29)
  HUB: scripts/ (fan-in=554)
  HUB: src.koruide/ (fan-in=161)
  SMELL: src.koruapi/ fan-out=148 → split needed
  SMELL: koru/ fan-out=43 → split needed
  SMELL: src.koruobserve/ fan-out=38 → split needed
  SMELL: src.koru/ fan-out=688 → split needed
  SMELL: src.korumesh/ fan-out=14 → split needed
  SMELL: src.koruvision/ fan-out=28 → split needed
  SMELL: examples/ fan-out=12 → split needed
  SMELL: src.koruide/ fan-out=81 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 114 groups | 428f 73196L | 2026-05-25

SUMMARY:
  files_scanned: 428
  total_lines:   73196
  dup_groups:    114
  dup_fragments: 280
  saved_lines:   1403
  scan_ms:       4164

HOTSPOTS[7] (files with most duplication):
  src/koru/cli_cleaned.py  dup=373L  groups=31  frags=36  (0.5%)
  src/koru/cli_task.py  dup=163L  groups=5  frags=5  (0.2%)
  src/koru/cli.py  dup=101L  groups=8  frags=9  (0.1%)
  src/koru/autonomy/phases/scan_phase.py  dup=80L  groups=4  frags=8  (0.1%)
  src/koru/ide_adapters/ide_reload.py  dup=68L  groups=4  frags=6  (0.1%)
  src/koru/autopilot/cli_parser.py  dup=66L  groups=1  frags=2  (0.1%)
  src/koru/cli_agent.py  dup=65L  groups=2  frags=2  (0.1%)

DUPLICATES[114] (ranked by impact):
  [3116e8f45fd387a5] ! STRU  agent_backends_main  L=57 N=2 saved=57 sim=1.00
      src/koru/cli_agent_backends.py:5-61  (agent_backends_main)
      src/koru/cli_cleaned.py:311-344  (_agent_backends_main)
  [239d5ce19c57d14b] ! STRU  _bootstrap_main  L=52 N=2 saved=52 sim=1.00
      src/koru/cli_bootstrap.py:12-63  (_bootstrap_main)
      src/koru/cli_cleaned.py:472-490  (_bootstrap_main)
  [10c17ef3fe2abcf5] ! STRU  _build_agent_parser  L=49 N=2 saved=49 sim=1.00
      src/koru/cli_agent.py:18-66  (_build_agent_parser)
      src/koru/cli_cleaned.py:163-175  (_build_agent_parser)
  [077cfa61a2943c36] ! STRU  _dsl_main  L=4 N=10 saved=36 sim=1.00
      src/koru/cli.py:57-60  (_dsl_main)
      src/koru/cli.py:63-66  (_api_main)
      src/koru/cli_cleaned.py:238-240  (_serve_main)
      src/koru/cli_cleaned.py:242-244  (_local_serve_main)
      src/koru/cli_cleaned.py:307-309  (_mcp_serve_main)
      src/koru/cli_cleaned.py:346-348  (_init_ide_main)
      src/koru/cli_cleaned.py:378-380  (_dsl_main)
      src/koru/cli_cleaned.py:382-384  (_api_main)
      src/koru/cli_local_serve.py:48-51  (_local_serve_main)
      src/koru/cli_serve.py:67-70  (_serve_main)
  [cd14704af11e3785] ! STRU  emit_intent  L=6 N=7 saved=36 sim=1.00
      src/koru/observability_events.py:41-46  (emit_intent)
      src/koru/observability_events.py:49-54  (emit_decision)
      src/koru/observability_events.py:57-62  (emit_action)
      src/koru/observability_events.py:65-70  (emit_phase)
      src/koru/observability_events.py:73-78  (emit_verify)
      src/koru/observability_events.py:95-100  (emit_blocker)
      src/koru/observability_events.py:103-108  (emit_next)
  [cd4cfd51cca75491] ! STRU  _add_calibrate_parser  L=35 N=2 saved=35 sim=1.00
      src/koru/autopilot/cli_parser.py:178-212  (_add_calibrate_parser)
      src/koru/autopilot/cli_parser.py:215-245  (_add_session_start_parser)
  [4a39ec7a354e028b] ! STRU  _run  L=8 N=5 saved=32 sim=1.00
      src/koru/ide_adapters/ide_reload.py:116-123  (_run)
      src/koruide/plugin_installer.py:428-435  (_run)
      src/koruos/strategies/darwin.py:25-32  (_run)
      src/koruos/strategies/wayland_linux.py:40-47  (_run)
      src/koruos/strategies/x11_linux.py:25-32  (_run)
  [42883f38a75056c9]   STRU  _warn_autopilot_focus_retry  L=15 N=3 saved=30 sim=1.00
      src/koru/autonomous_drive_retry_policy.py:37-51  (_warn_autopilot_focus_retry)
      src/koru/autonomous_drive_retry_policy.py:73-87  (_warn_autopilot_plugin_retry)
      src/koru/autonomous_drive_retry_policy.py:90-104  (_warn_autopilot_submit_retry)
  [400f9f906a729d1a]   STRU  provision_cursor  L=15 N=3 saved=30 sim=1.00
      src/koru/mcp_provision.py:205-219  (provision_cursor)
      src/koru/mcp_provision.py:222-236  (provision_vscode)
      src/koru/mcp_provision.py:246-260  (provision_zed)
  [1b78a8d8acdf8667]   STRU  reuse_window_reload_enabled  L=14 N=3 saved=28 sim=1.00
      src/koru/ide_adapters/ide_reload.py:85-98  (reuse_window_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:101-113  (new_window_reload_enabled)
      src/koruide/command_catalog_store.py:15-18  (command_catalog_enabled)
  [d49761de09617ba4]   EXAC  _finalise_ticket  L=25 N=2 saved=25 sim=1.00
      src/koru/wizard/cli.py:66-90  (_finalise_ticket)
      src/koru/wizard/orchestrator.py:167-191  (_finalise_ticket)
  [1d7c20b439cfc40f]   STRU  _koru_package_version  L=5 N=6 saved=25 sim=1.00
      src/koru/agents.py:82-86  (_koru_package_version)
      src/koru/autonomous_startup.py:36-40  (koru_distribution_version)
      src/koru/cli_cleaned.py:61-65  (_cli_version)
      src/koru/cli_parser.py:17-21  (_cli_version)
      src/koruapi/cli.py:61-65  (_cli_version)
      src/korudsl/cli.py:41-45  (_cli_version)
  [38c3640a1bca3fe6]   STRU  _plugin_package_version  L=7 N=4 saved=21 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:58-64  (_plugin_package_version)
      src/koru/autopilot/install_plugin_cli.py:67-73  (_plugin_package_name)
      src/koruide/plugin_installer.py:165-171  (_plugin_package_version)
      src/koruide/plugin_installer.py:174-180  (_plugin_package_name)
  [dc9dabf29359a004]   STRU  _maybe_reexec_for_project_venv  L=21 N=2 saved=21 sim=1.00
      src/koru/cli.py:209-229  (_maybe_reexec_for_project_venv)
      src/koru/cli_cleaned.py:504-522  (_maybe_reexec_for_project_venv)
  [d8b6166dd12467a7]   EXAC  _stdio_info  L=5 N=5 saved=20 sim=1.00
      src/koru/autonomous.py:168-172  (_stdio_info)
      src/koru/autonomous_checkpoint.py:16-19  (_stdio_info)
      src/koru/autonomous_cycle.py:69-72  (_stdio_info)
      src/koru/autonomous_daemon.py:26-30  (_stdio_info)
      src/koru/autonomous_processes.py:219-223  (_stdio_info)
  [9f01551219734789]   STRU  assess_drive_failure  L=20 N=2 saved=20 sim=1.00
      src/korullm/strategies/codex.py:50-69  (assess_drive_failure)
      src/korullm/strategies/ollama.py:37-56  (assess_drive_failure)
  [2d7b9210c1b65241]   STRU  activity_enabled  L=3 N=7 saved=18 sim=1.00
      src/koru/activity_log.py:16-18  (activity_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:71-73  (llm_needs_input_ticket_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:86-88  (llm_needs_input_heuristic_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:91-93  (chat_intake_ticket_enabled)
      src/koru/autonomy/operator_pipeline.py:285-287  (_operator_autostart_server_enabled)
      src/koru/ide_adapters/ide_reload.py:80-82  (auto_reload_enabled)
      src/koruide/plugin_installer.py:438-440  (_env_reassert_extension_install)
  [e29ad3fb5eb111af]   STRU  _is_topology_enabled  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous.py:344-352  (_is_topology_enabled)
      src/koru/autonomous_cycle_skip_conditions.py:25-33  (_is_topology_enabled)
      src/koru/autonomy/phases/utils.py:11-19  (is_topology_enabled)
  [fa6206f15e06c491]   STRU  current_head  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous_checkpoint.py:28-36  (current_head)
      src/koru/autonomous_cycle.py:118-126  (_current_head)
      src/koru/autonomy/phases/utils.py:22-30  (current_head)
  [fba62c0a0f651c53]   STRU  _run_queue_loop  L=18 N=2 saved=18 sim=1.00
      src/koru/autonomous_cycle.py:370-387  (_run_queue_loop)
      src/koru/autonomy/phases/queue_phase.py:51-68  (run_queue_loop)
  [7212aaa3f9adc25b]   STRU  _is_bare_invocation  L=17 N=2 saved=17 sim=1.00
      src/koru/cli.py:32-48  (_is_bare_invocation)
      src/koru/cli_cleaned.py:258-265  (_is_bare_invocation)
  [1fa7be9b2059ed27]   STRU  _load_tool_scaffold  L=17 N=2 saved=17 sim=1.00
      src/koru/cli_cleaned.py:177-193  (_load_tool_scaffold)
      src/koru/cli_task.py:77-100  (_load_tool_scaffold)
  [2523ecfe7a640e25]   STRU  ide_router_main  L=17 N=2 saved=17 sim=1.00
      src/koru/cli_cleaned.py:360-376  (ide_router_main)
      src/koru/cli_ide_router.py:17-51  (ide_router_main)
  [646aa60d2468b762]   STRU  _post_workers_register  L=17 N=2 saved=17 sim=1.00
      src/koru/local_service.py:225-241  (_post_workers_register)
      src/koru/local_service.py:244-260  (_post_worker_heartbeat)
  [54051ebae1746d54]   STRU  _agent_main  L=16 N=2 saved=16 sim=1.00
      src/koru/cli_agent.py:69-84  (_agent_main)
      src/koru/cli_cleaned.py:246-256  (_agent_main)
  [4c788efcc3404bcc]   STRU  _project_cli_reexec_argv  L=15 N=2 saved=15 sim=1.00
      src/koru/cli.py:86-100  (_project_cli_reexec_argv)
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
  [d4682f76b89685c4]   STRU  reload_via_reopen_workspace  L=15 N=2 saved=15 sim=1.00
      src/koru/ide_adapters/ide_reload.py:299-313  (reload_via_reopen_workspace)
      src/koru/ide_adapters/ide_reload.py:316-330  (reload_via_new_window)
  [3256d62f5fba7da7]   STRU  detection  L=5 N=4 saved=15 sim=1.00
      src/koruide/ides/antigravity.py:35-39  (detection)
      src/koruide/ides/cursor.py:50-54  (detection)
      src/koruide/ides/windsurf.py:35-39  (detection)
      src/koruide/ides/zed.py:32-36  (detection)
  [14cf32dfcbf83f08]   STRU  update_plugin_version_source  L=14 N=2 saved=14 sim=1.00
      scripts/sync-vscode-plugin-version.py:43-56  (update_plugin_version_source)
      scripts/sync-vscode-plugin-version.py:59-68  (update_package_json)
  [fa0cda14f71070c0]   STRU  _should_skip_repeated_create_failed_scan  L=14 N=2 saved=14 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:156-169  (_should_skip_repeated_create_failed_scan)
      src/koru/autonomy/phases/scan_phase.py:172-183  (_should_skip_repeated_duplicate_scan)
  [d86ec1c988a8a137]   STRU  _action_install_plugin  L=7 N=3 saved=14 sim=1.00
      src/koru/autopilot/cli_command.py:222-228  (_action_install_plugin)
      src/koru/autopilot/cli_command.py:231-237  (_action_install_plugin_jetbrains)
      src/koru/autopilot/cli_command.py:298-304  (_action_install_unit)
  [7a47c943e98a3943]   STRU  _peek_project_from_argv  L=7 N=3 saved=14 sim=1.00
      src/koru/cli.py:69-75  (_peek_project_from_argv)
      src/koru/cli_auto.py:13-19  (_peek_project_from_argv)
      src/koru/cli_cleaned.py:386-392  (_peek_project_from_argv)
  [c9dd6c5a9bf91266]   STRU  _maybe_print_project_venv_hint  L=14 N=2 saved=14 sim=1.00
      src/koru/cli.py:103-116  (_maybe_print_project_venv_hint)
      src/koru/cli_cleaned.py:415-425  (_maybe_print_project_venv_hint)
  [5dfaaa92d6a7d057]   STRU  _tools_main  L=14 N=2 saved=14 sim=1.00
      src/koru/cli_cleaned.py:113-126  (_tools_main)
      src/koru/cli_tools.py:41-71  (_tools_main)
  [c128cb85e01d8566]   STRU  _runtime_context_main  L=14 N=2 saved=14 sim=1.00
      src/koru/cli_cleaned.py:287-300  (_runtime_context_main)
      src/koru/cli_runtime_context.py:60-77  (_runtime_context_main)
  [2252dd4ae417456e]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:302-314  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:131-143  (_parse_iso_datetime)
  [f14ef8329a787fe8]   STRU  _remember_scan_create_failed_state  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:126-138  (_remember_scan_create_failed_state)
      src/koru/autonomy/phases/scan_phase.py:141-153  (_remember_scan_duplicate_state)
  [5ddec50ead9632f9]   STRU  _should_suggest_wizard  L=13 N=2 saved=13 sim=1.00
      src/koru/cli.py:119-131  (_should_suggest_wizard)
      src/koru/cli_cleaned.py:427-439  (_should_suggest_wizard)
  [6a88d9e54db032d3]   STRU  _render_runtime_context_text  L=13 N=2 saved=13 sim=1.00
      src/koru/cli_cleaned.py:273-285  (_render_runtime_context_text)
      src/koru/cli_runtime_context.py:36-57  (_render_runtime_context_text)
  [ad3918f482428329]   EXAC  _path_is_relative_to  L=6 N=3 saved=12 sim=1.00
      src/koru/autonomous_runtime.py:79-84  (_path_is_relative_to)
      src/koru/cli.py:78-83  (_path_is_relative_to)
      src/koru/cli_cleaned.py:394-399  (_path_is_relative_to)
  [7917af2f030ce975]   EXAC  assess_drive_failure  L=12 N=2 saved=12 sim=1.00
      src/korullm/strategies/claude.py:32-43  (assess_drive_failure)
      src/korullm/strategies/gpt.py:32-43  (assess_drive_failure)
  [caee51cd0b4a6207]   EXAC  list_monitors  L=4 N=4 saved=12 sim=1.00
      src/koruvision/providers/cli_tools.py:26-29  (list_monitors)
      src/koruvision/providers/grim.py:21-24  (list_monitors)
      src/koruvision/providers/portal_screencast.py:296-299  (list_monitors)
      src/koruvision/providers/portal_screenshot.py:26-29  (list_monitors)
  [07394d97ab843be1]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:9-21  (resolve_xdg_path)
  [cfa0e91c669b55c5]   STRU  _build_local_serve_parser  L=6 N=3 saved=12 sim=1.00
      src/koru/cli_cleaned.py:156-161  (_build_local_serve_parser)
      src/koru/cli_local_serve.py:17-45  (_build_local_serve_parser)
      src/koruapi/local.py:11-19  (build_local_parser)
  [40a7bc5fef2589e9]   STRU  _handle_mcp_list_tickets  L=6 N=3 saved=12 sim=1.00
      src/koruapi/invoke_handlers.py:191-196  (_handle_mcp_list_tickets)
      src/koruapi/invoke_handlers.py:199-202  (_handle_mcp_run_ticket)
      src/koruapi/invoke_handlers.py:205-210  (_handle_mcp_quality_gates)
  [d4d1a15bc8e8affa]   STRU  message_received  L=12 N=2 saved=12 sim=1.00
      src/koruide/protocol.py:230-241  (message_received)
      src/koruide/protocol.py:244-255  (status_error)
  [3d80b11159524d7e]   STRU  idle_marker_patterns  L=6 N=3 saved=12 sim=1.00
      src/korullm/strategies/claude.py:45-50  (idle_marker_patterns)
      src/korullm/strategies/gpt.py:45-50  (idle_marker_patterns)
      src/korullm/strategies/ollama.py:58-63  (idle_marker_patterns)
  [d26ceaa1a1fc37a6]   EXAC  _trace_event_matches  L=11 N=2 saved=11 sim=1.00
      src/koruapi/dashboard_observability.py:49-59  (_trace_event_matches)
      src/koruobserve/cli.py:179-189  (_trace_event_matches)
  [364c743e79262b8a]   STRU  _ensure_trusted_publisher_for_plugin  L=11 N=2 saved=11 sim=1.00
      src/koru/autonomous_operator.py:44-54  (_ensure_trusted_publisher_for_plugin)
      src/koru/autonomous_operator.py:105-115  (_emit_reload_required_lines)
  [b79fb4d314048ea0]   STRU  _build_serve_parser  L=11 N=2 saved=11 sim=1.00
      src/koru/cli_cleaned.py:144-154  (_build_serve_parser)
      src/koru/cli_serve.py:17-64  (_build_serve_parser)
  [881c2887af3e09d4]   STRU  _command_loop_main  L=11 N=2 saved=11 sim=1.00
      src/koru/cli_cleaned.py:492-502  (_command_loop_main)
      src/koru/cli_loop.py:12-49  (command_loop_main)
  [f04a2ae34c96bea7]   STRU  _event_to_record  L=11 N=2 saved=11 sim=1.00
      src/koru/cqrs/event_store.py:52-62  (_event_to_record)
      src/koruapi/dashboard_observability.py:62-72  (_stored_event_payload)
  [33eb8357d6e60c1c]   STRU  _versioned_plugin_vsix_candidates  L=10 N=2 saved=10 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:76-85  (_versioned_plugin_vsix_candidates)
      src/koruide/plugin_installer.py:183-192  (_versioned_vsix_candidates)
  [c8e2ac269d01941f]   STRU  _print_task_result  L=10 N=2 saved=10 sim=1.00
      src/koru/cli_cleaned.py:211-220  (_print_task_result)
      src/koru/cli_task.py:131-152  (_print_task_result)
  [db3e3e3ad621b70e]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:116-125  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve_utils.py:146-155  (read_serve_endpoint)
  [2a0193a0215ed99b]   STRU  extension_id_for_ide  L=10 N=2 saved=10 sim=1.00
      src/koruide/plugin_installer.py:67-76  (extension_id_for_ide)
      src/koruide/plugin_version.py:30-39  (expected_plugin_version_for_ide)
  [d9985d8bb1d9ca01]   EXAC  _focus_via_wmctrl  L=9 N=2 saved=9 sim=1.00
      src/koruos/strategies/wayland_linux.py:213-221  (_focus_via_wmctrl)
      src/koruos/strategies/x11_linux.py:117-125  (_focus_via_wmctrl)
  [5d74ce338549bb3e]   STRU  _default_runner  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomy/code2llm_discovery.py:85-93  (_default_runner)
      src/koru/self_control.py:72-80  (_run)
  [b6e9d359e1d4a0b7]   STRU  _action_drive  L=9 N=2 saved=9 sim=1.00
      src/koru/autopilot/cli_command.py:155-163  (_action_drive)
      src/koru/autopilot/cli_command.py:166-174  (_action_status)
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
  [607d78080ec7cca2]   STRU  get_plugin_version_from_source  L=8 N=2 saved=8 sim=1.00
      scripts/sync-vscode-plugin-version.py:23-30  (get_plugin_version_from_source)
      scripts/sync-vscode-plugin-version.py:33-40  (get_plugin_version_from_package)
  [d16cf5813adee1a1]   STRU  llm_reflection_summary_max_age_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomous_cycle_chat_activity_config.py:61-68  (llm_reflection_summary_max_age_seconds)
      src/koruide/daemon/handlers.py:93-100  (_plugin_rejection_log_interval_seconds)
  [5cbff64882e75a4f]   STRU  _create_failed_scan_cooldown_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:106-113  (_create_failed_scan_cooldown_seconds)
      src/koru/autonomy/phases/scan_phase.py:116-123  (_duplicate_only_scan_cooldown_seconds)
  [276bf4ee1b1c66e1]   STRU  _build_tools_parser  L=8 N=2 saved=8 sim=1.00
      src/koru/cli_cleaned.py:104-111  (_build_tools_parser)
      src/koru/cli_tools.py:17-38  (_build_tools_parser)
  [940e90e95c5d69b3]   STRU  _check_git_commit_policy  L=4 N=3 saved=8 sim=1.00
      src/koru/policy.py:194-197  (_check_git_commit_policy)
      src/koru/policy.py:200-203  (_check_git_push_policy)
      src/koru/policy.py:226-229  (_check_git_tag_policy)
  [abf90bbbadf601ec]   STRU  as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:153-159  (as_managed)
      src/koru/autonomous_processes.py:210-216  (_as_managed)
  [8e12ae22db3cad29]   STRU  confirm_replace_existing  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:200-206  (confirm_replace_existing)
      src/koru/autonomous_processes.py:270-276  (_confirm_replace_existing)
  [d84b14f17a72b9af]   STRU  _context_main  L=7 N=2 saved=7 sim=1.00
      src/koru/cli_cleaned.py:464-470  (_context_main)
      src/koru/cli_context.py:18-29  (_context_main)
  [1e804b3bf8580106]   STRU  cmd_providers_list  L=7 N=2 saved=7 sim=1.00
      src/koruobserve/providers_cli.py:117-123  (cmd_providers_list)
      src/koruobserve/providers_cli.py:142-148  (cmd_providers_reset)
  [86be90b88ecc7bec]   EXAC  all_events  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:120-125  (all_events)
      src/koru/cqrs/event_store.py:198-203  (all_events)
  [d5e44a983e3d6ecf]   EXAC  events_for_aggregate  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:127-132  (events_for_aggregate)
      src/koru/cqrs/event_store.py:205-210  (events_for_aggregate)
  [b6cb8ad5c2327f7d]   EXAC  plugin  L=6 N=2 saved=6 sim=1.00
      src/koruide/ides/antigravity.py:59-64  (plugin)
      src/koruide/ides/windsurf.py:56-61  (plugin)
  [9b7967c4c573e5f1]   STRU  process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous_process_guard.py:38-43  (process_cwd)
      src/koru/autonomous_processes.py:52-57  (_process_cwd)
  [0329c1421c67edc8]   STRU  _scan_result_is_create_failed_only  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:77-82  (_scan_result_is_create_failed_only)
      src/koru/autonomy/phases/scan_phase.py:85-90  (_scan_result_is_duplicate_only)
  [b51c404804ad37d1]   STRU  _previous_serve_config  L=3 N=3 saved=6 sim=1.00
      src/koru/configurator.py:267-269  (_previous_serve_config)
      src/koru/tasks.py:176-178  (_source_context)
      src/koruapi/dashboard_config.py:67-69  (_saved_serve_config)
  [c7374d52504d8e71]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:364-369  (set_component_enabled)
      src/koru/topology.py:372-377  (set_pipeline_enabled)
  [2e8d19beee2fb970]   STRU  keyboard  L=6 N=2 saved=6 sim=1.00
      src/koruide/ides/jetbrains.py:72-77  (keyboard)
      src/koruide/ides/zed.py:53-58  (keyboard)
  [c66988d54f59cb9c]   STRU  ydotool_enter_keycode  L=6 N=2 saved=6 sim=1.00
      src/koruide/injector_backends.py:14-19  (ydotool_enter_keycode)
      src/koruide/injector_backends.py:32-37  (ydotool_ctrl_keycode)
  [cede1a8630b48984]   STRU  os_injector_env_disabled  L=3 N=3 saved=6 sim=1.00
      src/koruide/os_injector.py:63-65  (os_injector_env_disabled)
      src/koruide/os_injector.py:68-70  (os_injector_env_forced)
      src/koruide/os_injector.py:73-75  (dry_run_from_env)
  [c459cda75c879909]   EXAC  png_dimensions  L=5 N=2 saved=5 sim=1.00
      src/koruvision/capture_mss.py:48-52  (png_dimensions)
      src/koruvision/providers/base.py:54-58  (png_dimensions)
  [965bd49cbae99ad0]   STRU  _current_koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous_daemon.py:33-37  (_current_koru_version)
      src/koruide/daemon/protocol.py:15-19  (_daemon_package_version)
  [f5678f096384626f]   STRU  _package_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autopilot/install_manager.py:128-132  (_package_version)
      src/koru/self_control.py:92-96  (_installed_version)
  [73cd2b2ecccd25b9]   STRU  _command_value  L=5 N=2 saved=5 sim=1.00
      src/koru/cli_cleaned.py:55-59  (_command_value)
      src/koru/cli_parser.py:10-14  (_command_value)
  [39b742eeea969c7e]   STRU  _build_runtime_context_parser  L=5 N=2 saved=5 sim=1.00
      src/koru/cli_cleaned.py:267-271  (_build_runtime_context_parser)
      src/koru/cli_runtime_context.py:17-33  (_build_runtime_context_parser)
  [2308ba5a8b7cf169]   STRU  runtime_for_project  L=5 N=2 saved=5 sim=1.00
      src/koru/cqrs/__init__.py:61-65  (runtime_for_project)
      src/koru/cqrs/__init__.py:68-76  (runtime_for_storage_dir)
  [dbf8a129ca3f33fb]   STRU  _koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/local_manager_client.py:23-27  (_koru_version)
      src/koru/local_manager_state.py:20-24  (koru_version)
  [e381e420e278e548]   STRU  planfile_dir  L=5 N=2 saved=5 sim=1.00
      src/koru/runtime.py:42-46  (planfile_dir)
      src/koruapi/dashboard_serve_utils.py:158-162  (_build_handler_for)
  [c4200e7110d9ebe1]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [d02f7c25f14027e0]   STRU  terminal  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/antigravity.py:42-46  (terminal)
      src/koruide/ides/windsurf.py:42-46  (terminal)
  [33a247180b684a48]   STRU  aliases  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/vscode.py:55-59  (aliases)
      src/koruide/ides/vscodium.py:41-45  (aliases)
  [03f2881011656d1f]   EXAC  _cycle_attr  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_cycle_chat_activity.py:56-59  (_cycle_attr)
      src/koru/autonomous_cycle_drive_retry.py:75-78  (_cycle_attr)
  [8c85b68869749734]   STRU  status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_checkpoint.py:192-195  (status_in_skip_list)
      src/koru/autonomous_cycle_common.py:17-20  (_status_in_skip_list)
  [6ab181429cc7b1d7]   STRU  _build_queue_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_cycle.py:364-367  (_build_queue_command)
      src/koru/autonomy/phases/queue_phase.py:45-48  (build_queue_command)
  [11e58559cb0f1b01]   STRU  _looks_like_autonomous_up_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_processes.py:84-87  (_looks_like_autonomous_up_command)
      src/koruobserve/providers_cli.py:10-13  (screencast_session_path)
  [db8d6ff4a9df70dc]   STRU  _init_ci_main  L=4 N=2 saved=4 sim=1.00
      src/koru/cli_cleaned.py:302-305  (_init_ci_main)
      src/koru/cli_init.py:103-119  (init_ci_main)
  [06b10647ffdd5626]   EXAC  to_json  L=3 N=2 saved=3 sim=1.00
      src/koru/deployment_events/batch.py:34-36  (to_json)
      src/koru/deployment_events/models.py:98-100  (to_json)
  [93c2d285f0f82504]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      src/koru/local_manager_state.py:57-59  (__init__)
      src/koru/local_manager_state.py:73-75  (__init__)
  [204c39c1b7c6c2bb]   EXAC  capture_one  L=3 N=2 saved=3 sim=1.00
      src/koruvision/providers/cli_tools.py:37-39  (capture_one)
      src/koruvision/providers/obs_websocket.py:229-231  (capture_one)
  [83806d712bf75019]   STRU  list_agent_backend_ids  L=3 N=2 saved=3 sim=1.00
      src/koru/agent_backends.py:100-102  (list_agent_backend_ids)
      src/koruos/strategies/registry.py:34-36  (list_os_strategy_ids)
  [19ffbb44324d5e1e]   STRU  iter_agent_backend_profiles  L=3 N=2 saved=3 sim=1.00
      src/koru/agent_backends.py:105-107  (iter_agent_backend_profiles)
      src/koruide/ide.py:93-95  (autopilot_ide_choices)
  [c313a68ea5e776b1]   STRU  _normalize_autonomous_argv  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:932-934  (_normalize_autonomous_argv)
      src/koru/wizard/cli.py:51-53  (propose_projects)
  [3e72ce8df48766bc]   STRU  _apply_auto_pipeline_flags  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:951-953  (_apply_auto_pipeline_flags)
      src/koru/autonomous.py:956-958  (_apply_replace_existing_flags)
  [815c4492e986dd60]   STRU  llm_needs_input_ticket_queue_name  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_chat_activity_config.py:76-78  (llm_needs_input_ticket_queue_name)
      src/koru/autonomous_cycle_chat_activity_config.py:81-83  (llm_needs_input_ticket_priority)
  [5d75a9aed94653a0]   STRU  allow_keyboard_autopilot_fallback  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_gate.py:54-56  (allow_keyboard_autopilot_fallback)
      src/koru/autonomous_cycle_gate.py:91-93  (scan_while_waiting_input_enabled)
  [db80bc98e097b6ec]   STRU  _auto_llm_ready_enabled  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_skip_conditions.py:20-22  (_auto_llm_ready_enabled)
      src/koru/autonomy/operator_pipeline.py:406-408  (_self_control_autorepair_enabled)
  [781cd2265323c713]   STRU  systemd_user_dir  L=3 N=2 saved=3 sim=1.00
      src/koru/autopilot/systemd_cli.py:15-17  (systemd_user_dir)
      src/koruide/config.py:66-68  (default_config_path)
  [60d745664334ec54]   STRU  redup_scan_command  L=3 N=2 saved=3 sim=1.00
      src/koru/redup_integration.py:22-24  (redup_scan_command)
      src/koru/redup_integration.py:27-29  (redup_check_command)
  [bb13ab89e965d21d]   STRU  build_dashboard_handler  L=3 N=2 saved=3 sim=1.00
      src/koruapi/dashboard_routes.py:583-585  (build_dashboard_handler)
      src/koruapi/dashboard_serve.py:94-96  (_build_handler)
  [3fc8b0d2a83cdbf8]   STRU  supported_autopilot_ide_ids  L=3 N=2 saved=3 sim=1.00
      src/koruide/ide.py:88-90  (supported_autopilot_ide_ids)
      src/koruide/ide.py:98-100  (vscode_extension_plugin_ide_ids)

REFACTOR[114] (ranked by priority):
  [1] ◐ extract_module     → src/koru/utils/agent_backends_main.py
      WHY: 2 occurrences of 57-line block across 2 files — saves 57 lines
      FILES: src/koru/cli_agent_backends.py, src/koru/cli_cleaned.py
  [2] ◐ extract_module     → src/koru/utils/_bootstrap_main.py
      WHY: 2 occurrences of 52-line block across 2 files — saves 52 lines
      FILES: src/koru/cli_bootstrap.py, src/koru/cli_cleaned.py
  [3] ◐ extract_function   → src/koru/utils/_build_agent_parser.py
      WHY: 2 occurrences of 49-line block across 2 files — saves 49 lines
      FILES: src/koru/cli_agent.py, src/koru/cli_cleaned.py
  [4] ○ extract_function   → src/koru/utils/_dsl_main.py
      WHY: 10 occurrences of 4-line block across 4 files — saves 36 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py, src/koru/cli_local_serve.py, src/koru/cli_serve.py
  [5] ○ extract_function   → src/koru/utils/emit_intent.py
      WHY: 7 occurrences of 6-line block across 1 files — saves 36 lines
      FILES: src/koru/observability_events.py
  [6] ○ extract_function   → src/koru/autopilot/utils/_add_calibrate_parser.py
      WHY: 2 occurrences of 35-line block across 1 files — saves 35 lines
      FILES: src/koru/autopilot/cli_parser.py
  [7] ○ extract_function   → src/utils/_run.py
      WHY: 5 occurrences of 8-line block across 5 files — saves 32 lines
      FILES: src/koru/ide_adapters/ide_reload.py, src/koruide/plugin_installer.py, src/koruos/strategies/darwin.py, src/koruos/strategies/wayland_linux.py, src/koruos/strategies/x11_linux.py
  [8] ○ extract_function   → src/koru/utils/_warn_autopilot_focus_retry.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: src/koru/autonomous_drive_retry_policy.py
  [9] ○ extract_function   → src/koru/utils/provision_cursor.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: src/koru/mcp_provision.py
  [10] ○ extract_function   → src/utils/reuse_window_reload_enabled.py
      WHY: 3 occurrences of 14-line block across 2 files — saves 28 lines
      FILES: src/koru/ide_adapters/ide_reload.py, src/koruide/command_catalog_store.py
  [11] ○ extract_function   → src/koru/wizard/utils/_finalise_ticket.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: src/koru/wizard/cli.py, src/koru/wizard/orchestrator.py
  [12] ○ extract_function   → src/utils/_koru_package_version.py
      WHY: 6 occurrences of 5-line block across 6 files — saves 25 lines
      FILES: src/koru/agents.py, src/koru/autonomous_startup.py, src/koru/cli_cleaned.py, src/koru/cli_parser.py, src/koruapi/cli.py +1 more
  [13] ○ extract_function   → src/utils/_plugin_package_version.py
      WHY: 4 occurrences of 7-line block across 2 files — saves 21 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [14] ○ extract_function   → src/koru/utils/_maybe_reexec_for_project_venv.py
      WHY: 2 occurrences of 21-line block across 2 files — saves 21 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [15] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 5 occurrences of 5-line block across 5 files — saves 20 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomous_daemon.py, src/koru/autonomous_processes.py
  [16] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: src/korullm/strategies/codex.py, src/korullm/strategies/ollama.py
  [17] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 7 occurrences of 3-line block across 5 files — saves 18 lines
      FILES: src/koru/activity_log.py, src/koru/autonomous_cycle_chat_activity_config.py, src/koru/autonomy/operator_pipeline.py, src/koru/ide_adapters/ide_reload.py, src/koruide/plugin_installer.py
  [18] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle_skip_conditions.py, src/koru/autonomy/phases/utils.py
  [19] ○ extract_function   → src/koru/utils/current_head.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomy/phases/utils.py
  [20] ○ extract_function   → src/koru/utils/_run_queue_loop.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [21] ○ extract_function   → src/koru/utils/_is_bare_invocation.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [22] ○ extract_function   → src/koru/utils/_load_tool_scaffold.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [23] ○ extract_function   → src/koru/utils/ide_router_main.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_ide_router.py
  [24] ○ extract_function   → src/koru/utils/_post_workers_register.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: src/koru/local_service.py
  [25] ○ extract_function   → src/koru/utils/_agent_main.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: src/koru/cli_agent.py, src/koru/cli_cleaned.py
  [26] ○ extract_function   → src/koru/utils/_project_cli_reexec_argv.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [27] ○ extract_function   → src/koru/utils/_build_task_parser.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [28] ○ extract_function   → src/koru/utils/_merge_cli_scaffold.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [29] ○ extract_function   → src/koru/utils/_task_main.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [30] ○ extract_function   → src/koru/ide_adapters/utils/reload_via_reopen_workspace.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/ide_adapters/ide_reload.py
  [31] ○ extract_function   → src/koruide/ides/utils/detection.py
      WHY: 4 occurrences of 5-line block across 4 files — saves 15 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/cursor.py, src/koruide/ides/windsurf.py, src/koruide/ides/zed.py
  [32] ○ extract_function   → scripts/utils/update_plugin_version_source.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [33] ○ extract_function   → src/koru/autonomy/phases/utils/_should_skip_repeated_create_failed_scan.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [34] ○ extract_function   → src/koru/autopilot/utils/_action_install_plugin.py
      WHY: 3 occurrences of 7-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/cli_command.py
  [35] ○ extract_function   → src/koru/utils/_peek_project_from_argv.py
      WHY: 3 occurrences of 7-line block across 3 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_auto.py, src/koru/cli_cleaned.py
  [36] ○ extract_function   → src/koru/utils/_maybe_print_project_venv_hint.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [37] ○ extract_function   → src/koru/utils/_tools_main.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_tools.py
  [38] ○ extract_function   → src/koru/utils/_runtime_context_main.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [39] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [40] ○ extract_function   → src/koru/autonomy/phases/utils/_remember_scan_create_failed_state.py
      WHY: 2 occurrences of 13-line block across 1 files — saves 13 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [41] ○ extract_function   → src/koru/utils/_should_suggest_wizard.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [42] ○ extract_function   → src/koru/utils/_render_runtime_context_text.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [43] ○ extract_function   → src/koru/utils/_path_is_relative_to.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koru/autonomous_runtime.py, src/koru/cli.py, src/koru/cli_cleaned.py
  [44] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py
  [45] ○ extract_function   → src/koruvision/providers/utils/list_monitors.py
      WHY: 4 occurrences of 4-line block across 4 files — saves 12 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/grim.py, src/koruvision/providers/portal_screencast.py, src/koruvision/providers/portal_screenshot.py
  [46] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [47] ○ extract_function   → src/utils/_build_local_serve_parser.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_local_serve.py, src/koruapi/local.py
  [48] ○ extract_function   → src/koruapi/utils/_handle_mcp_list_tickets.py
      WHY: 3 occurrences of 6-line block across 1 files — saves 12 lines
      FILES: src/koruapi/invoke_handlers.py
  [49] ○ extract_function   → src/koruide/utils/message_received.py
      WHY: 2 occurrences of 12-line block across 1 files — saves 12 lines
      FILES: src/koruide/protocol.py
  [50] ○ extract_function   → src/korullm/strategies/utils/idle_marker_patterns.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py, src/korullm/strategies/ollama.py
  [51] ○ extract_function   → src/utils/_trace_event_matches.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koruapi/dashboard_observability.py, src/koruobserve/cli.py
  [52] ○ extract_function   → src/koru/utils/_ensure_trusted_publisher_for_plugin.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: src/koru/autonomous_operator.py
  [53] ○ extract_function   → src/koru/utils/_build_serve_parser.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_serve.py
  [54] ○ extract_function   → src/koru/utils/_command_loop_main.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_loop.py
  [55] ○ extract_function   → src/utils/_event_to_record.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cqrs/event_store.py, src/koruapi/dashboard_observability.py
  [56] ○ extract_function   → src/utils/_versioned_plugin_vsix_candidates.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [57] ○ extract_function   → src/koru/utils/_print_task_result.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_task.py
  [58] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve_utils.py
  [59] ○ extract_function   → src/koruide/utils/extension_id_for_ide.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koruide/plugin_installer.py, src/koruide/plugin_version.py
  [60] ○ extract_function   → src/koruos/strategies/utils/_focus_via_wmctrl.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koruos/strategies/wayland_linux.py, src/koruos/strategies/x11_linux.py
  [61] ○ extract_function   → src/koru/utils/_default_runner.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomy/code2llm_discovery.py, src/koru/self_control.py
  [62] ○ extract_function   → src/koru/autopilot/utils/_action_drive.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: src/koru/autopilot/cli_command.py
  [63] ○ extract_function   → src/koru/utils/_refactor_planfile_handoff_main.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_refactor_planfile_handoff.py
  [64] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/koru/mcp_provision.py
  [65] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [66] ○ extract_function   → scripts/utils/get_plugin_version_from_source.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [67] ○ extract_function   → src/utils/llm_reflection_summary_max_age_seconds.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autonomous_cycle_chat_activity_config.py, src/koruide/daemon/handlers.py
  [68] ○ extract_function   → src/koru/autonomy/phases/utils/_create_failed_scan_cooldown_seconds.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [69] ○ extract_function   → src/koru/utils/_build_tools_parser.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_tools.py
  [70] ○ extract_function   → src/koru/utils/_check_git_commit_policy.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: src/koru/policy.py
  [71] ○ extract_function   → src/koru/utils/as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [72] ○ extract_function   → src/koru/utils/confirm_replace_existing.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [73] ○ extract_function   → src/koru/utils/_context_main.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_context.py
  [74] ○ extract_function   → src/koruobserve/utils/cmd_providers_list.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koruobserve/providers_cli.py
  [75] ○ extract_function   → src/koru/cqrs/utils/all_events.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [76] ○ extract_function   → src/koru/cqrs/utils/events_for_aggregate.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [77] ○ extract_function   → src/koruide/ides/utils/plugin.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/windsurf.py
  [78] ○ extract_function   → src/koru/utils/process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [79] ○ extract_function   → src/koru/autonomy/phases/utils/_scan_result_is_create_failed_only.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [80] ○ extract_function   → src/utils/_previous_serve_config.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/configurator.py, src/koru/tasks.py, src/koruapi/dashboard_config.py
  [81] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [82] ○ extract_function   → src/koruide/ides/utils/keyboard.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruide/ides/jetbrains.py, src/koruide/ides/zed.py
  [83] ○ extract_function   → src/koruide/utils/ydotool_enter_keycode.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koruide/injector_backends.py
  [84] ○ extract_function   → src/koruide/utils/os_injector_env_disabled.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: src/koruide/os_injector.py
  [85] ○ extract_function   → src/koruvision/utils/png_dimensions.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruvision/capture_mss.py, src/koruvision/providers/base.py
  [86] ○ extract_function   → src/utils/_current_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous_daemon.py, src/koruide/daemon/protocol.py
  [87] ○ extract_function   → src/koru/utils/_package_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autopilot/install_manager.py, src/koru/self_control.py
  [88] ○ extract_function   → src/koru/utils/_command_value.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_parser.py
  [89] ○ extract_function   → src/koru/utils/_build_runtime_context_parser.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_runtime_context.py
  [90] ○ extract_function   → src/koru/cqrs/utils/runtime_for_project.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/cqrs/__init__.py
  [91] ○ extract_function   → src/koru/utils/_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/local_manager_client.py, src/koru/local_manager_state.py
  [92] ○ extract_function   → src/utils/planfile_dir.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/runtime.py, src/koruapi/dashboard_serve_utils.py
  [93] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [94] ○ extract_function   → src/koruide/ides/utils/terminal.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/windsurf.py
  [95] ○ extract_function   → src/koruide/ides/utils/aliases.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/vscode.py, src/koruide/ides/vscodium.py
  [96] ○ extract_function   → src/koru/utils/_cycle_attr.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_cycle_chat_activity.py, src/koru/autonomous_cycle_drive_retry.py
  [97] ○ extract_function   → src/koru/utils/status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle_common.py
  [98] ○ extract_function   → src/koru/utils/_build_queue_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [99] ○ extract_function   → src/utils/_looks_like_autonomous_up_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_processes.py, src/koruobserve/providers_cli.py
  [100] ○ extract_function   → src/koru/utils/_init_ci_main.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_init.py
  [101] ○ extract_function   → src/koru/deployment_events/utils/to_json.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/deployment_events/batch.py, src/koru/deployment_events/models.py
  [102] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/local_manager_state.py
  [103] ○ extract_function   → src/koruvision/providers/utils/capture_one.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/obs_websocket.py
  [104] ○ extract_function   → src/utils/list_agent_backend_ids.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/agent_backends.py, src/koruos/strategies/registry.py
  [105] ○ extract_function   → src/utils/iter_agent_backend_profiles.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/agent_backends.py, src/koruide/ide.py
  [106] ○ extract_function   → src/koru/utils/_normalize_autonomous_argv.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous.py, src/koru/wizard/cli.py
  [107] ○ extract_function   → src/koru/utils/_apply_auto_pipeline_flags.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous.py
  [108] ○ extract_function   → src/koru/utils/llm_needs_input_ticket_queue_name.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_chat_activity_config.py
  [109] ○ extract_function   → src/koru/utils/allow_keyboard_autopilot_fallback.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_gate.py
  [110] ○ extract_function   → src/koru/utils/_auto_llm_ready_enabled.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_skip_conditions.py, src/koru/autonomy/operator_pipeline.py
  [111] ○ extract_function   → src/utils/systemd_user_dir.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autopilot/systemd_cli.py, src/koruide/config.py
  [112] ○ extract_function   → src/koru/utils/redup_scan_command.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/redup_integration.py
  [113] ○ extract_function   → src/koruapi/utils/build_dashboard_handler.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruapi/dashboard_routes.py, src/koruapi/dashboard_serve.py
  [114] ○ extract_function   → src/koruide/utils/supported_autopilot_ide_ids.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruide/ide.py

QUICK_WINS[81] (low risk, high savings — do first):
  [4] extract_function   saved=36L  → src/koru/utils/_dsl_main.py
      FILES: cli.py, cli_cleaned.py, cli_local_serve.py +1
  [5] extract_function   saved=36L  → src/koru/utils/emit_intent.py
      FILES: observability_events.py
  [6] extract_function   saved=35L  → src/koru/autopilot/utils/_add_calibrate_parser.py
      FILES: cli_parser.py
  [7] extract_function   saved=32L  → src/utils/_run.py
      FILES: ide_reload.py, plugin_installer.py, darwin.py +2
  [8] extract_function   saved=30L  → src/koru/utils/_warn_autopilot_focus_retry.py
      FILES: autonomous_drive_retry_policy.py
  [9] extract_function   saved=30L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [10] extract_function   saved=28L  → src/utils/reuse_window_reload_enabled.py
      FILES: ide_reload.py, command_catalog_store.py
  [11] extract_function   saved=25L  → src/koru/wizard/utils/_finalise_ticket.py
      FILES: cli.py, orchestrator.py
  [12] extract_function   saved=25L  → src/utils/_koru_package_version.py
      FILES: agents.py, autonomous_startup.py, cli_cleaned.py +3
  [13] extract_function   saved=21L  → src/utils/_plugin_package_version.py
      FILES: install_plugin_cli.py, plugin_installer.py

EFFORT_ESTIMATE (total ≈ 50.0h):
  hard   agent_backends_main                 saved=57L  ~171min
  hard   _bootstrap_main                     saved=52L  ~156min
  hard   _build_agent_parser                 saved=49L  ~147min
  medium _dsl_main                           saved=36L  ~72min
  medium emit_intent                         saved=36L  ~72min
  hard   _add_calibrate_parser               saved=35L  ~105min
  medium _run                                saved=32L  ~64min
  medium _warn_autopilot_focus_retry         saved=30L  ~60min
  medium provision_cursor                    saved=30L  ~60min
  medium reuse_window_reload_enabled         saved=28L  ~56min
  ... +104 more (~2036min)

METRICS-TARGET:
  dup_groups:  114 → 0
  saved_lines: 1403 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 4829 func | 416f | 2026-05-25
# generated in 0.03s

NEXT[5] (ranked by impact):
  [1] !! SPLIT           plugins/koru-autopilot-cursor/src/extension.ts
      WHY: 3013L, 2 classes, max CC=15
      EFFORT: ~4h  IMPACT: 45195

  [2] !! SPLIT           plugins/koru-autopilot-vscode/src/extension.ts
      WHY: 2757L, 2 classes, max CC=14
      EFFORT: ~4h  IMPACT: 38598

  [3] !! SPLIT           plugins/koru-autopilot-vscodium/src/extension.ts
      WHY: 2753L, 2 classes, max CC=14
      EFFORT: ~4h  IMPACT: 38542

  [4] !! SPLIT-FUNC      validate_ide_command_scenario  CC=37  fan=18
      WHY: CC=37 exceeds 15
      EFFORT: ~1h  IMPACT: 666

  [5] !  SPLIT-FUNC      AutopilotBridge._performInject  CC=15  fan=20
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 300


RISKS[3]:
  ⚠ Splitting plugins/koru-autopilot-cursor/src/extension.ts may break 210 import paths
  ⚠ Splitting plugins/koru-autopilot-vscode/src/extension.ts may break 207 import paths
  ⚠ Splitting plugins/koru-autopilot-vscodium/src/extension.ts may break 207 import paths

METRICS-TARGET:
  CC̄:          3.6 → ≤2.5
  max-CC:      37 → ≤18
  god-modules: 17 → 0
  high-CC(≥15): 6 → ≤3
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
  prev CC̄=3.6 → now CC̄=3.6
```

## Intent

Closed-loop automation across semcod/* repositories.
