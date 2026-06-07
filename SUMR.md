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
- **version**: `0.1.317`
- **python_requires**: `>=3.12,<3.14`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, testql(9), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, package.json, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.317;
}

dependencies {
  runtime: "gillm>=0.1.9, pyyaml>=6.0,<7.0, rich>=14.3.4";
  dev: "gillm>=0.1.9, pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, ruff>=0.11,<0.16, mypy>=1.11,<3.0, pyright>=1.1.390,<2.0, hypothesis>=6.112,<7.0, pre-commit>=3.8,<5.0, types-PyYAML>=6.0,<7.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60, tagi>=0.49.0";
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="coru"] {

}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS);
}

workflow[name="test-fast"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --quick $(PYTEST_ARGS);
}

workflow[name="test-parallel"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --fast --maxfail=1 $(PYTEST_ARGS);
}

workflow[name="test-parallel-fast"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --changed --critical --quick $(PYTEST_ARGS);
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

workflow[name="clean-dist"] {
  trigger: manual;
  step-1: run cmd=rm -f dist/koru-*;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=rm -rf build/ *.egg-info src/*.egg-info;
  step-2: run cmd=$(PYTHON) -m pip install -q build;
  step-3: run cmd=$(PYTHON) -m build;
  step-4: run cmd=echo "✓ Built dist/koru-$(VERSION)*";
}

workflow[name="check-dist"] {
  trigger: manual;
  step-1: run cmd=test -n "$(VERSION)" || (echo "Could not read version from pyproject.toml" && exit 1);
  step-2: run cmd=test -n "$$(ls dist/koru-$(VERSION)* 2>/dev/null)" || (echo "No artifacts for $(VERSION) in dist/ — run make build" && exit 1);
  step-3: run cmd=$(PYTHON) -m pip install -q twine;
  step-4: run cmd=$(PYTHON) -m twine check dist/koru-$(VERSION)*;
}

workflow[name="bump-patch"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping patch version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py patch;
}

workflow[name="bump-minor"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping minor version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py minor;
}

workflow[name="bump-major"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping major version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py major;
}

workflow[name="publish-test"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing to TestPyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=echo "   Skipping upload (dist/koru-$(VERSION)* built and twine-checked)."; \;
  step-9: run cmd=else \;
  step-10: run cmd=$(PYTHON) -m pip install -q twine && \;
  step-11: run cmd=$(PYTHON) -m twine upload --repository testpypi dist/koru-$(VERSION)* && \;
  step-12: run cmd=echo "✓ Published koru $(VERSION) to TestPyPI"; \;
  step-13: run cmd=fi';
}

workflow[name="publish"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing to PyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=echo "   Example: PYPI_API_TOKEN=pypi-xxx make publish"; \;
  step-9: run cmd=exit 1; \;
  step-10: run cmd=fi';
  step-11: run cmd=$(MAKE) bump-patch;
  step-12: run cmd=$(MAKE) build;
  step-13: run cmd=$(MAKE) check-dist;
  step-14: run cmd=echo "📦 Uploading dist/koru-$(VERSION)* to PyPI...";
  step-15: run cmd=$(PYTHON) -m pip install -q twine;
  step-16: run cmd=$(PYTHON) -m twine upload dist/koru-$(VERSION)*;
  step-17: run cmd=echo "✓ Published koru $(VERSION) to PyPI";
}

workflow[name="packages-build"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail; \;
  step-2: run cmd=if [ -z "$(PACKAGE_DIRS)" ]; then \;
  step-3: run cmd=echo "No package directories found under packages/"; \;
  step-4: run cmd=exit 1; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=$(PYTHON) -m pip install -q build; \;
  step-7: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-8: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-9: run cmd=echo "- skipping $$pkg (no pyproject.toml)"; \;
  step-10: run cmd=continue; \;
  step-11: run cmd=fi; \;
  step-12: run cmd=echo "📦 building $$pkg"; \;
  step-13: run cmd=rm -rf "$$pkg/dist" "$$pkg/build" "$$pkg"/*.egg-info "$$pkg/src"/*.egg-info; \;
  step-14: run cmd=$(PYTHON) -m build "$$pkg"; \;
  step-15: run cmd=done;
}

workflow[name="packages-check"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail; \;
  step-2: run cmd=$(PYTHON) -m pip install -q twine; \;
  step-3: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-4: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-5: run cmd=continue; \;
  step-6: run cmd=fi; \;
  step-7: run cmd=if ls "$$pkg"/dist/* >/dev/null 2>&1; then \;
  step-8: run cmd=echo "🔎 twine check $$pkg/dist/*"; \;
  step-9: run cmd=$(PYTHON) -m twine check "$$pkg"/dist/*; \;
  step-10: run cmd=else \;
  step-11: run cmd=echo "No artifacts in $$pkg/dist (run: make packages-build)"; \;
  step-12: run cmd=exit 1; \;
  step-13: run cmd=fi; \;
  step-14: run cmd=done;
}

workflow[name="packages-publish-test"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing packages/* to TestPyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=echo "   Skipping upload (artifacts are built and twine-checked)."; \;
  step-9: run cmd=exit 0; \;
  step-10: run cmd=fi; \;
  step-11: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-12: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-13: run cmd=continue; \;
  step-14: run cmd=fi; \;
  step-15: run cmd=echo "⬆️  testpypi upload $$pkg/dist/*"; \;
  step-16: run cmd=$(PYTHON) -m twine upload --repository testpypi "$$pkg"/dist/*; \;
  step-17: run cmd=done; \;
  step-18: run cmd=echo "✓ Published all packages/* to TestPyPI"';
}

workflow[name="packages-publish"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing packages/* to PyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=exit 1; \;
  step-9: run cmd=fi; \;
  step-10: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-11: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-12: run cmd=continue; \;
  step-13: run cmd=fi; \;
  step-14: run cmd=echo "⬆️  pypi upload $$pkg/dist/*"; \;
  step-15: run cmd=$(PYTHON) -m twine upload "$$pkg"/dist/*; \;
  step-16: run cmd=done; \;
  step-17: run cmd=echo "✓ Published all packages/* to PyPI"';
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
  step-1: run cmd=scripts/koru-pytest.sh --critical --fast {{.CLI_ARGS}};
}

workflow[name="test:quick"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --critical --quick {{.CLI_ARGS}};
}

workflow[name="test:parallel"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --critical --fast --maxfail=1 {{.CLI_ARGS}};
}

workflow[name="test:changed"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --changed --critical --quick {{.CLI_ARGS}};
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
  python_version: >=3.12,<3.14;
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
    desc: Run critical tests quietly in parallel when pytest-xdist is installed
    cmds:
      - scripts/koru-pytest.sh --critical --fast {{.CLI_ARGS}}

  test:quick:
    desc: Fastest feedback loop (parallel, fail fast, failed tests first)
    cmds:
      - scripts/koru-pytest.sh --critical --quick {{.CLI_ARGS}}

  test:parallel:
    desc: Run critical tests in parallel with configurable workers (KORU_PYTEST_WORKERS=4)
    cmds:
      - scripts/koru-pytest.sh --critical --fast --maxfail=1 {{.CLI_ARGS}}

  test:changed:
    desc: Run changed pytest files under tests/; falls back to default tests when none changed
    cmds:
      - scripts/koru-pytest.sh --changed --critical --quick {{.CLI_ARGS}}

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
gillm>=0.1.9
pyyaml>=6.0,<7.0
rich>=14.3.4
```

### Development

```text markpact:deps python scope=dev
gillm>=0.1.9
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
tagi>=0.49.0
```

## Call Graph

*263 nodes · 500 edges · 26 modules · CC̄=3.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in project)* | 0 | 835 | 0 | **835** |
| `list` *(in src.koru.wizard.gui.static.wizard)* | 5 | 188 | 9 | **197** |
| `_attempt_plugin_self_heal` *(in packages.coru.src.coru.cli)* | 12 ⚠ | 2 | 36 | **38** |
| `detect_running_ides` *(in src.koruide.ide)* | 17 ⚠ | 27 | 11 | **38** |
| `_diagnose_lane` *(in packages.coru.src.coru.cli)* | 15 ⚠ | 4 | 31 | **35** |
| `_auto_readiness_gate` *(in packages.coru.src.coru.cli)* | 22 ⚠ | 1 | 33 | **34** |
| `_lane_status_payload` *(in packages.coru.src.coru.cli)* | 19 ⚠ | 12 | 21 | **33** |
| `load_registry` *(in packages.coru.src.coru.supervisor.registry)* | 5 | 21 | 11 | **32** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.46s
# nodes: 263 | edges: 500 | modules: 26
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:835  out:0  total:835
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:188  out:9  total:197
  packages.coru.src.coru.cli._attempt_plugin_self_heal
    CC=12  in:2  out:36  total:38
  src.koruide.ide.detect_running_ides
    CC=17  in:27  out:11  total:38
  packages.coru.src.coru.cli._diagnose_lane
    CC=15  in:4  out:31  total:35
  packages.coru.src.coru.cli._auto_readiness_gate
    CC=22  in:1  out:33  total:34
  packages.coru.src.coru.cli._lane_status_payload
    CC=19  in:12  out:21  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._infer_default_ide
    CC=26  in:3  out:28  total:31
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:6  out:24  total:30
  plugins.koru-autopilot-shared.src.bridge-focus-core.SharedAutopilotBridgeFocusCore.next
    CC=2  in:27  out:1  total:28
  packages.coru.src.coru.cli._repo_root
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.repair.diagnostics.collect_problems_from_status
    CC=19  in:0  out:28  total:28
  packages.coru.src.coru.cli._trace
    CC=3  in:23  out:5  total:28
  packages.coru.src.coru.repair.diagnostics._collect_plugin_alignment_problems
    CC=19  in:1  out:26  total:27
  packages.coru.src.coru.cli._auto_ownership_gate
    CC=22  in:2  out:25  total:27
  packages.coru.src.coru.cli._lane_calibration
    CC=14  in:2  out:25  total:27
  packages.coru.src.coru.cli._run_default_autonomous
    CC=10  in:2  out:24  total:26
  packages.coru.src.coru.cli._maybe_reexec_into_project_python
    CC=12  in:1  out:25  total:26
  packages.coru.src.coru.repair.projector._project_one_session
    CC=19  in:1  out:25  total:26

MODULES:
  packages.coru.src.coru.cli  [179 funcs]
    _add_lane_identifiers  CC=1  out:2
    _add_shell_argument  CC=1  out:1
    _agent_lane_from_auto_args  CC=7  out:7
    _alive_daemon_ide  CC=17  out:19
    _alive_daemon_instance  CC=13  out:16
    _append_desktop_focus_lines  CC=2  out:2
    _attempt_plugin_self_heal  CC=12  out:36
    _auto_default_instance  CC=4  out:3
    _auto_ownership_gate  CC=22  out:25
    _auto_readiness_can_continue_with_keyboard_fallback  CC=7  out:6
  packages.coru.src.coru.ecosystem  [5 funcs]
    _default_runner  CC=1  out:2
    _detect_running_plugin_ides  CC=4  out:2
    _local_package_paths  CC=5  out:7
    sync_ecosystem  CC=14  out:13
    sync_python_packages  CC=6  out:5
  packages.coru.src.coru.ide_detection  [4 funcs]
    _terminal_shell_context_fallback  CC=22  out:21
    terminal_host_kind  CC=2  out:1
    terminal_ide_hint  CC=1  out:1
    terminal_shell_context  CC=3  out:2
  packages.coru.src.coru.repair.diagnostics  [19 funcs]
    _collect_manage_action_problems  CC=4  out:3
    _collect_manage_issue_problems  CC=4  out:3
    _collect_plugin_alignment_problems  CC=19  out:26
    _dedupe_problems  CC=3  out:3
    _drive_intent_unverified_problem  CC=8  out:11
    _focus_risk_problem  CC=4  out:6
    _host_key_trace_problem  CC=10  out:11
    _installed_extension_dir  CC=4  out:6
    _paste_risk_problem  CC=5  out:7
    _plugin_row_for_ide  CC=7  out:7
  packages.coru.src.coru.repair.events  [1 funcs]
    aggregate_id_for  CC=1  out:3
  packages.coru.src.coru.repair.pipeline  [9 funcs]
    _get_installed_version  CC=6  out:7
    _installed_extension_dir  CC=4  out:6
    _read_vsix_version  CC=3  out:5
    _resolve_repo_vsix  CC=6  out:6
    _unpack_vsix_archive  CC=4  out:12
    _vsix_source  CC=2  out:3
    _vsix_unpack_layout  CC=2  out:4
    _vsix_unpack_result  CC=4  out:6
    manual_vsix_unpack  CC=3  out:5
  packages.coru.src.coru.repair.projector  [4 funcs]
    _project_one_session  CC=19  out:25
    format_case_llm  CC=5  out:5
    format_history_llm  CC=3  out:2
    project_repair_cases  CC=9  out:10
  packages.coru.src.coru.repair.query  [3 funcs]
    cases  CC=2  out:2
    cases_for_lane  CC=5  out:4
    format_llm  CC=2  out:3
  packages.coru.src.coru.repair.registry  [2 funcs]
    playbook_for_codes  CC=5  out:6
    registry_steps_for_code  CC=3  out:1
  packages.coru.src.coru.repair.service  [1 funcs]
    run_repair_with_events  CC=3  out:7
  packages.coru.src.coru.repair_registry  [1 funcs]
    run_repair_pipeline  CC=1  out:1
  packages.coru.src.coru.supervisor.paths  [1 funcs]
    registry_path  CC=1  out:1
  packages.coru.src.coru.supervisor.registry  [2 funcs]
    active_lane_pair  CC=2  out:2
    load_registry  CC=5  out:11
  packages.koruenv.src.koruenv.cli  [6 funcs]
    _emit_log  CC=5  out:7
    _iso_ts  CC=1  out:4
    _normalize_log_format  CC=3  out:2
    _run_with_overlay  CC=4  out:11
    _strip_double_dash  CC=3  out:1
    main  CC=5  out:18
  packages.koruenv.src.koruenv.lane  [6 funcs]
    _fallback_temp_dir  CC=5  out:5
    build_lane_environ  CC=2  out:5
    resolve_lane_socket  CC=1  out:1
    resolve_lane_socket_for_os  CC=5  out:10
    validate_ide  CC=3  out:6
    validate_instance  CC=3  out:4
  packages.nlpshim.src.nlpshim.client  [5 funcs]
    __init__  CC=2  out:2
    parse_intent  CC=15  out:20
    _use_intent_ir  CC=2  out:1
    analyze_text_structure  CC=2  out:2
    get_nlp2dsl_client  CC=2  out:0
  packages.nlpshim.src.nlpshim.conversation_client  [3 funcs]
    __init__  CC=2  out:2
    export_trace  CC=1  out:2
    message  CC=9  out:22
  packages.nlpshim.src.nlpshim.conversation_test_api  [2 funcs]
    complete_missing_fields  CC=1  out:2
    parse_conversation_step  CC=10  out:16
  plugins.koru-autopilot-shared.src.bridge-focus-core  [1 funcs]
    next  CC=2  out:1
  plugins.koru-autopilot-shared.src.bridge-network  [1 funcs]
    dispatch  CC=10  out:6
  project  [1 funcs]
    print  CC=0  out:0
  src.koru.autonomy.env  [1 funcs]
    plugin_required_for_ide  CC=8  out:7
  src.koru.autonomy.ide_operator_guidance  [1 funcs]
    terminal_kind_label  CC=3  out:0
  src.koru.ide_adapters.ide_reload  [2 funcs]
    connect_via_command_palette  CC=1  out:1
    try_reload_vscode_family_ide  CC=12  out:15
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=17  out:11
    detect_terminal_host_context  CC=9  out:9

EDGES:
  packages.koruenv.src.koruenv.cli._emit_log → packages.koruenv.src.koruenv.cli._iso_ts
  packages.koruenv.src.koruenv.cli._strip_double_dash → src.koru.wizard.gui.static.wizard.list
  packages.koruenv.src.koruenv.cli._run_with_overlay → packages.koruenv.src.koruenv.cli._emit_log
  packages.koruenv.src.koruenv.cli._run_with_overlay → src.koru.wizard.gui.static.wizard.list
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._normalize_log_format
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._strip_double_dash
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._run_with_overlay
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.lane.build_lane_environ
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._emit_log
  packages.koruenv.src.koruenv.cli.main → project.print
  packages.koruenv.src.koruenv.lane.resolve_lane_socket → packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os
  packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os → packages.koruenv.src.koruenv.lane.validate_instance
  packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os → packages.koruenv.src.koruenv.lane._fallback_temp_dir
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.validate_ide
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.validate_instance
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.__init__ → packages.nlpshim.src.nlpshim.client.get_nlp2dsl_client
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.message → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.export_trace → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.client.analyze_text_structure → packages.nlpshim.src.nlpshim.client._use_intent_ir
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.__init__ → packages.nlpshim.src.nlpshim.client.get_nlp2dsl_client
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.parse_intent → packages.nlpshim.src.nlpshim.client.analyze_text_structure
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.parse_intent → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_test_api.parse_conversation_step → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_test_api.complete_missing_fields → src.koru.wizard.gui.static.wizard.list
  packages.coru.src.coru.ecosystem.sync_python_packages → packages.coru.src.coru.ecosystem._local_package_paths
  packages.coru.src.coru.ecosystem._default_runner → src.koru.wizard.gui.static.wizard.list
  packages.coru.src.coru.ecosystem._detect_running_plugin_ides → src.koruide.ide.detect_running_ides
  packages.coru.src.coru.ecosystem.sync_ecosystem → packages.coru.src.coru.ecosystem.sync_python_packages
  packages.coru.src.coru.ecosystem.sync_ecosystem → packages.coru.src.coru.ecosystem._detect_running_plugin_ides
  packages.coru.src.coru.cli._trace → project.print
  packages.coru.src.coru.cli._trace → packages.coru.src.coru.cli._trace_enabled
  packages.coru.src.coru.cli._current_log_format → packages.coru.src.coru.cli._normalize_log_format
  packages.coru.src.coru.cli._emit_log → packages.coru.src.coru.cli._current_log_format
  packages.coru.src.coru.cli._emit_log → project.print
  packages.coru.src.coru.cli._print_runtime_versions → project.print
  packages.coru.src.coru.cli._print_runtime_versions → packages.coru.src.coru.cli._distribution_version
  packages.coru.src.coru.cli._startup_mode → project.print
  packages.coru.src.coru.cli._autonomous_startup_chain → packages.coru.src.coru.cli._resolve_defaults
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._agent_lane_from_auto_args
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._resolve_defaults
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._terminal_shell_context
  packages.coru.src.coru.cli._run_default_autonomous → project.print
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._print_runtime_versions
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._print_troubleshooting_log_locations
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._repo_root
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._autonomous_startup_chain
  packages.coru.src.coru.cli._running_ide_choices → src.koruide.ide.detect_running_ides
  packages.coru.src.coru.cli._supervisor_project_choices → packages.coru.src.coru.supervisor.registry.load_registry
  packages.coru.src.coru.cli._supervisor_project_choices → packages.coru.src.coru.supervisor.paths.registry_path
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (8)

**`coru calibration command (WUP quick / dry-run safe)`**

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
# generated in 0.46s
# nodes: 263 | edges: 500 | modules: 26
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:835  out:0  total:835
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:188  out:9  total:197
  packages.coru.src.coru.cli._attempt_plugin_self_heal
    CC=12  in:2  out:36  total:38
  src.koruide.ide.detect_running_ides
    CC=17  in:27  out:11  total:38
  packages.coru.src.coru.cli._diagnose_lane
    CC=15  in:4  out:31  total:35
  packages.coru.src.coru.cli._auto_readiness_gate
    CC=22  in:1  out:33  total:34
  packages.coru.src.coru.cli._lane_status_payload
    CC=19  in:12  out:21  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._infer_default_ide
    CC=26  in:3  out:28  total:31
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:6  out:24  total:30
  plugins.koru-autopilot-shared.src.bridge-focus-core.SharedAutopilotBridgeFocusCore.next
    CC=2  in:27  out:1  total:28
  packages.coru.src.coru.cli._repo_root
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.repair.diagnostics.collect_problems_from_status
    CC=19  in:0  out:28  total:28
  packages.coru.src.coru.cli._trace
    CC=3  in:23  out:5  total:28
  packages.coru.src.coru.repair.diagnostics._collect_plugin_alignment_problems
    CC=19  in:1  out:26  total:27
  packages.coru.src.coru.cli._auto_ownership_gate
    CC=22  in:2  out:25  total:27
  packages.coru.src.coru.cli._lane_calibration
    CC=14  in:2  out:25  total:27
  packages.coru.src.coru.cli._run_default_autonomous
    CC=10  in:2  out:24  total:26
  packages.coru.src.coru.cli._maybe_reexec_into_project_python
    CC=12  in:1  out:25  total:26
  packages.coru.src.coru.repair.projector._project_one_session
    CC=19  in:1  out:25  total:26

MODULES:
  packages.coru.src.coru.cli  [179 funcs]
    _add_lane_identifiers  CC=1  out:2
    _add_shell_argument  CC=1  out:1
    _agent_lane_from_auto_args  CC=7  out:7
    _alive_daemon_ide  CC=17  out:19
    _alive_daemon_instance  CC=13  out:16
    _append_desktop_focus_lines  CC=2  out:2
    _attempt_plugin_self_heal  CC=12  out:36
    _auto_default_instance  CC=4  out:3
    _auto_ownership_gate  CC=22  out:25
    _auto_readiness_can_continue_with_keyboard_fallback  CC=7  out:6
  packages.coru.src.coru.ecosystem  [5 funcs]
    _default_runner  CC=1  out:2
    _detect_running_plugin_ides  CC=4  out:2
    _local_package_paths  CC=5  out:7
    sync_ecosystem  CC=14  out:13
    sync_python_packages  CC=6  out:5
  packages.coru.src.coru.ide_detection  [4 funcs]
    _terminal_shell_context_fallback  CC=22  out:21
    terminal_host_kind  CC=2  out:1
    terminal_ide_hint  CC=1  out:1
    terminal_shell_context  CC=3  out:2
  packages.coru.src.coru.repair.diagnostics  [19 funcs]
    _collect_manage_action_problems  CC=4  out:3
    _collect_manage_issue_problems  CC=4  out:3
    _collect_plugin_alignment_problems  CC=19  out:26
    _dedupe_problems  CC=3  out:3
    _drive_intent_unverified_problem  CC=8  out:11
    _focus_risk_problem  CC=4  out:6
    _host_key_trace_problem  CC=10  out:11
    _installed_extension_dir  CC=4  out:6
    _paste_risk_problem  CC=5  out:7
    _plugin_row_for_ide  CC=7  out:7
  packages.coru.src.coru.repair.events  [1 funcs]
    aggregate_id_for  CC=1  out:3
  packages.coru.src.coru.repair.pipeline  [9 funcs]
    _get_installed_version  CC=6  out:7
    _installed_extension_dir  CC=4  out:6
    _read_vsix_version  CC=3  out:5
    _resolve_repo_vsix  CC=6  out:6
    _unpack_vsix_archive  CC=4  out:12
    _vsix_source  CC=2  out:3
    _vsix_unpack_layout  CC=2  out:4
    _vsix_unpack_result  CC=4  out:6
    manual_vsix_unpack  CC=3  out:5
  packages.coru.src.coru.repair.projector  [4 funcs]
    _project_one_session  CC=19  out:25
    format_case_llm  CC=5  out:5
    format_history_llm  CC=3  out:2
    project_repair_cases  CC=9  out:10
  packages.coru.src.coru.repair.query  [3 funcs]
    cases  CC=2  out:2
    cases_for_lane  CC=5  out:4
    format_llm  CC=2  out:3
  packages.coru.src.coru.repair.registry  [2 funcs]
    playbook_for_codes  CC=5  out:6
    registry_steps_for_code  CC=3  out:1
  packages.coru.src.coru.repair.service  [1 funcs]
    run_repair_with_events  CC=3  out:7
  packages.coru.src.coru.repair_registry  [1 funcs]
    run_repair_pipeline  CC=1  out:1
  packages.coru.src.coru.supervisor.paths  [1 funcs]
    registry_path  CC=1  out:1
  packages.coru.src.coru.supervisor.registry  [2 funcs]
    active_lane_pair  CC=2  out:2
    load_registry  CC=5  out:11
  packages.koruenv.src.koruenv.cli  [6 funcs]
    _emit_log  CC=5  out:7
    _iso_ts  CC=1  out:4
    _normalize_log_format  CC=3  out:2
    _run_with_overlay  CC=4  out:11
    _strip_double_dash  CC=3  out:1
    main  CC=5  out:18
  packages.koruenv.src.koruenv.lane  [6 funcs]
    _fallback_temp_dir  CC=5  out:5
    build_lane_environ  CC=2  out:5
    resolve_lane_socket  CC=1  out:1
    resolve_lane_socket_for_os  CC=5  out:10
    validate_ide  CC=3  out:6
    validate_instance  CC=3  out:4
  packages.nlpshim.src.nlpshim.client  [5 funcs]
    __init__  CC=2  out:2
    parse_intent  CC=15  out:20
    _use_intent_ir  CC=2  out:1
    analyze_text_structure  CC=2  out:2
    get_nlp2dsl_client  CC=2  out:0
  packages.nlpshim.src.nlpshim.conversation_client  [3 funcs]
    __init__  CC=2  out:2
    export_trace  CC=1  out:2
    message  CC=9  out:22
  packages.nlpshim.src.nlpshim.conversation_test_api  [2 funcs]
    complete_missing_fields  CC=1  out:2
    parse_conversation_step  CC=10  out:16
  plugins.koru-autopilot-shared.src.bridge-focus-core  [1 funcs]
    next  CC=2  out:1
  plugins.koru-autopilot-shared.src.bridge-network  [1 funcs]
    dispatch  CC=10  out:6
  project  [1 funcs]
    print  CC=0  out:0
  src.koru.autonomy.env  [1 funcs]
    plugin_required_for_ide  CC=8  out:7
  src.koru.autonomy.ide_operator_guidance  [1 funcs]
    terminal_kind_label  CC=3  out:0
  src.koru.ide_adapters.ide_reload  [2 funcs]
    connect_via_command_palette  CC=1  out:1
    try_reload_vscode_family_ide  CC=12  out:15
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=17  out:11
    detect_terminal_host_context  CC=9  out:9

EDGES:
  packages.koruenv.src.koruenv.cli._emit_log → packages.koruenv.src.koruenv.cli._iso_ts
  packages.koruenv.src.koruenv.cli._strip_double_dash → src.koru.wizard.gui.static.wizard.list
  packages.koruenv.src.koruenv.cli._run_with_overlay → packages.koruenv.src.koruenv.cli._emit_log
  packages.koruenv.src.koruenv.cli._run_with_overlay → src.koru.wizard.gui.static.wizard.list
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._normalize_log_format
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._strip_double_dash
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._run_with_overlay
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.lane.build_lane_environ
  packages.koruenv.src.koruenv.cli.main → packages.koruenv.src.koruenv.cli._emit_log
  packages.koruenv.src.koruenv.cli.main → project.print
  packages.koruenv.src.koruenv.lane.resolve_lane_socket → packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os
  packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os → packages.koruenv.src.koruenv.lane.validate_instance
  packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os → packages.koruenv.src.koruenv.lane._fallback_temp_dir
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.validate_ide
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.validate_instance
  packages.koruenv.src.koruenv.lane.build_lane_environ → packages.koruenv.src.koruenv.lane.resolve_lane_socket_for_os
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.__init__ → packages.nlpshim.src.nlpshim.client.get_nlp2dsl_client
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.message → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.export_trace → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.client.analyze_text_structure → packages.nlpshim.src.nlpshim.client._use_intent_ir
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.__init__ → packages.nlpshim.src.nlpshim.client.get_nlp2dsl_client
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.parse_intent → packages.nlpshim.src.nlpshim.client.analyze_text_structure
  packages.nlpshim.src.nlpshim.client.NLPBridgeClient.parse_intent → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_test_api.parse_conversation_step → src.koru.wizard.gui.static.wizard.list
  packages.nlpshim.src.nlpshim.conversation_test_api.complete_missing_fields → src.koru.wizard.gui.static.wizard.list
  packages.coru.src.coru.ecosystem.sync_python_packages → packages.coru.src.coru.ecosystem._local_package_paths
  packages.coru.src.coru.ecosystem._default_runner → src.koru.wizard.gui.static.wizard.list
  packages.coru.src.coru.ecosystem._detect_running_plugin_ides → src.koruide.ide.detect_running_ides
  packages.coru.src.coru.ecosystem.sync_ecosystem → packages.coru.src.coru.ecosystem.sync_python_packages
  packages.coru.src.coru.ecosystem.sync_ecosystem → packages.coru.src.coru.ecosystem._detect_running_plugin_ides
  packages.coru.src.coru.cli._trace → project.print
  packages.coru.src.coru.cli._trace → packages.coru.src.coru.cli._trace_enabled
  packages.coru.src.coru.cli._current_log_format → packages.coru.src.coru.cli._normalize_log_format
  packages.coru.src.coru.cli._emit_log → packages.coru.src.coru.cli._current_log_format
  packages.coru.src.coru.cli._emit_log → project.print
  packages.coru.src.coru.cli._print_runtime_versions → project.print
  packages.coru.src.coru.cli._print_runtime_versions → packages.coru.src.coru.cli._distribution_version
  packages.coru.src.coru.cli._startup_mode → project.print
  packages.coru.src.coru.cli._autonomous_startup_chain → packages.coru.src.coru.cli._resolve_defaults
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._agent_lane_from_auto_args
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._resolve_defaults
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._terminal_shell_context
  packages.coru.src.coru.cli._run_default_autonomous → project.print
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._print_runtime_versions
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._print_troubleshooting_log_locations
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._repo_root
  packages.coru.src.coru.cli._run_default_autonomous → packages.coru.src.coru.cli._autonomous_startup_chain
  packages.coru.src.coru.cli._running_ide_choices → src.koruide.ide.detect_running_ides
  packages.coru.src.coru.cli._supervisor_project_choices → packages.coru.src.coru.supervisor.registry.load_registry
  packages.coru.src.coru.cli._supervisor_project_choices → packages.coru.src.coru.supervisor.paths.registry_path
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 790f 133046L | python:564,typescript:93,shell:53,yaml:30,json:16,yml:10,kotlin:6,txt:5,toml:4,md:1,javascript:1,properties:1,xml:1 | 2026-06-07
# generated in 0.59s
# CC̅=3.7 | critical:50/5723 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    parse_intent CC=15 (limit:15)
  🟡 CC    _alive_daemon_ide CC=17 (limit:15)
  🟡 CC    _infer_default_ide CC=26 (limit:15)
  🟡 CC    _lane_status_payload CC=19 (limit:15)
  🟡 CC    _format_calibration_probe_report CC=17 (limit:15)
  🟡 CC    _auto_readiness_gate CC=22 (limit:15)
  🟡 CC    _auto_ownership_gate CC=22 (limit:15)
  🟡 CC    _diagnose_lane CC=15 (limit:15)
  🟡 CC    _heuristic_plan CC=16 (limit:15)
  🟡 CC    _execute_plans CC=22 (limit:15)
  🟡 CC    _terminal_shell_context_fallback CC=22 (limit:15)
  🟡 CC    _project_one_session CC=19 (limit:15)
  🟡 CC    collect_problems_from_status CC=19 (limit:15)
  🟡 CC    _collect_plugin_alignment_problems CC=19 (limit:15)
  🟡 CC    _execute_step CC=19 (limit:15)
  🟡 CC    _apply_round_resolution CC=22 (limit:15)
  🟡 CC    cmd_start CC=15 (limit:15)
  🟡 CC    validate_single_calibration CC=20 (limit:15)
  🟡 CC    validate_calibrations CC=16 (limit:15)
  🟡 CC    desktop_uri_control_execute CC=15 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[1821]:
  [1] Src [get_files]: get_files
      PURITY: 100% pure
  [2] Src [main]: main → _normalize_log_format
      PURITY: 100% pure
  [3] Src [resolve_lane_socket]: resolve_lane_socket → resolve_lane_socket_for_os → validate_instance
      PURITY: 100% pure
  [4] Src [__init__]: __init__ → get_nlp2dsl_client
      PURITY: 100% pure
  [5] Src [start]: start
      PURITY: 100% pure
  [6] Src [message]: message → list → escapeHtml
      PURITY: 100% pure
  [7] Src [run_dsl]: run_dsl
      PURITY: 100% pure
  [8] Src [export_trace]: export_trace → list → escapeHtml
      PURITY: 100% pure
  [9] Src [_record]: _record
      PURITY: 100% pure
  [10] Src [from_env]: from_env
      PURITY: 100% pure
  [11] Src [workflow_from_text]: workflow_from_text
      PURITY: 100% pure
  [12] Src [__init__]: __init__ → get_nlp2dsl_client
      PURITY: 100% pure
  [13] Src [parse_intent]: parse_intent → analyze_text_structure → _use_intent_ir
      PURITY: 100% pure
  [14] Src [workflow_plan]: workflow_plan
      PURITY: 100% pure
  [15] Src [parse_conversation_step]: parse_conversation_step → list → escapeHtml
      PURITY: 100% pure
  [16] Src [complete_missing_fields]: complete_missing_fields → list → escapeHtml
      PURITY: 100% pure
  [17] Src [execute_conversation_plan]: execute_conversation_plan
      PURITY: 100% pure
  [18] Src [export_trace]: export_trace
      PURITY: 100% pure
  [19] Src [_default_runner]: _default_runner → list → escapeHtml
      PURITY: 100% pure
  [20] Src [_cmd_exists]: _cmd_exists → _binary_path → _repo_root
      PURITY: 100% pure
  [21] Src [_ide_from_vscode_pid]: _ide_from_vscode_pid
      PURITY: 100% pure
  [22] Src [_vscode_family_env_hint]: _vscode_family_env_hint
      PURITY: 100% pure
  [23] Src [_windsurf_terminal_marker]: _windsurf_terminal_marker
      PURITY: 100% pure
  [24] Src [_koruenv_run_fallback]: _koruenv_run_fallback → _run_with_lane_environment → _run → list → ...(1 more)
      PURITY: 100% pure
  [25] Src [_write_calibration_desktop_oql]: _write_calibration_desktop_oql → _materialize_calibration_desktop_oql → _calibration_desktop_template_path
      PURITY: 100% pure
  [26] Src [_status_failure_ok_to_continue]: _status_failure_ok_to_continue
      PURITY: 100% pure
  [27] Src [_ide_from_vscode_pid]: _ide_from_vscode_pid
      PURITY: 100% pure
  [28] Src [_vscode_family_env_hint]: _vscode_family_env_hint
      PURITY: 100% pure
  [29] Src [_windsurf_terminal_marker]: _windsurf_terminal_marker
      PURITY: 100% pure
  [30] Src [terminal_ide_hint]: terminal_ide_hint → terminal_shell_context → _terminal_shell_context_fallback
      PURITY: 100% pure
  [31] Src [terminal_host_kind]: terminal_host_kind → detect_terminal_host_context → _terminal_ide_from_env_with_source → normalize_ide_id
      PURITY: 100% pure
  [32] Src [for_project]: for_project
      PURITY: 100% pure
  [33] Src [append]: append
      PURITY: 100% pure
  [34] Src [append_many]: append_many
      PURITY: 100% pure
  [35] Src [read_all]: read_all
      PURITY: 100% pure
  [36] Src [read_recent]: read_recent
      PURITY: 100% pure
  [37] Src [for_project]: for_project
      PURITY: 100% pure
  [38] Src [cases]: cases → project_repair_cases → _project_one_session → next → ...(2 more)
      PURITY: 100% pure
  [39] Src [cases_for_lane]: cases_for_lane → aggregate_id_for
      PURITY: 100% pure
  [40] Src [cases_matching_code]: cases_matching_code
      PURITY: 100% pure
  [41] Src [format_llm]: format_llm → format_history_llm → format_case_llm
      PURITY: 100% pure
  [42] Src [format_json]: format_json
      PURITY: 100% pure
  [43] Src [problems_to_payload]: problems_to_payload
      PURITY: 100% pure
  [44] Src [from_dict]: from_dict
      PURITY: 100% pure
  [45] Src [dedupe_problems]: dedupe_problems → _dedupe_problems
      PURITY: 100% pure
  [46] Src [collect_problems_from_manage_report]: collect_problems_from_manage_report → _collect_manage_issue_problems → _problem_from_manage_issue
      PURITY: 100% pure
  [47] Src [collect_problems_from_status]: collect_problems_from_status → _plugin_row_for_ide
      PURITY: 100% pure
  [48] Src [collect_problems_from_drive_result]: collect_problems_from_drive_result → _dedupe_problems
      PURITY: 100% pure
  [49] Src [collect_problems_from_console_logs]: collect_problems_from_console_logs → _dedupe_problems
      PURITY: 100% pure
  [50] Src [run_repair_pipeline]: run_repair_pipeline → _emit_session_started → _emit
      PURITY: 100% pure

LAYERS:
  packages/                       CC̄=4.9    ←in:0  →out:0
  │ !! cli                       4053L  3C  187m  CC=26     ←1
  │ !! pipeline                   879L  2C   32m  CC=22     ←4
  │ !! diagnostics                458L  0C   20m  CC=19     ←1
  │ !! cli                        327L  0C   18m  CC=15     ←0
  │ ecosystem                  225L  2C   11m  CC=14     ←2
  │ http_handlers              199L  0C   16m  CC=9      ←1
  │ cli                        197L  0C    8m  CC=5      ←2
  │ service                    186L  1C   14m  CC=5      ←4
  │ registry                   177L  0C    3m  CC=5      ←2
  │ service                    164L  1C    5m  CC=3      ←1
  │ !! ide_detection              149L  0C    7m  CC=22     ←0
  │ registry                   146L  0C   10m  CC=14     ←5
  │ probe                      136L  0C    8m  CC=13     ←1
  │ !! client                     120L  2C   11m  CC=15     ←2
  │ models                     108L  3C    6m  CC=8      ←0
  │ systemd_unit               105L  0C    4m  CC=9      ←1
  │ !! projector                   99L  0C    4m  CC=19     ←1
  │ lane                        93L  0C    6m  CC=5      ←1
  │ repair_registry             84L  0C    1m  CC=1      ←1
  │ http_server                 83L  1C    5m  CC=2      ←0
  │ conversation_client         82L  2C    6m  CC=9      ←0
  │ query                       80L  1C    8m  CC=5      ←0
  │ conversation_test_api       75L  3C    5m  CC=10     ←0
  │ daemon_ctl                  73L  0C    3m  CC=9      ←1
  │ domain                      64L  5C    0m  CC=0.0    ←0
  │ store                       55L  1C    6m  CC=6      ←0
  │ events                      54L  1C    3m  CC=7      ←2
  │ __init__                    52L  0C    0m  CC=0.0    ←0
  │ socket_path                 47L  0C    2m  CC=8      ←1
  │ paths                       43L  0C    6m  CC=5      ←5
  │ commands                    38L  3C    0m  CC=0.0    ←0
  │ http_util                   36L  0C    3m  CC=5      ←2
  │ editor_cli                  35L  0C    2m  CC=9      ←1
  │ pyproject.toml              27L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              23L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              22L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ koruenv-lane.sh              4L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │
  services/                       CC̄=4.4    ←in:0  →out:0
  │ !! app                        694L  0C   28m  CC=11     ←1
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ app_command_routing         82L  0C    2m  CC=7      ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │ app_bootstrap               34L  0C    2m  CC=1      ←0
  │
  src/                            CC̄=3.9    ←in:0  →out:1
  │ !! scan                      1621L  0C   61m  CC=13     ←7
  │ !! autonomous_cycle          1443L  0C   46m  CC=14     ←1
  │ !! install_manager           1265L  1C   54m  CC=18     ←3
  │ !! autonomous_loop_runner    1256L  1C   56m  CC=12     ←2
  │ !! plugin_installer          1194L  3C   56m  CC=22     ←9
  │ !! autonomous                1032L  0C   64m  CC=4      ←3
  │ !! operator_pipeline         1009L  2C   44m  CC=14     ←0
  │ !! drive_orchestrator         965L  1C   56m  CC=14     ←0
  │ !! ide                        939L  2C   53m  CC=17     ←43
  │ !! ide_reload                 898L  1C   39m  CC=12     ←5
  │ !! autonomous_readiness       895L  3C   36m  CC=19     ←4
  │ !! mcp_server_planfile        839L  0C   28m  CC=14     ←1
  │ !! context                    822L  0C   31m  CC=12     ←7
  │ !! autonomous_startup         812L  3C   37m  CC=16     ←5
  │ !! autonomous_wup             808L  3C   39m  CC=12     ←2
  │ !! code2llm_discovery         752L  1C   31m  CC=13     ←4
  │ !! autonomous_plugin_wait     735L  0C   19m  CC=14     ←1
  │ !! decision_trace             696L  1C   24m  CC=12     ←5
  │ !! autonomous_cycle_skip_conditions   681L  0C   30m  CC=14     ←3
  │ !! handlers_ack               677L  0C   24m  CC=13     ←1
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←1
  │ !! handlers_drive             675L  0C   15m  CC=14     ←0
  │ !! cli_parser                 662L  0C   17m  CC=1      ←0
  │ !! init                       659L  3C   18m  CC=12     ←2
  │ !! scan_phase                 655L  0C   25m  CC=11     ←0
  │ !! doctor_reporting_checks    651L  1C   27m  CC=13     ←0
  │ !! autonomous_cycle_drive_retry   639L  0C   29m  CC=11     ←3
  │ !! autonomous_cycle_chat_activity   634L  0C   20m  CC=11     ←2
  │ !! dashboard_routes           607L  0C   35m  CC=9      ←2
  │ !! self_control               607L  3C   25m  CC=15     ←2
  │ !! ide_doctor_cli             595L  0C   24m  CC=11     ←1
  │ !! command_catalog            575L  1C    8m  CC=9      ←8
  │ !! autonomous_runtime         575L  2C   23m  CC=14     ←4
  │ !! install_plugin_cli         575L  0C   23m  CC=12     ←2
  │ !! configurator               552L  3C   29m  CC=12     ←6
  │ !! autonomous_cycle_orchestrator   541L  2C   11m  CC=14     ←1
  │ !! mcp_provision              533L  0C   28m  CC=10     ←6
  │ !! install_checks             512L  1C   22m  CC=10     ←0
  │ !! autonomous_parser          502L  0C   13m  CC=14     ←2
  │ context_render             496L  1C   21m  CC=14     ←5
  │ shared                     480L  0C   25m  CC=9      ←1
  │ !! desktop_uri                472L  0C   21m  CC=15     ←3
  │ command_picker             469L  2C   25m  CC=14     ←1
  │ ide_work                   465L  0C   17m  CC=12     ←6
  │ runner                     463L  0C   14m  CC=9      ←3
  │ bootstrap                  459L  2C   21m  CC=10     ←3
  │ doctor                     454L  0C   17m  CC=1      ←0
  │ drive                      431L  0C   12m  CC=11     ←0
  │ verification_engine        427L  7C   13m  CC=14     ←1
  │ doctor_chat_control        426L  1C   17m  CC=12     ←2
  │ topology                   425L  1C   18m  CC=9      ←9
  │ observability_dsl          424L  1C   35m  CC=9      ←6
  │ mcp_server_ide             413L  0C   11m  CC=7      ←0
  │ autonomous_cycle_chat_activity_tickets   409L  0C   14m  CC=12     ←1
  │ !! cli_snapshot               407L  0C   10m  CC=16     ←0
  │ env                        399L  0C   19m  CC=12     ←7
  │ !! bridge                     393L  0C   17m  CC=17     ←7
  │ handlers_hello             392L  0C   13m  CC=12     ←0
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ command_scenario           390L  2C   19m  CC=8      ←4
  │ cli_cleaned                389L  0C   24m  CC=11     ←1
  │ invoke_handlers            386L  1C   22m  CC=8      ←0
  │ portal_screencast          383L  1C    7m  CC=10     ←0
  │ autonomous_cycle_post_drive   383L  0C   14m  CC=8      ←0
  │ post_run_verify            381L  2C   16m  CC=14     ←3
  │ local_service              376L  1C   15m  CC=10     ←1
  │ !! agent_backend_runtime      373L  8C   10m  CC=19     ←1
  │ autonomous_operator        368L  0C   20m  CC=8      ←1
  │ orchestrator               367L  1C   15m  CC=11     ←2
  │ doctor_project_health      366L  0C   18m  CC=14     ←0
  │ gc                         364L  2C   13m  CC=11     ←1
  │ server                     358L  1C   16m  CC=8      ←0
  │ autonomous_processes       355L  3C   16m  CC=11     ←3
  │ agents                     354L  1C   17m  CC=14     ←5
  │ env2llm_registry           347L  0C   14m  CC=7      ←4
  │ tree                       342L  5C   19m  CC=10     ←4
  │ cli_command                340L  0C   20m  CC=6      ←0
  │ init_host_environment      337L  0C   18m  CC=14     ←1
  │ handlers                   335L  0C   15m  CC=8      ←4
  │ dashboard_projects         334L  0C   20m  CC=10     ←2
  │ activity_log               329L  0C   14m  CC=10     ←24
  │ lifecycle                  328L  2C   16m  CC=10     ←1
  │ autonomous_cycle_gate      328L  0C   14m  CC=14     ←3
  │ !! tools                      327L  0C   19m  CC=19     ←2
  │ dashboard_tickets          322L  2C   17m  CC=10     ←1
  │ ticket_evidence            322L  3C   17m  CC=9      ←1
  │ doctor_autopilot_debug     317L  1C   13m  CC=10     ←0
  │ gillm_client               316L  1C    5m  CC=5      ←2
  │ strategies.json            315L  0C    0m  CC=0.0    ←0
  │ app                        312L  0C   17m  CC=10     ←1
  │ host_setup                 309L  0C   14m  CC=14     ←2
  │ cli_doctor                 309L  0C   14m  CC=11     ←0
  │ autonomous_cycle_chat_activity_analyzer   307L  0C   18m  CC=11     ←1
  │ detector                   306L  0C   14m  CC=11     ←8
  │ protocol                   305L  3C   16m  CC=12     ←7
  │ autonomous_diagnostics     305L  0C    9m  CC=13     ←1
  │ !! calibration_validator      304L  0C    4m  CC=20     ←1
  │ !! calibrate_cli              304L  0C    9m  CC=21     ←0
  │ tagi_integration           302L  2C   13m  CC=13     ←2
  │ structured_report          301L  1C    8m  CC=13     ←1
  │ local_manager_state        292L  4C   21m  CC=14     ←0
  │ wizard.js                  292L  0C   38m  CC=13     ←98
  │ queue_cli_helpers          290L  0C   10m  CC=9      ←1
  │ autonomous_daemon          287L  0C   10m  CC=10     ←3
  │ autonomous_plugin          287L  0C   19m  CC=12     ←4
  │ control_commands           286L  0C   12m  CC=12     ←7
  │ runners                    286L  0C   12m  CC=12     ←2
  │ !! lane_context               285L  1C   11m  CC=24     ←3
  │ doctor_autopilot_checks    281L  0C   22m  CC=13     ←1
  │ autonomous_drive_retry_policy   281L  0C    9m  CC=13     ←1
  │ cli_parser                 281L  0C    8m  CC=2      ←0
  │ cli_main                   281L  0C    6m  CC=14     ←0
  │ !! ide_control_cli            279L  0C   14m  CC=19     ←1
  │ plugin_router              278L  3C   18m  CC=13     ←0
  │ cli_tagi                   278L  0C   12m  CC=11     ←0
  │ cli_direct_drive           278L  0C   13m  CC=7      ←0
  │ git_cli                    274L  0C   20m  CC=9      ←0
  │ environment_profile        271L  5C   11m  CC=9      ←4
  │ autonomous_process_guard   271L  3C   16m  CC=10     ←1
  │ browser_getdisplay         266L  1C   14m  CC=8      ←2
  │ integrations               264L  1C    2m  CC=4      ←4
  │ policy                     262L  1C   10m  CC=9      ←3
  │ agent_backends             259L  3C   11m  CC=11     ←3
  │ client                     257L  1C   10m  CC=10     ←1
  │ decision_engine            257L  4C   11m  CC=11     ←2
  │ autonomous_auto_pipeline   255L  2C    9m  CC=9      ←0
  │ cli_queue                  255L  0C    7m  CC=12     ←0
  │ base                       254L  9C   10m  CC=2      ←1
  │ local_manager_client       252L  2C   15m  CC=7      ←4
  │ dashboard_serve_utils      251L  1C   19m  CC=7      ←3
  │ doctor_plugin_console      251L  0C   10m  CC=11     ←0
  │ environment                250L  3C    6m  CC=14     ←5
  │ capture_mss                248L  1C   12m  CC=14     ←5
  │ decision_arbiter           241L  2C    9m  CC=9      ←1
  │ ide_install                241L  1C    6m  CC=9      ←1
  │ dashboard_serve            240L  1C   10m  CC=6      ←1
  │ doctor_constants           237L  1C    0m  CC=0.0    ←0
  │ planning_llm               235L  0C    7m  CC=5      ←0
  │ autonomous_up              234L  2C    5m  CC=7      ←0
  │ cli                        232L  0C   12m  CC=12     ←0
  │ mcp_server_env2llm         231L  0C   10m  CC=3      ←1
  │ obs_websocket              231L  1C   15m  CC=11     ←1
  │ interface_registry         230L  3C   14m  CC=9      ←7
  │ dev_sync                   229L  1C    9m  CC=11     ←0
  │ autonomous_onboarding      227L  1C   10m  CC=10     ←0
  │ gillm_recovery             227L  0C    3m  CC=2      ←4
  │ planning_llm_prompts       222L  0C    6m  CC=8      ←1
  │ mcp_server_desktop_uri     220L  0C    8m  CC=1      ←0
  │ event_store                220L  4C   17m  CC=10     ←3
  │ autonomous_cycle_config    219L  0C    6m  CC=10     ←2
  │ autonomous_checkpoint      217L  0C   11m  CC=9      ←4
  │ ide                        216L  1C    6m  CC=10     ←1
  │ task_intake                214L  3C   13m  CC=4      ←1
  │ scan_ticket_emission       211L  0C    6m  CC=11     ←1
  │ !! status                     211L  0C    7m  CC=20     ←0
  │ command_telemetry          210L  1C   11m  CC=13     ←0
  │ ide_client                 210L  2C   12m  CC=12     ←1
  │ library                    207L  0C   19m  CC=9      ←1
  │ autonomous_plugin_runtime   203L  0C   10m  CC=11     ←2
  │ gate                       202L  1C    5m  CC=12     ←1
  │ cli_topology               196L  0C    9m  CC=5      ←0
  │ templates                  194L  1C   12m  CC=9      ←1
  │ runtime_insights           192L  0C    7m  CC=9      ←1
  │ handlers_plugin_event      191L  1C    9m  CC=7      ←0
  │ dashboard                  190L  0C   10m  CC=5      ←2
  │ server                     190L  1C    8m  CC=9      ←1
  │ scan_dedupe_policy         190L  0C    8m  CC=13     ←1
  │ models                     190L  2C    6m  CC=8      ←0
  │ redup_integration          188L  0C   10m  CC=3      ←2
  │ ide_operator_guidance      184L  0C    8m  CC=14     ←5
  │ openapi                    183L  0C    1m  CC=2      ←1
  │ cli_task                   183L  0C    5m  CC=11     ←0
  │ diagnostics                175L  0C    8m  CC=8      ←2
  │ events                     174L  1C   11m  CC=7      ←1
  │ llm_reflect                173L  1C    5m  CC=8      ←2
  │ cli                        173L  0C    5m  CC=2      ←6
  │ queue_phase                170L  0C    6m  CC=11     ←0
  │ autonomous_cli_config      168L  0C   11m  CC=10     ←0
  │ chat_history               166L  1C    6m  CC=13     ←2
  │ handoff                    166L  0C    2m  CC=11     ←0
  │ command_catalog_store      165L  1C   13m  CC=10     ←3
  │ dashboard_config           164L  1C   13m  CC=10     ←1
  │ application                164L  2C   11m  CC=3      ←0
  │ ticket                     164L  0C    8m  CC=10     ←8
  │ doctor_runtime_checks      163L  0C    7m  CC=11     ←2
  │ project                    160L  1C   11m  CC=7      ←1
  │ cli                        159L  0C   10m  CC=3      ←0
  │ project_pipeline           158L  0C    5m  CC=11     ←7
  │ audit                      154L  2C    6m  CC=6      ←1
  │ analyzer                   154L  1C   12m  CC=12     ←0
  │ doctor_cli                 152L  0C    9m  CC=8      ←1
  │ daemon_cli                 151L  0C    7m  CC=11     ←0
  │ ide_chat                   149L  1C    6m  CC=9      ←0
  │ semcod_tools               149L  1C    4m  CC=7      ←5
  │ providers_cli              148L  0C   10m  CC=13     ←1
  │ sllm_bridge                148L  0C   12m  CC=3      ←7
  │ git_attribution            146L  1C    5m  CC=9      ←1
  │ config                     146L  1C    1m  CC=11     ←0
  │ vscode_family              144L  1C    4m  CC=9      ←0
  │ strategy_prompt            142L  0C    3m  CC=6      ←2
  │ doctor_autonomous_streams   142L  0C    7m  CC=9      ←0
  │ autonomous_cycle_chat_activity_text   138L  0C    6m  CC=12     ←0
  │ replay_parser              137L  0C   13m  CC=5      ←2
  │ local_manager              136L  1C    6m  CC=5      ←1
  │ integration_ledger         135L  0C    4m  CC=5      ←3
  │ cli_replay                 135L  0C    4m  CC=8      ←0
  │ base                       134L  4C   10m  CC=4      ←0
  │ task_ticket                131L  0C    6m  CC=6      ←1
  │ loop                       131L  3C    4m  CC=12     ←2
  │ observability_writer       131L  0C    9m  CC=8      ←9
  │ replay_builders            131L  0C    9m  CC=3      ←3
  │ llx                        128L  1C    4m  CC=14     ←3
  │ cli_parser                 125L  0C    4m  CC=7      ←1
  │ scan_render                125L  0C    5m  CC=8      ←1
  │ autonomous_cycle_chat_activity_config   125L  0C    9m  CC=3      ←0
  │ autonomous_submit_strategy   123L  0C    7m  CC=11     ←3
  │ doctor_plugin_bundle       123L  0C    6m  CC=8      ←0
  │ run_log                    123L  1C    7m  CC=4      ←1
  │ observability_events       122L  0C   10m  CC=3      ←5
  │ metadata                   121L  0C    9m  CC=5      ←2
  │ cli_events                 121L  0C    3m  CC=7      ←0
  │ application                120L  2C    4m  CC=12     ←0
  │ prompters                  120L  2C    9m  CC=11     ←0
  │ mcp_server_dispatch        119L  0C    7m  CC=6      ←1
  │ cli_init                   119L  0C    3m  CC=7      ←0
  │ prompts                    119L  1C    2m  CC=10     ←0
  │ application                119L  2C    6m  CC=5      ←0
  │ portal_capture             118L  1C    2m  CC=8      ←4
  │ ports                      118L  5C    4m  CC=1      ←0
  │ cycle_trace                118L  0C    3m  CC=9      ←1
  │ replay_execution           117L  0C    9m  CC=5      ←1
  │ dashboard_html             116L  0C    3m  CC=4      ←1
  │ registry                   116L  1C    6m  CC=9      ←3
  │ cli_gate                   116L  0C    2m  CC=5      ←0
  │ task_dedupe                116L  0C   10m  CC=12     ←1
  │ heal                       116L  1C    3m  CC=5      ←1
  │ loop                       115L  0C    1m  CC=14     ←4
  │ replay_handlers            113L  2C    5m  CC=3      ←0
  │ session                    112L  2C    8m  CC=4      ←0
  │ planning_llm_parsing       111L  0C    7m  CC=7      ←1
  │ defaults                   109L  0C    2m  CC=1      ←2
  │ doctor_project_checks      108L  0C    4m  CC=7      ←0
  │ nlp2oql_bridge             107L  0C    5m  CC=4      ←1
  │ contexts                   107L  8C    0m  CC=0.0    ←0
  │ dashboard_state            106L  0C    4m  CC=7      ←3
  │ ide_router                 105L  1C    2m  CC=10     ←4
  │ cli_auto                   105L  0C    5m  CC=14     ←1
  │ cli_trace                  105L  0C    3m  CC=11     ←0
  │ __init__                   104L  0C    1m  CC=1      ←0
  │ runtime                    104L  0C    5m  CC=2      ←5
  │ dotenv_loader              104L  0C    3m  CC=7      ←2
  │ cycle_finalize             104L  0C    1m  CC=4      ←1
  │ web-app.json               104L  0C    0m  CC=0.0    ←0
  │ systemd_cli                103L  0C    4m  CC=6      ←0
  │ testql_bridge              101L  0C    5m  CC=7      ←1
  │ storage                    100L  0C    5m  CC=6      ←2
  │ fallback                   100L  1C    1m  CC=1      ←0
  │ __init__                    97L  0C    2m  CC=2      ←0
  │ drive_phase                 97L  0C    2m  CC=1      ←0
  │ __init__                    97L  0C    3m  CC=9      ←0
  │ ide_control                 95L  1C    2m  CC=3      ←1
  │ __init__                    95L  2C    5m  CC=3      ←6
  │ locking                     94L  0C    5m  CC=5      ←3
  │ config                      94L  1C    3m  CC=4      ←5
  │ mcp_server                  94L  0C    0m  CC=0.0    ←0
  │ watch                       93L  0C    6m  CC=9      ←1
  │ replay_quick_actions        93L  0C    4m  CC=8      ←1
  │ cli_scan                    92L  0C    2m  CC=3      ←0
  │ application                 92L  2C    4m  CC=5      ←0
  │ cli_self                    91L  1C    4m  CC=5      ←0
  │ cli                         90L  0C    4m  CC=11     ←0
  │ base                        90L  4C    6m  CC=5      ←4
  │ events                      90L  0C    2m  CC=8      ←14
  │ autonomous_resources        90L  0C    1m  CC=4      ←0
  │ openrouter                  89L  1C    2m  CC=5      ←3
  │ transport                   88L  0C    4m  CC=9      ←2
  │ autoloop_cli                88L  0C    4m  CC=8      ←0
  │ types                       88L  5C    1m  CC=2      ←0
  │ agent_cli_helpers           87L  0C    3m  CC=10     ←1
  │ cli_gc                      87L  0C    2m  CC=1      ←0
  │ codex                       86L  1C    5m  CC=6      ←0
  │ dashboard                   86L  0C    8m  CC=3      ←1
  │ browser_capture             86L  0C    5m  CC=10     ←1
  │ cursor                      86L  1C    3m  CC=1      ←0
  │ envelope                    85L  1C    4m  CC=3      ←4
  │ cli_agent                   85L  0C    3m  CC=3      ←0
  │ autonomous_cycle_drive_outcome    85L  0C    1m  CC=9      ←1
  │ mcp_server_nlp2oql          84L  0C    3m  CC=1      ←0
  │ drive_repair_policy         84L  1C    3m  CC=6      ←1
  │ mcp_server_runtime          83L  0C    6m  CC=1      ←1
  │ sleep_phase                 83L  0C    1m  CC=4      ←1
  │ registry                    82L  0C    5m  CC=4      ←1
  │ doctor_runner               82L  0C    3m  CC=4      ←2
  │ gc_cli_helpers              81L  0C    5m  CC=12     ←1
  │ env_flags                   81L  0C    4m  CC=5      ←3
  │ mesh                        79L  0C    5m  CC=8      ←2
  │ cli_runtime_context         79L  0C    3m  CC=14     ←0
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ scan_types                  78L  3C    3m  CC=2      ←1
  │ manage                      78L  0C    1m  CC=11     ←0
  │ base                        78L  5C    3m  CC=4      ←0
  │ jetbrains                   78L  1C    0m  CC=0.0    ←0
  │ enums                       78L  3C    0m  CC=0.0    ←0
  │ agent                       76L  0C    5m  CC=11     ←1
  │ autonomous_plugin_lifecycle    76L  1C    1m  CC=9      ←1
  │ application                 76L  2C    4m  CC=3      ←0
  │ mcp_server_testql           75L  0C    3m  CC=2      ←0
  │ dashboard_observability     75L  0C    3m  CC=7      ←1
  │ cli                         75L  0C    4m  CC=5      ←0
  │ topology_cli                75L  1C    4m  CC=8      ←1
  │ application                 74L  2C    4m  CC=3      ←0
  │ !! read_model                  74L  1C    2m  CC=24     ←1
  │ cli_strategy                73L  0C    1m  CC=9      ←0
  │ tail_cli                    73L  0C    4m  CC=6      ←0
  │ server                      73L  0C    3m  CC=4      ←1
  │ cli_serve                   72L  0C    2m  CC=1      ←0
  │ shell_evidence              72L  0C    2m  CC=7      ←1
  │ planning_llm_types          71L  5C    5m  CC=1      ←0
  │ transform                   70L  0C    4m  CC=12     ←2
  │ emitter                     70L  1C    5m  CC=6      ←4
  │ event_log_projection        70L  2C    5m  CC=6      ←0
  │ capture                     69L  1C    4m  CC=2      ←3
  │ __init__                    69L  5C    0m  CC=0.0    ←0
  │ topology_post               68L  0C    1m  CC=14     ←1
  │ store_persistence           68L  0C    4m  CC=8      ←1
  │ antigravity                 68L  1C    3m  CC=1      ←0
  │ application                 68L  2C    3m  CC=4      ←0
  │ windsurf                    67L  1C    3m  CC=1      ←0
  │ local_manager               67L  0C    2m  CC=2      ←1
  │ heuristics                  67L  0C    3m  CC=6      ←2
  │ application                 66L  2C    3m  CC=1      ←0
  │ vscode                      65L  1C    3m  CC=1      ←0
  │ env_config                  65L  0C    3m  CC=1      ←1
  │ cli_bootstrap               65L  0C    2m  CC=5      ←0
  │ ollama                      64L  1C    4m  CC=2      ←0
  │ wup_testql_compat           64L  0C    4m  CC=5      ←0
  │ cli_tools                   64L  0C    2m  CC=7      ←0
  │ __init__                    64L  5C    0m  CC=0.0    ←0
  │ dashboard_http              63L  1C    6m  CC=4      ←0
  │ protocol                    62L  2C    2m  CC=3      ←2
  │ doctor_render               62L  0C    3m  CC=8      ←1
  │ cli_agent_backends          61L  0C    1m  CC=8      ←1
  │ screencast_session          60L  0C    5m  CC=7      ←2
  │ store                       60L  0C    4m  CC=6      ←2
  │ dashboard_runtime           59L  0C    4m  CC=5      ←1
  │ replay_types                59L  3C    2m  CC=2      ←0
  │ planning_llm_budget         59L  1C    7m  CC=3      ←1
  │ zed                         59L  1C    0m  CC=0.0    ←0
  │ env                         58L  0C    7m  CC=5      ←9
  │ client                      58L  1C    7m  CC=6      ←0
  │ policy_decision             58L  1C    3m  CC=3      ←0
  │ socket                      57L  0C    2m  CC=7      ←12
  │ client_helpers              57L  0C    2m  CC=4      ←1
  │ dashboard_plugin_logs       56L  0C    5m  CC=5      ←0
  │ cli_commands                56L  0C    3m  CC=3      ←1
  │ planfile_ticket_note        55L  0C    2m  CC=5      ←2
  │ library.json                55L  0C    0m  CC=0.0    ←0
  │ ml-research.json            55L  0C    0m  CC=0.0    ←0
  │ cli-tool.json               55L  0C    0m  CC=0.0    ←0
  │ mss                         54L  1C    4m  CC=8      ←0
  │ batch                       54L  1C    5m  CC=2      ←0
  │ registry                    54L  0C    4m  CC=3      ←2
  │ cli_local_serve             53L  0C    2m  CC=1      ←0
  │ cli_ide_router              53L  0C    1m  CC=3      ←0
  │ replay_actions              53L  0C    0m  CC=0.0    ←0
  │ mcp_server_transport        52L  0C    3m  CC=7      ←1
  │ scaling                     52L  0C    3m  CC=6      ←5
  │ dashboard_parse             52L  0C    3m  CC=6      ←2
  │ prompts                     52L  0C    1m  CC=2      ←1
  │ gpt                         51L  1C    4m  CC=1      ←0
  │ claude                      51L  1C    4m  CC=1      ←0
  │ vscodium                    51L  1C    3m  CC=1      ←0
  │ doctor_models               51L  2C    3m  CC=2      ←0
  │ log_contract                51L  0C    2m  CC=5      ←5
  │ state                       51L  1C    0m  CC=0.0    ←0
  │ capture_probe               50L  0C    2m  CC=7      ←1
  │ shutdown                    50L  0C    1m  CC=3      ←0
  │ __init__                    50L  0C    0m  CC=0.0    ←0
  │ cli_loop                    49L  0C    1m  CC=7      ←0
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ __init__                    48L  5C    0m  CC=0.0    ←0
  │ protocol                    48L  0C    0m  CC=0.0    ←0
  │ __init__                    47L  0C    0m  CC=0.0    ←0
  │ plugin_version              46L  0C    1m  CC=2      ←2
  │ refactor_planfile_handoff    46L  0C    1m  CC=6      ←1
  │ __init__                    46L  3C    0m  CC=0.0    ←0
  │ cli_tools                   45L  1C    5m  CC=3      ←0
  │ task_io                     45L  0C    3m  CC=4      ←2
  │ verify_phase                45L  0C    1m  CC=5      ←0
  │ portal_screenshot           44L  1C    4m  CC=2      ←0
  │ grim                        44L  1C    5m  CC=4      ←0
  │ ide_runtime                 44L  0C    2m  CC=5      ←1
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ event_log_query             43L  1C    2m  CC=5      ←0
  │ __init__                    43L  2C    0m  CC=0.0    ←0
  │ planfile_handoff            42L  0C    2m  CC=2      ←2
  │ cli_parser                  41L  0C    4m  CC=2      ←1
  │ cli_watch                   41L  0C    1m  CC=2      ←0
  │ planning_llm_runtime        41L  1C    5m  CC=3      ←1
  │ registry.json               41L  0C    0m  CC=0.0    ←0
  │ reflection_policy           40L  1C    2m  CC=9      ←1
  │ subprocess_runner           40L  0C    3m  CC=3      ←4
  │ __init__                    40L  0C    0m  CC=0.0    ←0
  │ scan_collection             39L  0C    1m  CC=3      ←0
  │ __init__                    39L  2C    0m  CC=0.0    ←0
  │ __init__                    39L  0C    0m  CC=0.0    ←0
  │ bootstrap                   38L  0C    3m  CC=3      ←2
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ mcp_server_cli              37L  0C    1m  CC=2      ←1
  │ codec                       37L  0C    2m  CC=1      ←2
  │ event_bus                   37L  1C    3m  CC=2      ←0
  │ __init__                    37L  2C    0m  CC=0.0    ←0
  │ __init__                    37L  0C    0m  CC=0.0    ←0
  │ local                       36L  0C    2m  CC=6      ←2
  │ __init__                    36L  3C    0m  CC=0.0    ←0
  │ planfile_queue              36L  0C    0m  CC=0.0    ←0
  │ cli_refactor_planfile_handoff    35L  0C    1m  CC=1      ←0
  │ __init__                    34L  2C    0m  CC=0.0    ←0
  │ dashboard_context           33L  0C    2m  CC=3      ←1
  │ __init__                    33L  0C    1m  CC=4      ←0
  │ __init__                    33L  4C    0m  CC=0.0    ←0
  │ __init__                    33L  2C    0m  CC=0.0    ←0
  │ registry                    32L  0C    2m  CC=1      ←1
  │ tasks                       32L  0C    1m  CC=1      ←9
  │ __init__                    32L  1C    0m  CC=0.0    ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ cli_parser                  31L  0C    1m  CC=1      ←1
  │ cli_context                 31L  0C    1m  CC=2      ←0
  │ ide_status_systemmap        31L  0C    1m  CC=3      ←1
  │ cli_shim_builders           31L  0C    2m  CC=1      ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ utils                       30L  0C    2m  CC=4      ←3
  │ __init__                    30L  3C    0m  CC=0.0    ←0
  │ mcp_server_schema           29L  0C    1m  CC=1      ←0
  │ __init__                    29L  1C    0m  CC=0.0    ←0
  │ __init__                    29L  2C    0m  CC=0.0    ←0
  │ doctor_registry_checks      28L  0C    2m  CC=4      ←0
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
  │ config                      23L  0C    0m  CC=0.0    ←0
  │ dashboard_topology          22L  0C    2m  CC=1      ←1
  │ __init__                    22L  2C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ paths                       21L  0C    4m  CC=1      ←7
  │ utils                       21L  0C    1m  CC=2      ←1
  │ __init__                    21L  1C    0m  CC=0.0    ←0
  │ __init__                    21L  2C    0m  CC=0.0    ←0
  │ autonomous_cycle_bridge     20L  0C    1m  CC=2      ←0
  │ autonomous_cycle_common     20L  1C    2m  CC=3      ←10
  │ __init__                    20L  1C    0m  CC=0.0    ←0
  │ __init__                    20L  2C    0m  CC=0.0    ←0
  │ domain_event                19L  1C    1m  CC=2      ←0
  │ __init__                    19L  0C    0m  CC=0.0    ←0
  │ injector                    19L  0C    0m  CC=0.0    ←0
  │ os_injector                 19L  0C    0m  CC=0.0    ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ autonomous_diag_markers     16L  0C    1m  CC=1      ←3
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ injector_errors             16L  0C    0m  CC=0.0    ←0
  │ injector                    16L  0C    0m  CC=0.0    ←0
  │ os_injector                 16L  0C    0m  CC=0.0    ←0
  │ injector_backends           16L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←2
  │ __init__                    14L  1C    0m  CC=0.0    ←0
  │ __init__                    14L  1C    0m  CC=0.0    ←0
  │ task_models                 13L  1C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    11L  0C    0m  CC=0.0    ←0
  │ drive_policy                11L  0C    0m  CC=0.0    ←0
  │ startup_phase               10L  0C    1m  CC=1      ←1
  │ client                      10L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ audit                        9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ cli_ide                      7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
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
  │ cli                          0L  0C   16m  CC=8      ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=2.8    ←in:0  →out:76  !! split
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ scaffold-ide-plugin        310L  0C    7m  CC=7      ←0
  │ write-ide-plugin-tests     261L  0C    3m  CC=3      ←0
  │ planfile-sync-todo         251L  0C   12m  CC=14     ←0
  │ koru-pytest.sh             247L  0C    6m  CC=0.0    ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ sync-plugin-version        149L  0C    4m  CC=7      ←0
  │ sync-plugin-build          136L  0C    6m  CC=13     ←0
  │ koru-semcod-gates.sh       135L  0C    2m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←0
  │ !! e2e_envmap_koru            128L  0C    2m  CC=22     ←0
  │ sync-vscode-plugin-version   125L  0C    6m  CC=2      ←0
  │ koru-autopilot-lanes.sh    125L  0C    5m  CC=0.0    ←0
  │ koru-queue-diagnose.sh     124L  0C    0m  CC=0.0    ←0
  │ koru-soak-stop.sh          123L  0C    5m  CC=0.0    ←0
  │ validate_testql_conversations   109L  0C    5m  CC=12     ←0
  │ sync-plugin-shared         108L  0C    2m  CC=7      ←0
  │ koru-soak-status.sh        100L  0C    6m  CC=0.0    ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ bump_version                94L  0C    5m  CC=5      ←0
  │ docker-ide-matrix.sh        92L  0C    2m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←0
  │ docker-ide-matrix-entrypoint.sh    75L  0C    1m  CC=0.0    ←0
  │ !! run_testql_conversations    68L  0C    2m  CC=16     ←0
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │ test-browser-stack.sh       48L  0C    0m  CC=0.0    ←0
  │ koru-soak-start.sh          39L  0C    1m  CC=0.0    ←0
  │ simulate-multi-lane-docker.sh    31L  0C    0m  CC=0.0    ←0
  │ activate-koru-dev.sh        18L  0C    0m  CC=0.0    ←0
  │ koru-from-repo.sh           10L  0C    0m  CC=0.0    ←0
  │ koru-autopilot-lane.sh      10L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=2.4    ←in:0  →out:0
  │ !! bridge-submit.ts           992L  1C   72m  CC=13     ←1
  │ !! bridge-paste.ts            781L  1C   59m  CC=26     ←0
  │ !! bridge-submit-focus.test.ts   581L  0C   30m  CC=3      ←0
  │ !! bridge-fastpath.ts         511L  1C   26m  CC=7      ←0
  │ probe-ladder.ts            452L  3C   45m  CC=12     ←0
  │ probe-ladder.ts            432L  3C   43m  CC=10     ←0
  │ chat-history-watcher.test.ts   416L  0C   35m  CC=5      ←0
  │ bridge-network.ts          411L  1C   56m  CC=10     ←4
  │ cursor.test.ts             411L  0C   31m  CC=8      ←0
  │ bridge-focus-strategy.ts   410L  1C   31m  CC=9      ←0
  │ chat-history-watcher.test.ts   355L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ cursor.ts                  328L  0C   19m  CC=12     ←0
  │ probe-ladder.test.ts       315L  0C   38m  CC=5      ←0
  │ KoruAutopilotService.kt    264L  1C    6m  CC=0.0    ←0
  │ ack-payload.ts             260L  0C   31m  CC=12     ←3
  │ bridge-focus-core.ts       239L  1C   33m  CC=5      ←21
  │ package.json               213L  0C    0m  CC=0.0    ←0
  │ package.json               202L  0C    0m  CC=0.0    ←0
  │ autopilot-bridge.ts        200L  1C   20m  CC=8      ←7
  │ chat-history-watcher.ts    197L  2C   11m  CC=10     ←0
  │ package.json               194L  0C    0m  CC=0.0    ←0
  │ package.json               193L  0C    0m  CC=0.0    ←0
  │ step-decisions.ts          192L  1C   20m  CC=9      ←0
  │ package.json               188L  0C    0m  CC=0.0    ←0
  │ !! bridge-ack.ts              186L  1C   12m  CC=15     ←0
  │ step-decisions.test.ts     176L  0C   14m  CC=2      ←0
  │ step-decisions.test.ts     162L  0C   12m  CC=2      ←0
  │ cursor-bubble-adapter.ts   159L  1C   21m  CC=11     ←14
  │ bridge-helpers.ts          150L  0C   17m  CC=9      ←0
  │ step-decisions.test.ts     148L  0C   12m  CC=2      ←0
  │ vscode-chat-session-adapter.ts   146L  2C   22m  CC=10     ←0
  │ command-catalog.ts         136L  1C    7m  CC=6      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ dispatch-plan.test.ts      118L  0C   12m  CC=4      ←0
  │ ide-strategy.ts            117L  2C    0m  CC=0.0    ←0
  │ probe-ladder.test.ts       115L  0C   16m  CC=3      ←0
  │ vscodium.test.ts           114L  0C   14m  CC=3      ←0
  │ ChatInjector.kt            112L  0C    1m  CC=0.0    ←0
  │ windsurf.ts                108L  0C    8m  CC=6      ←0
  │ vscodium.ts                100L  0C   11m  CC=3      ←0
  │ probe-ladder.test.ts        93L  0C   14m  CC=3      ←0
  │ bridge-watcher.ts           91L  1C   10m  CC=10     ←0
  │ bridge-focus.ts             82L  1C    9m  CC=6      ←0
  │ vscode.ts                   81L  0C   11m  CC=7      ←0
  │ bridge-config.ts            80L  1C    7m  CC=9      ←0
  │ bridge-commands.ts          77L  1C   16m  CC=7      ←0
  │ probe-ladder.test.ts        77L  0C   10m  CC=2      ←0
  │ socketPath.ts               75L  0C   15m  CC=10     ←0
  │ bridge-base-class.ts        69L  1C   10m  CC=3      ←0
  │ probe-ladder.test.ts        69L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     69L  0C    7m  CC=2      ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ antigravity.ts              68L  0C    8m  CC=5      ←0
  │ command-catalog.test.ts     65L  0C    6m  CC=2      ←0
  │ bridge-base.ts              64L  1C    6m  CC=5      ←0
  │ ide-control-strategy.ts     64L  1C    2m  CC=4      ←0
  │ registry.ts                 63L  0C    7m  CC=6      ←0
  │ extension-wrapper.ts        57L  2C    3m  CC=4      ←0
  │ index.ts                    57L  0C    0m  CC=0.0    ←0
  │ command-catalog.test.ts     53L  0C    6m  CC=2      ←0
  │ extension.ts                53L  0C    6m  CC=7      ←0
  │ ack-payload.test.ts         52L  0C    7m  CC=4      ←0
  │ version-reconnect.test.ts    52L  0C    4m  CC=2      ←0
  │ build.gradle.kts            49L  0C    4m  CC=0.0    ←0
  │ extension.ts                47L  0C    3m  CC=1      ←0
  │ registry.ts                 45L  0C    7m  CC=6      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←1
  │ extension.ts                42L  0C    3m  CC=1      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ extension.ts                40L  0C    3m  CC=1      ←0
  │ antigravity-fastpath.test.ts    40L  0C    8m  CC=2      ←0
  │ antigravity-fastpath.test.ts    39L  0C    8m  CC=2      ←0
  │ host-click-submit.test.ts    39L  0C    6m  CC=2      ←0
  │ host-click-submit.ts        35L  0C    7m  CC=6      ←0
  │ submit-match.ts             35L  0C    8m  CC=10     ←0
  │ extension.ts                34L  0C    3m  CC=1      ←0
  │ types.ts                    33L  1C    0m  CC=0.0    ←0
  │ SocketPath.kt               33L  0C    0m  CC=0.0    ←0
  │ chat-history-types.ts       32L  3C    0m  CC=0.0    ←0
  │ cursor-composer-paste.ts    31L  0C    5m  CC=4      ←0
  │ chat-history-adapters.ts    31L  0C    1m  CC=2      ←0
  │ chat-history-paths.ts       29L  0C    5m  CC=4      ←0
  │ dispatch-plan.ts            26L  1C    1m  CC=7      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ plugin.xml                  24L  0C    0m  CC=0.0    ←0
  │ version-reconnect.ts        22L  0C    4m  CC=7      ←0
  │ operator-hints.ts           22L  0C    4m  CC=2      ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=3      ←0
  │ unsupported-chat-adapter.ts    19L  1C    2m  CC=1      ←0
  │ antigravity-fastpath.ts     18L  0C    2m  CC=3      ←0
  │ extension.test.ts           18L  0C    2m  CC=2      ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │ vscodium-host.ts            10L  0C    2m  CC=5      ←0
  │ KoruAutopilotReconnectAction.kt    10L  1C    0m  CC=0.0    ←0
  │ package.json                10L  0C    0m  CC=0.0    ←0
  │ settings.gradle.kts          8L  0C    2m  CC=0.0    ←0
  │ bridge-handle.ts             8L  1C    0m  CC=0.0    ←0
  │ index.ts                     8L  0C    0m  CC=0.0    ←0
  │ gradle.properties            6L  0C    0m  CC=0.0    ←0
  │ cursor-bubble-adapter.ts     1L  0C    0m  CC=0.0    ←0
  │ vscode-chat-session-adapter.ts     1L  0C    0m  CC=0.0    ←0
  │ chat-history-watcher.ts      1L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=2.2    ←in:0  →out:12  !! split
  │ bootstrap.planfile.yaml    425L  0C    0m  CC=0.0    ←0
  │ run.sh                     121L  0C    3m  CC=0.0    ←1
  │ remote_orchestration_demo    69L  0C    1m  CC=9      ←0
  │ run-e2e.sh                  43L  0C    0m  CC=0.0    ←0
  │ gitlab-ci.example.yml       41L  0C    0m  CC=0.0    ←0
  │ docker-compose-remote-mesh.yml    38L  0C    0m  CC=0.0    ←0
  │ browser-dom.testql.toon.yaml    30L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      21L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      19L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      19L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      15L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ run-docker.sh                7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │
  docker/                         CC̄=2.2    ←in:0  →out:0
  │ smoke                      141L  0C    8m  CC=4      ←0
  │ Dockerfile                  61L  0C    0m  CC=0.0    ←0
  │ run.sh                      58L  0C    0m  CC=0.0    ←0
  │ entrypoint-x11.sh           35L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=2.0    ←in:0  →out:0
  │ !! tree.txt                  2722L  0C    0m  CC=0.0    ←0
  │ !! planfile.yaml             1331L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               922L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  531L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             258L  0C    0m  CC=0.0    ←0
  │ gillm_defs.txt             195L  0C    0m  CC=0.0    ←0
  │ Makefile                   191L  0C    0m  CC=0.0    ←0
  │ koru.yaml                  150L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ project.sh                 140L  0C    1m  CC=0.0    ←112
  │ wup.yaml                   113L  0C    0m  CC=0.0    ←0
  │ wup-shell-only.yaml        110L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ sllm_defs.txt               45L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
  │ check_dups                  27L  0C    1m  CC=4      ←0
  │ package.json                25L  0C    0m  CC=0.0    ←0
  │ .pretest.yml                17L  0C    0m  CC=0.0    ←0
  │ nlp2uri.yaml                 8L  0C    0m  CC=0.0    ←0
  │ output.txt                   3L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │ coverage.json                1L  0C    0m  CC=0.0    ←0
  │
  schemas/                        CC̄=0.0    ←in:0  →out:0
  │ koru-stdio-event.schema.json    16L  0C    0m  CC=0.0    ←0
  │
  docs/                           CC̄=0.0    ←in:0  →out:0
  │ ide-command-api-map.yaml   425L  0C    0m  CC=0.0    ←0
  │ koru-interface-registry.yaml   270L  0C    0m  CC=0.0    ←0
  │ ai-tool-registry-2026.yaml   206L  0C    0m  CC=0.0    ←0
  │ install.sh                  88L  0C    0m  CC=0.0    ←0
  │ install.sh                  87L  0C    0m  CC=0.0    ←0
  │ install.sh                  80L  0C    0m  CC=0.0    ←0
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
  │ send-invoice.testql.toon.yaml    39L  0C    0m  CC=0.0    ←0
  │ generated-cli-tests.testql.toon.yaml    19L  0C    0m  CC=0.0    ←0
  │ cli-koru-live.testql.toon.yaml    16L  0C    0m  CC=0.0    ←0
  │ cli-koru.testql.toon.yaml    15L  0C    0m  CC=0.0    ←0
  │ cli-koru_api.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_dsl.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_wup_testql.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │ cli-coru_calibration.testql.toon.yaml     9L  0C    0m  CC=0.0    ←0
  │ mock-llm-replies.yaml        4L  0C    0m  CC=0.0    ←0
  │
  testql-testing/                 CC̄=0.0    ←in:0  →out:0
  │ realtime-health.testql.toon.yaml    11L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     docs/pipeline-design.md                   0L
     src/koru/cli.py                           0L
     src/koruenv/__init__.py                   0L

COUPLING:
                                                      src.koru                        project                    src.koruide                  packages.coru                    src.koruapi  plugins.koru-autopilot-shared                        scripts                 src.koruvision                           koru                src.koruobserve                   src.korumesh                       examples               packages.koruenv               packages.nlpshim                 docker.capture
                       src.koru                             ──                            477                            194                             25                             14                             45                             ←1                             19                             23                             10                             ←2                                                             3                             ←6                                 hub
                        project                           ←477                             ──                            ←26                           ←177                            ←17                                                           ←74                            ←12                             ←7                            ←22                             ←7                            ←12                             ←3                                                            ←1  hub
                    src.koruide                             29                             26                             ──                             ←6                            ←27                              9                                                                                            7                                                                                                                                                                                            hub
                  packages.coru                             30                            177                              6                             ──                                                             4                                                            ←1                                                                                                                                                                                                                           hub
                    src.koruapi                             86                             17                             27                                                            ──                             13                             ←1                              2                              3                                                             3                                                                                            1                                 hub
  plugins.koru-autopilot-shared                            ←45                                                            ←9                             ←4                            ←13                             ──                                                            ←2                                                                                           ←2                                                                                                                              hub
                        scripts                              1                             74                                                                                            1                                                            ──                                                                                                                                                                                                                                                          !! fan-out
                 src.koruvision                              5                             12                                                             1                             ←2                              2                                                            ──                                                             1                              8                                                                                                                          ←4  hub
                           koru                             11                              7                             ←7                                                            ←3                                                                                                                          ──                             ←1                                                                                                                                                             hub
                src.koruobserve                              7                             22                                                                                                                                                                                         7                              1                             ──                              1                                                                                                                          ←1  hub
                   src.korumesh                              2                              7                                                                                           ←3                              2                                                             2                                                             1                             ──                                                                                                                              hub
                       examples                                                            12                                                                                                                                                                                                                                                                                                                    ──                                                                                               !! fan-out
               packages.koruenv                              3                              3                                                                                                                                                                                                                                                                                                                                                   ──                                                              
               packages.nlpshim                              6                                                                                                                          ←1                                                                                                                                                                                                                                                                                     ──                               
                 docker.capture                                                             1                                                                                                                                                                                         4                                                             1                                                                                                                                                         ──
  CYCLES: none
  HUB: plugins.koru-autopilot-shared/ (fan-in=79)
  HUB: src.koruvision/ (fan-in=34)
  HUB: src.korumesh/ (fan-in=12)
  HUB: src.koruide/ (fan-in=227)
  HUB: koru/ (fan-in=34)
  HUB: src.koru/ (fan-in=183)
  HUB: project/ (fan-in=835)
  HUB: src.koruapi/ (fan-in=15)
  HUB: src.koruobserve/ (fan-in=13)
  HUB: packages.coru/ (fan-in=26)
  SMELL: src.koruvision/ fan-out=29 → split needed
  SMELL: src.korumesh/ fan-out=14 → split needed
  SMELL: src.koruide/ fan-out=76 → split needed
  SMELL: koru/ fan-out=18 → split needed
  SMELL: scripts/ fan-out=76 → split needed
  SMELL: src.koru/ fan-out=814 → split needed
  SMELL: src.koruapi/ fan-out=156 → split needed
  SMELL: src.koruobserve/ fan-out=38 → split needed
  SMELL: examples/ fan-out=12 → split needed
  SMELL: packages.coru/ fan-out=217 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 134 groups | 546f 102185L | 2026-06-07

SUMMARY:
  files_scanned: 546
  total_lines:   102185
  dup_groups:    134
  dup_fragments: 325
  saved_lines:   1625
  scan_ms:       5335

HOTSPOTS[7] (files with most duplication):
  src/koru/doctor_chat_control.py  dup=131L  groups=8  frags=8  (0.1%)
  src/koru/doctor_reporting_checks.py  dup=131L  groups=8  frags=8  (0.1%)
  src/koru/cli_cleaned.py  dup=122L  groups=12  frags=15  (0.1%)
  src/koru/ide_adapters/ide_reload.py  dup=87L  groups=4  frags=8  (0.1%)
  src/koru/autopilot/install_checks.py  dup=82L  groups=1  frags=2  (0.1%)
  src/koru/autopilot/cli_parser.py  dup=80L  groups=1  frags=2  (0.1%)
  src/koru/autonomy/phases/scan_phase.py  dup=80L  groups=4  frags=8  (0.1%)

DUPLICATES[134] (ranked by impact):
  [aaa66107e74e8486] ! STRU  _bootstrap_main  L=52 N=2 saved=52 sim=1.00
      src/koru/cli_bootstrap.py:12-63  (_bootstrap_main)
      src/koru/cli_cleaned.py:297-315  (_bootstrap_main)
  [f99ca0c17eccf4a7] ! STRU  _scan_pyqual_report  L=26 N=3 saved=52 sim=1.00
      src/koru/scan.py:1022-1047  (_scan_pyqual_report)
      src/koru/scan.py:1050-1074  (_scan_prefact_report)
      src/koru/scan.py:1103-1128  (_scan_redsl_report)
  [3e6656800e695838] ! STRU  _add_calibrate_parser  L=42 N=2 saved=42 sim=1.00
      src/koru/autopilot/cli_parser.py:193-234  (_add_calibrate_parser)
      src/koru/autopilot/cli_parser.py:237-274  (_add_session_start_parser)
  [6de599a6b460d10e] ! STRU  reuse_window_reload_enabled  L=14 N=4 saved=42 sim=1.00
      src/koru/ide_adapters/ide_reload.py:91-104  (reuse_window_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:107-118  (command_palette_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:121-133  (new_window_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:145-155  (detached_reload_enabled)
  [80ba138d2082ae9d] ! STRU  check_plugin_version_mismatch_issue  L=41 N=2 saved=41 sim=1.00
      src/koru/autopilot/install_checks.py:389-429  (check_plugin_version_mismatch_issue)
      src/koru/autopilot/install_checks.py:432-472  (check_plugin_build_mismatch_issue)
  [48899e7264c0a244] ! STRU  emit_intent  L=6 N=7 saved=36 sim=1.00
      src/koru/observability_events.py:41-46  (emit_intent)
      src/koru/observability_events.py:49-54  (emit_decision)
      src/koru/observability_events.py:57-62  (emit_action)
      src/koru/observability_events.py:65-70  (emit_phase)
      src/koru/observability_events.py:73-78  (emit_verify)
      src/koru/observability_events.py:95-100  (emit_blocker)
      src/koru/observability_events.py:103-108  (emit_next)
  [f75adf4607da007b] ! STRU  build_chat_control_detail_bits  L=33 N=2 saved=33 sim=1.00
      src/koru/doctor_chat_control.py:218-250  (build_chat_control_detail_bits)
      src/koru/doctor_reporting_checks.py:96-128  (_build_chat_control_detail_bits)
  [4b4e0453ad1ecf33] ! STRU  _dsl_main  L=4 N=9 saved=32 sim=1.00
      src/koru/cli.py:60-63  (_dsl_main)
      src/koru/cli.py:66-69  (_api_main)
      src/koru/cli.py:86-89  (_agent_backends_main)
      src/koru/cli_cleaned.py:189-191  (_mcp_serve_main)
      src/koru/cli_cleaned.py:195-197  (_init_ide_main)
      src/koru/cli_cleaned.py:203-205  (_dsl_main)
      src/koru/cli_cleaned.py:207-209  (_api_main)
      src/koru/cli_local_serve.py:48-51  (_local_serve_main)
      src/koru/cli_serve.py:67-70  (_serve_main)
  [8211c31c08c522f1]   STRU  activity_enabled  L=3 N=11 saved=30 sim=1.00
      src/koru/activity_log.py:16-18  (activity_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:90-92  (llm_needs_input_ticket_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:105-107  (llm_needs_input_heuristic_enabled)
      src/koru/autonomous_cycle_chat_activity_config.py:110-112  (chat_intake_ticket_enabled)
      src/koru/autonomous_operator.py:19-21  (_operator_autostart_envmap_enabled)
      src/koru/autonomy/operator_pipeline.py:266-268  (_operator_autostart_server_enabled)
      src/koru/autonomy/planning_llm_runtime.py:10-12  (planning_llm_enabled)
      src/koru/ide_adapters/ide_reload.py:86-88  (auto_reload_enabled)
      src/koru/mcp_provision.py:329-331  (_operator_autostart_mcp_enabled)
      src/koruide/plugin_installer.py:494-496  (_env_reassert_extension_install)
      src/koruide/plugin_installer.py:504-506  (_env_build_local_vsix)
  [b614604b4d5c21f7]   STRU  provision_cursor  L=15 N=3 saved=30 sim=1.00
      src/koru/mcp_provision.py:254-268  (provision_cursor)
      src/koru/mcp_provision.py:271-285  (provision_vscode)
      src/koru/mcp_provision.py:295-309  (provision_zed)
  [f8b0f7f5a0f8ad4c]   STRU  _build_local_serve_parser  L=29 N=2 saved=29 sim=1.00
      src/koru/cli_local_serve.py:17-45  (_build_local_serve_parser)
      src/koruapi/local.py:11-19  (build_local_parser)
  [29fcba90a55ca71d]   STRU  chat_control_result  L=29 N=2 saved=29 sim=1.00
      src/koru/doctor_chat_control.py:288-316  (chat_control_result)
      src/koru/doctor_reporting_checks.py:166-194  (_chat_control_result)
  [53dcede7aa7a316e]   STRU  _register_calibration_command  L=26 N=2 saved=26 sim=1.00
      packages/coru/src/coru/cli.py:3693-3718  (_register_calibration_command)
      packages/coru/src/coru/cli.py:3721-3731  (_register_doctor_command)
  [8b13f2270232bdb8]   EXAC  _finalise_ticket  L=25 N=2 saved=25 sim=1.00
      src/koru/wizard/cli.py:66-90  (_finalise_ticket)
      src/koru/wizard/orchestrator.py:212-236  (_finalise_ticket)
  [1654292a9e444a37]   STRU  _koru_package_version  L=5 N=6 saved=25 sim=1.00
      src/koru/agents.py:82-86  (_koru_package_version)
      src/koru/autonomous_startup.py:39-43  (koru_distribution_version)
      src/koru/cli_cleaned.py:84-88  (_cli_version)
      src/koru/cli_parser.py:17-21  (_cli_version)
      src/koruapi/cli.py:61-65  (_cli_version)
      src/korudsl/cli.py:41-45  (_cli_version)
  [40d1ea5508176900]   STRU  windsurf_chat_column_result  L=23 N=2 saved=23 sim=1.00
      src/koru/doctor_chat_control.py:404-426  (windsurf_chat_column_result)
      src/koru/doctor_reporting_checks.py:333-355  (_windsurf_chat_column_result)
  [750fe07bcaf40496]   STRU  sync_plugins_for_ide  L=21 N=2 saved=21 sim=1.00
      packages/coru/src/coru/ecosystem.py:97-117  (sync_plugins_for_ide)
      packages/coru/src/coru/ecosystem.py:120-130  (sync_manage_fix)
  [5c4792dac892876e]   STRU  _plugin_reconnected_after_wait  L=21 N=2 saved=21 sim=1.00
      src/koru/autonomous_plugin_wait.py:297-317  (_plugin_reconnected_after_wait)
      src/koru/autonomous_plugin_wait.py:351-371  (_plugin_connected_after_fresh_window)
  [ec9cdc5db0b730e6]   STRU  _plugin_package_version  L=7 N=4 saved=21 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:76-82  (_plugin_package_version)
      src/koru/autopilot/install_plugin_cli.py:85-91  (_plugin_package_name)
      src/koruide/plugin_installer.py:198-204  (_plugin_package_version)
      src/koruide/plugin_installer.py:207-213  (_plugin_package_name)
  [62098847ad4d50c2]   EXAC  _stdio_info  L=5 N=5 saved=20 sim=1.00
      src/koru/autonomous.py:201-205  (_stdio_info)
      src/koru/autonomous_checkpoint.py:16-19  (_stdio_info)
      src/koru/autonomous_cycle.py:94-97  (_stdio_info)
      src/koru/autonomous_daemon.py:26-30  (_stdio_info)
      src/koru/autonomous_processes.py:219-223  (_stdio_info)
  [9a275423ff311e44]   STRU  _wup_process_match  L=20 N=2 saved=20 sim=1.00
      src/koru/autonomous_process_guard.py:169-188  (_wup_process_match)
      src/koru/autonomous_processes.py:130-148  (_wup_process_matches_project)
  [9fc6ccb633a9cc1c]   STRU  assess_drive_failure  L=20 N=2 saved=20 sim=1.00
      src/korullm/strategies/codex.py:48-67  (assess_drive_failure)
      src/korullm/strategies/ollama.py:33-52  (assess_drive_failure)
  [e03dedc25160d357]   STRU  _is_topology_enabled  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous.py:377-385  (_is_topology_enabled)
      src/koru/autonomous_cycle_skip_conditions.py:46-54  (_is_topology_enabled)
      src/koru/autonomy/phases/utils.py:11-19  (is_topology_enabled)
  [6fe7a1fb2ee640ce]   STRU  current_head  L=9 N=3 saved=18 sim=1.00
      src/koru/autonomous_checkpoint.py:28-36  (current_head)
      src/koru/autonomous_cycle.py:143-151  (_current_head)
      src/koru/autonomy/phases/utils.py:22-30  (current_head)
  [eb6e04ef39b64936]   STRU  _run_queue_loop  L=18 N=2 saved=18 sim=1.00
      src/koru/autonomous_cycle.py:599-616  (_run_queue_loop)
      src/koru/autonomy/phases/queue_phase.py:51-68  (run_queue_loop)
  [0e509b6ebf83784c]   STRU  autopilot_redrive_cooldown_seconds  L=17 N=2 saved=17 sim=1.00
      src/koru/autonomous_cycle_chat_activity_config.py:19-35  (autopilot_redrive_cooldown_seconds)
      src/koru/autonomous_cycle_chat_activity_config.py:38-54  (autopilot_os_injector_cooldown_seconds)
  [bad3d6a88c27433b]   STRU  _is_bare_invocation  L=17 N=2 saved=17 sim=1.00
      src/koru/cli.py:35-51  (_is_bare_invocation)
      src/koru/cli_cleaned.py:163-179  (_is_bare_invocation)
  [2fbf5aef00d80329]   STRU  _post_workers_register  L=17 N=2 saved=17 sim=1.00
      src/koru/local_service.py:218-234  (_post_workers_register)
      src/koru/local_service.py:237-253  (_post_worker_heartbeat)
  [cb837998f89e21d6]   STRU  _topology_component_toggler  L=15 N=2 saved=15 sim=1.00
      src/koru/cli_topology.py:111-125  (_topology_component_toggler)
      src/koru/cli_topology.py:128-142  (_topology_pipeline_toggler)
  [d793c24c40a62888]   STRU  reload_via_reopen_workspace  L=15 N=2 saved=15 sim=1.00
      src/koru/ide_adapters/ide_reload.py:430-444  (reload_via_reopen_workspace)
      src/koru/ide_adapters/ide_reload.py:447-461  (reload_via_new_window)
  [3b6ae6de406e66ec]   STRU  tool_env2llm_get_registry  L=5 N=4 saved=15 sim=1.00
      src/koruapi/mcp_server_env2llm.py:164-168  (tool_env2llm_get_registry)
      src/koruapi/mcp_server_env2llm.py:189-193  (tool_env2llm_get_desktop)
      src/koruapi/mcp_server_env2llm.py:196-200  (tool_env2llm_list_commands)
      src/koruapi/mcp_server_env2llm.py:203-207  (tool_env2llm_list_uris)
  [681ecd425304ea8f]   EXAC  _installed_extension_dir  L=14 N=2 saved=14 sim=1.00
      packages/coru/src/coru/repair/diagnostics.py:39-52  (_installed_extension_dir)
      packages/coru/src/coru/repair/pipeline.py:48-61  (_installed_extension_dir)
  [52d0f2e451c7e06b]   STRU  update_plugin_version_source  L=14 N=2 saved=14 sim=1.00
      scripts/sync-vscode-plugin-version.py:43-56  (update_plugin_version_source)
      scripts/sync-vscode-plugin-version.py:59-68  (update_package_json)
  [ddb1c2a9a5efa318]   STRU  _should_skip_repeated_create_failed_scan  L=14 N=2 saved=14 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:167-180  (_should_skip_repeated_create_failed_scan)
      src/koru/autonomy/phases/scan_phase.py:183-194  (_should_skip_repeated_duplicate_scan)
  [a548921494239b98]   STRU  _action_install_plugin  L=7 N=3 saved=14 sim=1.00
      src/koru/autopilot/cli_command.py:269-275  (_action_install_plugin)
      src/koru/autopilot/cli_command.py:278-284  (_action_install_plugin_jetbrains)
      src/koru/autopilot/cli_command.py:303-309  (_action_install_unit)
  [457bd73359bd4bcc]   STRU  _open_new_ide_window_for_plugin_build_action  L=14 N=2 saved=14 sim=1.00
      src/koru/autopilot/install_manager.py:788-801  (_open_new_ide_window_for_plugin_build_action)
      src/koru/autopilot/install_manager.py:840-853  (_restart_ide_for_plugin_build_action)
  [ebc5cd8d8ca670d4]   STRU  _peek_project_from_argv  L=7 N=3 saved=14 sim=1.00
      src/koru/cli.py:92-98  (_peek_project_from_argv)
      src/koru/cli_auto.py:13-19  (_peek_project_from_argv)
      src/koru/cli_cleaned.py:211-217  (_peek_project_from_argv)
  [085fbe981d2bd417]   STRU  _maybe_print_project_venv_hint  L=14 N=2 saved=14 sim=1.00
      src/koru/cli.py:101-114  (_maybe_print_project_venv_hint)
      src/koru/cli_cleaned.py:240-250  (_maybe_print_project_venv_hint)
  [c9fe98aa9145404a]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:302-314  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:131-143  (_parse_iso_datetime)
  [6d4d6f4a9db924b5]   STRU  _remember_scan_create_failed_state  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:137-149  (_remember_scan_create_failed_state)
      src/koru/autonomy/phases/scan_phase.py:152-164  (_remember_scan_duplicate_state)
  [af8ce360505c4ae3]   STRU  _should_suggest_wizard  L=13 N=2 saved=13 sim=1.00
      src/koru/cli.py:117-129  (_should_suggest_wizard)
      src/koru/cli_cleaned.py:252-264  (_should_suggest_wizard)
  [9772283ee40ed244]   EXAC  _bridge_hypotheses_payload  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/commands/drive.py:147-158  (_bridge_hypotheses_payload)
      src/koru/ide_doctor_cli.py:92-103  (_bridge_hypotheses_payload)
  [43cf5259d2a755f4]   EXAC  assess_drive_failure  L=12 N=2 saved=12 sim=1.00
      src/korullm/strategies/claude.py:28-39  (assess_drive_failure)
      src/korullm/strategies/gpt.py:28-39  (assess_drive_failure)
  [35ca7615eb80ab15]   EXAC  list_monitors  L=4 N=4 saved=12 sim=1.00
      src/koruvision/providers/cli_tools.py:26-29  (list_monitors)
      src/koruvision/providers/grim.py:21-24  (list_monitors)
      src/koruvision/providers/portal_screencast.py:296-299  (list_monitors)
      src/koruvision/providers/portal_screenshot.py:26-29  (list_monitors)
  [29eeaf16cb9c8025]   STRU  resolve_coru_bin  L=12 N=2 saved=12 sim=1.00
      packages/coru/src/coru/supervisor/systemd_unit.py:21-32  (resolve_coru_bin)
      src/koru/autopilot/systemd_cli.py:20-37  (resolve_koru_bin)
  [8fd129eaadb00d1a]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:9-21  (resolve_xdg_path)
  [25ad78f42f52e0f9]   STRU  chat_control_has_failures  L=12 N=2 saved=12 sim=1.00
      src/koru/doctor_chat_control.py:253-264  (chat_control_has_failures)
      src/koru/doctor_reporting_checks.py:131-142  (_chat_control_has_failures)
  [c4663b0a04b1a8e0]   STRU  windsurf_chat_column_detail_bits  L=12 N=2 saved=12 sim=1.00
      src/koru/doctor_chat_control.py:390-401  (windsurf_chat_column_detail_bits)
      src/koru/doctor_reporting_checks.py:319-330  (_windsurf_chat_column_detail_bits)
  [a53921561c0718a9]   STRU  _path_step_autopilot_intent  L=3 N=5 saved=12 sim=1.00
      src/koru/observability_dsl.py:209-211  (_path_step_autopilot_intent)
      src/koru/observability_dsl.py:219-221  (_path_step_autopilot_drive_requested)
      src/koru/observability_dsl.py:236-238  (_path_step_autopilot_drive_failed)
      src/koru/observability_dsl.py:241-243  (_path_step_autonomy_blocker)
      src/koru/observability_dsl.py:246-248  (_path_step_autonomy_next)
  [debc1b641269fc65]   STRU  _handle_mcp_list_tickets  L=6 N=3 saved=12 sim=1.00
      src/koruapi/invoke_handlers.py:191-196  (_handle_mcp_list_tickets)
      src/koruapi/invoke_handlers.py:199-202  (_handle_mcp_run_ticket)
      src/koruapi/invoke_handlers.py:205-210  (_handle_mcp_quality_gates)
  [c20862ff3335f22f]   STRU  message_received  L=12 N=2 saved=12 sim=1.00
      src/koruide/protocol.py:256-267  (message_received)
      src/koruide/protocol.py:270-281  (status_error)
  [5ce2dcca655ca5f7]   STRU  idle_marker_patterns  L=6 N=3 saved=12 sim=1.00
      src/korullm/strategies/claude.py:41-46  (idle_marker_patterns)
      src/korullm/strategies/gpt.py:41-46  (idle_marker_patterns)
      src/korullm/strategies/ollama.py:54-59  (idle_marker_patterns)
  [eca4d44fc02dbc88]   EXAC  _bridge_status_payload  L=11 N=2 saved=11 sim=1.00
      src/koru/autopilot/commands/drive.py:161-171  (_bridge_status_payload)
      src/koru/ide_doctor_cli.py:106-116  (_bridge_status_payload)
  [289ad8ee3567327f]   EXAC  _trace_event_matches  L=11 N=2 saved=11 sim=1.00
      src/koruapi/dashboard_observability.py:49-59  (_trace_event_matches)
      src/koruobserve/cli.py:179-189  (_trace_event_matches)
  [b90195cf482e2b54]   STRU  _terminal_shell_context  L=11 N=2 saved=11 sim=1.00
      packages/coru/src/coru/cli.py:702-712  (_terminal_shell_context)
      packages/coru/src/coru/ide_detection.py:125-135  (terminal_shell_context)
  [7bae356d1069c49d]   STRU  _ensure_trusted_publisher_for_plugin  L=11 N=2 saved=11 sim=1.00
      src/koru/autonomous_operator.py:108-118  (_ensure_trusted_publisher_for_plugin)
      src/koru/autonomous_operator.py:169-179  (_emit_reload_required_lines)
  [9c87044244d55b14]   STRU  _command_loop_main  L=11 N=2 saved=11 sim=1.00
      src/koru/cli_cleaned.py:317-327  (_command_loop_main)
      src/koru/cli_loop.py:12-49  (command_loop_main)
  [9da96ec07ab2704d]   STRU  _event_to_record  L=11 N=2 saved=11 sim=1.00
      src/koru/cqrs/event_store.py:52-62  (_event_to_record)
      src/koruapi/dashboard_observability.py:62-72  (_stored_event_payload)
  [c93549cdf0de486b]   STRU  chat_control_recovered_after_retry  L=11 N=2 saved=11 sim=1.00
      src/koru/doctor_chat_control.py:275-285  (chat_control_recovered_after_retry)
      src/koru/doctor_reporting_checks.py:153-163  (_chat_control_recovered_after_retry)
  [9ffe15f1e8330ded]   STRU  _current_koru_version  L=5 N=3 saved=10 sim=1.00
      src/koru/autonomous_daemon.py:33-37  (_current_koru_version)
      src/koruide/daemon/metadata.py:77-81  (_package_version)
      src/koruide/daemon/protocol.py:15-19  (_daemon_package_version)
  [d7c7635fb09b204f]   STRU  trace_show_decisions  L=10 N=2 saved=10 sim=1.00
      src/koru/autonomy/replay_builders.py:38-47  (trace_show_decisions)
      src/koru/autonomy/replay_builders.py:50-59  (trace_show_interfaces)
  [05359c39f46bbb39]   STRU  _versioned_plugin_vsix_candidates  L=10 N=2 saved=10 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:94-103  (_versioned_plugin_vsix_candidates)
      src/koruide/plugin_installer.py:216-225  (_versioned_vsix_candidates)
  [1aa3e302d63a9653]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:116-125  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve_utils.py:146-155  (read_serve_endpoint)
  [307ce5aa804011f3]   STRU  _sanitize_cursor_paste  L=10 N=2 saved=10 sim=1.00
      src/koruide/command_picker.py:147-156  (_sanitize_cursor_paste)
      src/koruide/command_picker.py:163-172  (_sanitize_cursor_focus_open)
  [9b9080c892a8a0f7]   STRU  _clear_pending_plugin_drive  L=10 N=2 saved=10 sim=1.00
      src/koruide/daemon/handlers_ack.py:186-195  (_clear_pending_plugin_drive)
      src/koruide/daemon/handlers_drive.py:258-267  (_clear_stale_pending_plugin_drive)
  [69b1daff9f6bbf2b]   STRU  detection  L=5 N=3 saved=10 sim=1.00
      src/koruide/ides/antigravity.py:28-32  (detection)
      src/koruide/ides/cursor.py:43-47  (detection)
      src/koruide/ides/zed.py:28-32  (detection)
  [bdba1cde154965e7]   STRU  extension_id_for_ide  L=10 N=2 saved=10 sim=1.00
      src/koruide/plugin_installer.py:69-78  (extension_id_for_ide)
      src/koruide/plugin_version.py:30-39  (expected_plugin_version_for_ide)
  [16682c7e498f70df]   STRU  allow_keyboard_autopilot_fallback  L=3 N=4 saved=9 sim=1.00
      src/koru/autonomous_cycle_gate.py:226-228  (allow_keyboard_autopilot_fallback)
      src/koru/autonomous_cycle_gate.py:267-269  (scan_while_waiting_input_enabled)
      src/koru/autopilot/install_manager.py:547-552  (_restart_ide_on_build_mismatch_enabled)
      src/koruide/plugin_installer.py:499-501  (_env_force_reassert_extension_install)
  [afb2980f49f0e790]   STRU  _default_runner  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomy/code2llm_discovery.py:102-110  (_default_runner)
      src/koru/self_control.py:113-121  (_run)
  [087cc37be81c7aa2]   STRU  _action_drive  L=9 N=2 saved=9 sim=1.00
      src/koru/autopilot/cli_command.py:201-209  (_action_drive)
      src/koru/autopilot/cli_command.py:216-224  (_action_status)
  [1359dc36e2736e4b]   STRU  _add_queue_args  L=9 N=2 saved=9 sim=1.00
      src/koru/cli_cleaned.py:97-105  (_add_queue_args)
      src/koru/cli_parser.py:45-97  (_add_queue_arguments)
  [d13ba2ad7b9027b8]   STRU  _cursor_project_config  L=3 N=4 saved=9 sim=1.00
      src/koru/mcp_provision.py:44-46  (_cursor_project_config)
      src/koru/mcp_provision.py:49-51  (_vscode_project_config)
      src/koru/mcp_provision.py:54-56  (_windsurf_project_config)
      src/koru/mcp_provision.py:59-61  (_zed_project_settings)
  [42eceec610714f38]   STRU  _handle_wait  L=3 N=4 saved=9 sim=1.00
      src/korudsl/library.py:38-40  (_handle_wait)
      src/korudsl/library.py:43-45  (_handle_get)
      src/korudsl/library.py:48-50  (_handle_save)
      src/korudsl/library.py:53-55  (_handle_if)
  [77510f4ffc3c1e43]   EXAC  _lane_environ  L=8 N=2 saved=8 sim=1.00
      packages/coru/src/coru/supervisor/daemon_ctl.py:12-19  (_lane_environ)
      packages/coru/src/coru/supervisor/probe.py:18-25  (_lane_environ)
  [1d3dac913ac1fd2e]   EXAC  _pid_alive  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomous_readiness.py:312-319  (_pid_alive)
      src/koru/autopilot/lane_context.py:98-105  (_pid_alive)
  [cd4295cd9e19bb5a]   STRU  get_plugin_version_from_source  L=8 N=2 saved=8 sim=1.00
      scripts/sync-vscode-plugin-version.py:23-30  (get_plugin_version_from_source)
      scripts/sync-vscode-plugin-version.py:33-40  (get_plugin_version_from_package)
  [4039faecf06f3b49]   STRU  llm_reflection_summary_max_age_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomous_cycle_chat_activity_config.py:80-87  (llm_reflection_summary_max_age_seconds)
      src/koruide/daemon/handlers.py:92-99  (_plugin_rejection_log_interval_seconds)
  [d6ab146dbe20dd1d]   STRU  _create_failed_scan_cooldown_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:117-124  (_create_failed_scan_cooldown_seconds)
      src/koru/autonomy/phases/scan_phase.py:127-134  (_duplicate_only_scan_cooldown_seconds)
  [e2cb0d17a3d9ba71]   STRU  scan_force  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/replay_builders.py:89-96  (scan_force)
      src/koru/autonomy/replay_builders.py:99-106  (wup_show_health)
  [e405b9419776997d]   STRU  _check_git_commit_policy  L=4 N=3 saved=8 sim=1.00
      src/koru/policy.py:194-197  (_check_git_commit_policy)
      src/koru/policy.py:200-203  (_check_git_push_policy)
      src/koru/policy.py:226-229  (_check_git_tag_policy)
  [aadbe4684712c6c8]   STRU  nlp2uri_missing_message  L=8 N=2 saved=8 sim=1.00
      src/koruapi/desktop_uri.py:28-35  (nlp2uri_missing_message)
      src/koruapi/nlp2oql_bridge.py:24-30  (nlp2oql_missing_message)
  [cb37c14faf2d9f23]   EXAC  _ps_rows  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:90-96  (_ps_rows)
      src/koru/autonomous_processes.py:90-96  (_ps_rows)
  [8d303b9fda997ca0]   STRU  as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomous_process_guard.py:213-219  (as_managed)
      src/koru/autonomous_processes.py:210-216  (_as_managed)
  [11fb6d2566e9557e]   STRU  _context_main  L=7 N=2 saved=7 sim=1.00
      src/koru/cli_cleaned.py:289-295  (_context_main)
      src/koru/cli_context.py:18-29  (_context_main)
  [0de131b92b4b1418]   STRU  is_shell_agent  L=7 N=2 saved=7 sim=1.00
      src/koru/sllm_bridge.py:38-44  (is_shell_agent)
      src/koru/sllm_bridge.py:47-53  (shell_agent_available)
  [903e876d5fa9e91e]   STRU  shell_tool_registry_entries  L=7 N=2 saved=7 sim=1.00
      src/koru/sllm_bridge.py:65-71  (shell_tool_registry_entries)
      src/koru/sllm_bridge.py:74-80  (shell_agent_backend_profiles)
  [bb03ab059e9c3576]   STRU  cmd_providers_list  L=7 N=2 saved=7 sim=1.00
      src/koruobserve/providers_cli.py:117-123  (cmd_providers_list)
      src/koruobserve/providers_cli.py:142-148  (cmd_providers_reset)
  [2f70022f4d619771]   EXAC  _path_is_relative_to  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous_runtime.py:83-88  (_path_is_relative_to)
      src/koru/cli_cleaned.py:219-224  (_path_is_relative_to)
  [e4f69d6ce48d3dc0]   EXAC  all_events  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:120-125  (all_events)
      src/koru/cqrs/event_store.py:198-203  (all_events)
  [d5c3295002f07996]   EXAC  events_for_aggregate  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:127-132  (events_for_aggregate)
      src/koru/cqrs/event_store.py:205-210  (events_for_aggregate)
  [44807df02c2db882]   EXAC  plugin  L=6 N=2 saved=6 sim=1.00
      src/koruide/ides/antigravity.py:52-57  (plugin)
      src/koruide/ides/windsurf.py:51-56  (plugin)
  [ab111a81f67e34c9]   STRU  _desktop_capture_enabled  L=6 N=2 saved=6 sim=1.00
      packages/coru/src/coru/cli.py:1813-1818  (_desktop_capture_enabled)
      packages/coru/src/coru/cli.py:2836-2841  (_coru_readiness_strict)
  [6586a27651ee785d]   STRU  _collect_manage_issue_problems  L=6 N=2 saved=6 sim=1.00
      packages/coru/src/coru/repair/diagnostics.py:98-103  (_collect_manage_issue_problems)
      packages/coru/src/coru/repair/diagnostics.py:132-137  (_collect_manage_action_problems)
  [f62b4298f50f9a3e]   STRU  process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomous_process_guard.py:45-50  (process_cwd)
      src/koru/autonomous_processes.py:52-57  (_process_cwd)
  [f7f221a1339ae592]   STRU  _scan_result_is_create_failed_only  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:88-93  (_scan_result_is_create_failed_only)
      src/koru/autonomy/phases/scan_phase.py:96-101  (_scan_result_is_duplicate_only)
  [934a7fee5623b8db]   STRU  _previous_serve_config  L=3 N=3 saved=6 sim=1.00
      src/koru/configurator.py:267-269  (_previous_serve_config)
      src/koru/task_dedupe.py:14-16  (_source_context)
      src/koruapi/dashboard_config.py:67-69  (_saved_serve_config)
  [08e658ea14cb595d]   STRU  _check_autopilot_chat_control  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor.py:294-299  (_check_autopilot_chat_control)
      src/koru/doctor.py:444-449  (_check_pytest_collect)
  [8e647d39a6242d46]   STRU  chat_control_command_hints  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor_chat_control.py:267-272  (chat_control_command_hints)
      src/koru/doctor_reporting_checks.py:145-150  (_chat_control_command_hints)
  [0368f441c70e35f2]   STRU  _read_json_file  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor_plugin_bundle.py:12-17  (_read_json_file)
      src/koruide/daemon/metadata.py:58-63  (read_daemon_metadata)
  [23bf44be8059e529]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:364-369  (set_component_enabled)
      src/koru/topology.py:372-377  (set_pipeline_enabled)
  [484cbd493df1c900]   STRU  keyboard  L=6 N=2 saved=6 sim=1.00
      src/koruide/ides/jetbrains.py:68-73  (keyboard)
      src/koruide/ides/zed.py:49-54  (keyboard)
  [e33387610a1ba207]   EXAC  png_dimensions  L=5 N=2 saved=5 sim=1.00
      src/koruvision/capture_mss.py:48-52  (png_dimensions)
      src/koruvision/providers/base.py:54-58  (png_dimensions)
  [48d6b6df3a9a1079]   STRU  _blocked_interface_items  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous_loop_runner.py:71-75  (_blocked_interface_items)
      src/koru/doctor_autopilot_checks.py:228-232  (_daemon_plugin_rows)
  [2fb9b052401849b5]   STRU  _socket_inode  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomous_readiness.py:322-326  (_socket_inode)
      src/koruide/daemon/metadata.py:103-107  (_inode)
  [7f81fbca957398f9]   STRU  _build_trace_decisions_action  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomy/replay_parser.py:85-89  (_build_trace_decisions_action)
      src/koru/autonomy/replay_parser.py:92-96  (_build_trace_interfaces_action)
  [e995cdfdac544c37]   STRU  _package_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autopilot/install_manager.py:139-143  (_package_version)
      src/koru/self_control.py:133-137  (_installed_version)
  [53e0b94dd0e401c5]   STRU  _command_value  L=5 N=2 saved=5 sim=1.00
      src/koru/cli_cleaned.py:78-82  (_command_value)
      src/koru/cli_parser.py:10-14  (_command_value)
  [2ebf8cc4fedc8cdc]   STRU  runtime_for_project  L=5 N=2 saved=5 sim=1.00
      src/koru/cqrs/__init__.py:61-65  (runtime_for_project)
      src/koru/cqrs/__init__.py:68-76  (runtime_for_storage_dir)
  [140b901fee617a1b]   STRU  _check_autonomous_service_stream  L=5 N=2 saved=5 sim=1.00
      src/koru/doctor.py:231-235  (_check_autonomous_service_stream)
      src/koru/doctor.py:420-424  (_check_planfile_cli_version)
  [8745b82e7c4fd665]   STRU  _check_autopilot_debug_log  L=5 N=2 saved=5 sim=1.00
      src/koru/doctor.py:259-263  (_check_autopilot_debug_log)
      src/koru/doctor.py:310-314  (_check_windsurf_chat_column_control)
  [52b6978976918642]   STRU  windsurf_line_mentions_chat_open_command  L=5 N=2 saved=5 sim=1.00
      src/koru/doctor_chat_control.py:383-387  (windsurf_line_mentions_chat_open_command)
      src/koru/doctor_reporting_checks.py:312-316  (_windsurf_line_mentions_chat_open_command)
  [4d55a4ed8c7926d3]   STRU  _koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/local_manager_client.py:23-27  (_koru_version)
      src/koru/local_manager_state.py:20-24  (koru_version)
  [3cece1e608066b8f]   STRU  planfile_dir  L=5 N=2 saved=5 sim=1.00
      src/koru/runtime.py:42-46  (planfile_dir)
      src/koruapi/dashboard_serve_utils.py:158-162  (_build_handler_for)
  [2dca45dba8f8e078]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [3bb87e332b7bbbe9]   STRU  detection  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/vscode.py:27-31  (detection)
      src/koruide/ides/windsurf.py:28-34  (detection)
  [322d974cc48eae57]   STRU  aliases  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/vscode.py:47-51  (aliases)
      src/koruide/ides/vscodium.py:33-37  (aliases)
  [962ce98f78874f51]   EXAC  _cycle_attr  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_cycle_chat_activity.py:56-59  (_cycle_attr)
      src/koru/autonomous_cycle_drive_retry.py:79-82  (_cycle_attr)
  [d994225d45fadf8d]   EXAC  _terminal_host_ide_id  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_plugin_wait.py:27-30  (_terminal_host_ide_id)
      src/koru/ide_adapters/ide_reload.py:510-513  (_terminal_host_ide_id)
  [7fd8c14ac09b2e1a]   STRU  _terminal_ide_hint  L=4 N=2 saved=4 sim=1.00
      packages/coru/src/coru/cli.py:696-699  (_terminal_ide_hint)
      packages/coru/src/coru/ide_detection.py:138-141  (terminal_ide_hint)
  [abd6da8ed80bf640]   STRU  status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_checkpoint.py:204-207  (status_in_skip_list)
      src/koru/autonomous_cycle_common.py:17-20  (_status_in_skip_list)
  [450f03815092d888]   STRU  _build_queue_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_cycle.py:593-596  (_build_queue_command)
      src/koru/autonomy/phases/queue_phase.py:45-48  (build_queue_command)
  [7c9e9272487e6fed]   STRU  _looks_like_autonomous_up_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomous_processes.py:84-87  (_looks_like_autonomous_up_command)
      src/koruobserve/providers_cli.py:10-13  (screencast_session_path)
  [7ee750a1b7660a3e]   EXAC  to_json  L=3 N=2 saved=3 sim=1.00
      src/koru/deployment_events/batch.py:34-36  (to_json)
      src/koru/deployment_events/models.py:98-100  (to_json)
  [727da6a61b64086c]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      src/koru/local_manager_state.py:57-59  (__init__)
      src/koru/local_manager_state.py:73-75  (__init__)
  [836645be6056623e]   EXAC  _bound_port  L=3 N=2 saved=3 sim=1.00
      src/koru/local_service.py:329-331  (_bound_port)
      src/koruapi/dashboard_serve_utils.py:170-172  (_bound_port)
  [dfeb14021be03fc6]   EXAC  capture_one  L=3 N=2 saved=3 sim=1.00
      src/koruvision/providers/cli_tools.py:37-39  (capture_one)
      src/koruvision/providers/obs_websocket.py:229-231  (capture_one)
  [3ea4bac2fd5c5d5a]   STRU  _ide_from_vscode_pid  L=3 N=2 saved=3 sim=1.00
      packages/coru/src/coru/cli.py:681-683  (_ide_from_vscode_pid)
      packages/coru/src/coru/cli.py:686-688  (_vscode_family_env_hint)
  [27b507b39e730868]   STRU  _normalize_autonomous_argv  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:973-975  (_normalize_autonomous_argv)
      src/koru/wizard/cli.py:51-53  (propose_projects)
  [88f4f0796c577e69]   STRU  _apply_auto_pipeline_flags  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:992-994  (_apply_auto_pipeline_flags)
      src/koru/autonomous.py:997-999  (_apply_replace_existing_flags)
  [051381e8727d3870]   STRU  llm_needs_input_ticket_queue_name  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_chat_activity_config.py:95-97  (llm_needs_input_ticket_queue_name)
      src/koru/autonomous_cycle_chat_activity_config.py:100-102  (llm_needs_input_ticket_priority)
  [4d353528733d9de9]   STRU  _auto_llm_ready_enabled  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous_cycle_skip_conditions.py:41-43  (_auto_llm_ready_enabled)
      src/koru/autonomy/operator_pipeline.py:396-398  (_self_control_autorepair_enabled)
  [aba873354115f873]   STRU  redup_scan_command  L=3 N=2 saved=3 sim=1.00
      src/koru/redup_integration.py:22-24  (redup_scan_command)
      src/koru/redup_integration.py:27-29  (redup_check_command)
  [ef59c3eeb1bec905]   STRU  build_dashboard_handler  L=3 N=2 saved=3 sim=1.00
      src/koruapi/dashboard_routes.py:605-607  (build_dashboard_handler)
      src/koruapi/dashboard_serve.py:94-96  (_build_handler)
  [efe3054fb1cdddb4]   STRU  supported_autopilot_ide_ids  L=3 N=2 saved=3 sim=1.00
      src/koruide/ide.py:93-95  (supported_autopilot_ide_ids)
      src/koruide/ide.py:103-105  (vscode_extension_plugin_ide_ids)

REFACTOR[134] (ranked by priority):
  [1] ◐ extract_module     → src/koru/utils/_bootstrap_main.py
      WHY: 2 occurrences of 52-line block across 2 files — saves 52 lines
      FILES: src/koru/cli_bootstrap.py, src/koru/cli_cleaned.py
  [2] ○ extract_function   → src/koru/utils/_scan_pyqual_report.py
      WHY: 3 occurrences of 26-line block across 1 files — saves 52 lines
      FILES: src/koru/scan.py
  [3] ○ extract_function   → src/koru/autopilot/utils/_add_calibrate_parser.py
      WHY: 2 occurrences of 42-line block across 1 files — saves 42 lines
      FILES: src/koru/autopilot/cli_parser.py
  [4] ○ extract_function   → src/koru/ide_adapters/utils/reuse_window_reload_enabled.py
      WHY: 4 occurrences of 14-line block across 1 files — saves 42 lines
      FILES: src/koru/ide_adapters/ide_reload.py
  [5] ○ extract_function   → src/koru/autopilot/utils/check_plugin_version_mismatch_issue.py
      WHY: 2 occurrences of 41-line block across 1 files — saves 41 lines
      FILES: src/koru/autopilot/install_checks.py
  [6] ○ extract_function   → src/koru/utils/emit_intent.py
      WHY: 7 occurrences of 6-line block across 1 files — saves 36 lines
      FILES: src/koru/observability_events.py
  [7] ◐ extract_function   → src/koru/utils/build_chat_control_detail_bits.py
      WHY: 2 occurrences of 33-line block across 2 files — saves 33 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [8] ○ extract_function   → src/koru/utils/_dsl_main.py
      WHY: 9 occurrences of 4-line block across 4 files — saves 32 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py, src/koru/cli_local_serve.py, src/koru/cli_serve.py
  [9] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 11 occurrences of 3-line block across 8 files — saves 30 lines
      FILES: src/koru/activity_log.py, src/koru/autonomous_cycle_chat_activity_config.py, src/koru/autonomous_operator.py, src/koru/autonomy/operator_pipeline.py, src/koru/autonomy/planning_llm_runtime.py +3 more
  [10] ○ extract_function   → src/koru/utils/provision_cursor.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: src/koru/mcp_provision.py
  [11] ○ extract_function   → src/utils/_build_local_serve_parser.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/cli_local_serve.py, src/koruapi/local.py
  [12] ○ extract_function   → src/koru/utils/chat_control_result.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [13] ○ extract_function   → packages/coru/src/coru/utils/_register_calibration_command.py
      WHY: 2 occurrences of 26-line block across 1 files — saves 26 lines
      FILES: packages/coru/src/coru/cli.py
  [14] ○ extract_function   → src/koru/wizard/utils/_finalise_ticket.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: src/koru/wizard/cli.py, src/koru/wizard/orchestrator.py
  [15] ○ extract_function   → src/utils/_koru_package_version.py
      WHY: 6 occurrences of 5-line block across 6 files — saves 25 lines
      FILES: src/koru/agents.py, src/koru/autonomous_startup.py, src/koru/cli_cleaned.py, src/koru/cli_parser.py, src/koruapi/cli.py +1 more
  [16] ○ extract_function   → src/koru/utils/windsurf_chat_column_result.py
      WHY: 2 occurrences of 23-line block across 2 files — saves 23 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [17] ○ extract_function   → packages/coru/src/coru/utils/sync_plugins_for_ide.py
      WHY: 2 occurrences of 21-line block across 1 files — saves 21 lines
      FILES: packages/coru/src/coru/ecosystem.py
  [18] ○ extract_function   → src/koru/utils/_plugin_reconnected_after_wait.py
      WHY: 2 occurrences of 21-line block across 1 files — saves 21 lines
      FILES: src/koru/autonomous_plugin_wait.py
  [19] ○ extract_function   → src/utils/_plugin_package_version.py
      WHY: 4 occurrences of 7-line block across 2 files — saves 21 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [20] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 5 occurrences of 5-line block across 5 files — saves 20 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomous_daemon.py, src/koru/autonomous_processes.py
  [21] ○ extract_function   → src/koru/utils/_wup_process_match.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [22] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: src/korullm/strategies/codex.py, src/korullm/strategies/ollama.py
  [23] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous.py, src/koru/autonomous_cycle_skip_conditions.py, src/koru/autonomy/phases/utils.py
  [24] ○ extract_function   → src/koru/utils/current_head.py
      WHY: 3 occurrences of 9-line block across 3 files — saves 18 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle.py, src/koru/autonomy/phases/utils.py
  [25] ○ extract_function   → src/koru/utils/_run_queue_loop.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [26] ○ extract_function   → src/koru/utils/autopilot_redrive_cooldown_seconds.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: src/koru/autonomous_cycle_chat_activity_config.py
  [27] ○ extract_function   → src/koru/utils/_is_bare_invocation.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [28] ○ extract_function   → src/koru/utils/_post_workers_register.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: src/koru/local_service.py
  [29] ○ extract_function   → src/koru/utils/_topology_component_toggler.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/cli_topology.py
  [30] ○ extract_function   → src/koru/ide_adapters/utils/reload_via_reopen_workspace.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/ide_adapters/ide_reload.py
  [31] ○ extract_function   → src/koruapi/utils/tool_env2llm_get_registry.py
      WHY: 4 occurrences of 5-line block across 1 files — saves 15 lines
      FILES: src/koruapi/mcp_server_env2llm.py
  [32] ○ extract_function   → packages/coru/src/coru/repair/utils/_installed_extension_dir.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: packages/coru/src/coru/repair/diagnostics.py, packages/coru/src/coru/repair/pipeline.py
  [33] ○ extract_function   → scripts/utils/update_plugin_version_source.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [34] ○ extract_function   → src/koru/autonomy/phases/utils/_should_skip_repeated_create_failed_scan.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [35] ○ extract_function   → src/koru/autopilot/utils/_action_install_plugin.py
      WHY: 3 occurrences of 7-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/cli_command.py
  [36] ○ extract_function   → src/koru/autopilot/utils/_open_new_ide_window_for_plugin_build_action.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/install_manager.py
  [37] ○ extract_function   → src/koru/utils/_peek_project_from_argv.py
      WHY: 3 occurrences of 7-line block across 3 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_auto.py, src/koru/cli_cleaned.py
  [38] ○ extract_function   → src/koru/utils/_maybe_print_project_venv_hint.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [39] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [40] ○ extract_function   → src/koru/autonomy/phases/utils/_remember_scan_create_failed_state.py
      WHY: 2 occurrences of 13-line block across 1 files — saves 13 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [41] ○ extract_function   → src/koru/utils/_should_suggest_wizard.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/cli.py, src/koru/cli_cleaned.py
  [42] ○ extract_function   → src/koru/utils/_bridge_hypotheses_payload.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/commands/drive.py, src/koru/ide_doctor_cli.py
  [43] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py
  [44] ○ extract_function   → src/koruvision/providers/utils/list_monitors.py
      WHY: 4 occurrences of 4-line block across 4 files — saves 12 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/grim.py, src/koruvision/providers/portal_screencast.py, src/koruvision/providers/portal_screenshot.py
  [45] ○ extract_function   → utils/resolve_coru_bin.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: packages/coru/src/coru/supervisor/systemd_unit.py, src/koru/autopilot/systemd_cli.py
  [46] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [47] ○ extract_function   → src/koru/utils/chat_control_has_failures.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [48] ○ extract_function   → src/koru/utils/windsurf_chat_column_detail_bits.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [49] ○ extract_function   → src/koru/utils/_path_step_autopilot_intent.py
      WHY: 5 occurrences of 3-line block across 1 files — saves 12 lines
      FILES: src/koru/observability_dsl.py
  [50] ○ extract_function   → src/koruapi/utils/_handle_mcp_list_tickets.py
      WHY: 3 occurrences of 6-line block across 1 files — saves 12 lines
      FILES: src/koruapi/invoke_handlers.py
  [51] ○ extract_function   → src/koruide/utils/message_received.py
      WHY: 2 occurrences of 12-line block across 1 files — saves 12 lines
      FILES: src/koruide/protocol.py
  [52] ○ extract_function   → src/korullm/strategies/utils/idle_marker_patterns.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py, src/korullm/strategies/ollama.py
  [53] ○ extract_function   → src/koru/utils/_bridge_status_payload.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/autopilot/commands/drive.py, src/koru/ide_doctor_cli.py
  [54] ○ extract_function   → src/utils/_trace_event_matches.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koruapi/dashboard_observability.py, src/koruobserve/cli.py
  [55] ○ extract_function   → packages/coru/src/coru/utils/_terminal_shell_context.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/ide_detection.py
  [56] ○ extract_function   → src/koru/utils/_ensure_trusted_publisher_for_plugin.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: src/koru/autonomous_operator.py
  [57] ○ extract_function   → src/koru/utils/_command_loop_main.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_loop.py
  [58] ○ extract_function   → src/utils/_event_to_record.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cqrs/event_store.py, src/koruapi/dashboard_observability.py
  [59] ○ extract_function   → src/koru/utils/chat_control_recovered_after_retry.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [60] ○ extract_function   → src/utils/_current_koru_version.py
      WHY: 3 occurrences of 5-line block across 3 files — saves 10 lines
      FILES: src/koru/autonomous_daemon.py, src/koruide/daemon/metadata.py, src/koruide/daemon/protocol.py
  [61] ○ extract_function   → src/koru/autonomy/utils/trace_show_decisions.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/koru/autonomy/replay_builders.py
  [62] ○ extract_function   → src/utils/_versioned_plugin_vsix_candidates.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [63] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve_utils.py
  [64] ○ extract_function   → src/koruide/utils/_sanitize_cursor_paste.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/koruide/command_picker.py
  [65] ○ extract_function   → src/koruide/daemon/utils/_clear_pending_plugin_drive.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koruide/daemon/handlers_ack.py, src/koruide/daemon/handlers_drive.py
  [66] ○ extract_function   → src/koruide/ides/utils/detection.py
      WHY: 3 occurrences of 5-line block across 3 files — saves 10 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/cursor.py, src/koruide/ides/zed.py
  [67] ○ extract_function   → src/koruide/utils/extension_id_for_ide.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koruide/plugin_installer.py, src/koruide/plugin_version.py
  [68] ○ extract_function   → src/utils/allow_keyboard_autopilot_fallback.py
      WHY: 4 occurrences of 3-line block across 3 files — saves 9 lines
      FILES: src/koru/autonomous_cycle_gate.py, src/koru/autopilot/install_manager.py, src/koruide/plugin_installer.py
  [69] ○ extract_function   → src/koru/utils/_default_runner.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomy/code2llm_discovery.py, src/koru/self_control.py
  [70] ○ extract_function   → src/koru/autopilot/utils/_action_drive.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: src/koru/autopilot/cli_command.py
  [71] ○ extract_function   → src/koru/utils/_add_queue_args.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_parser.py
  [72] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/koru/mcp_provision.py
  [73] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [74] ○ extract_function   → packages/coru/src/coru/supervisor/utils/_lane_environ.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/coru/src/coru/supervisor/daemon_ctl.py, packages/coru/src/coru/supervisor/probe.py
  [75] ○ extract_function   → src/koru/utils/_pid_alive.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autonomous_readiness.py, src/koru/autopilot/lane_context.py
  [76] ○ extract_function   → scripts/utils/get_plugin_version_from_source.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [77] ○ extract_function   → src/utils/llm_reflection_summary_max_age_seconds.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autonomous_cycle_chat_activity_config.py, src/koruide/daemon/handlers.py
  [78] ○ extract_function   → src/koru/autonomy/phases/utils/_create_failed_scan_cooldown_seconds.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [79] ○ extract_function   → src/koru/autonomy/utils/scan_force.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/autonomy/replay_builders.py
  [80] ○ extract_function   → src/koru/utils/_check_git_commit_policy.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: src/koru/policy.py
  [81] ○ extract_function   → src/koruapi/utils/nlp2uri_missing_message.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koruapi/desktop_uri.py, src/koruapi/nlp2oql_bridge.py
  [82] ○ extract_function   → src/koru/utils/_ps_rows.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [83] ○ extract_function   → src/koru/utils/as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [84] ○ extract_function   → src/koru/utils/_context_main.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_context.py
  [85] ○ extract_function   → src/koru/utils/is_shell_agent.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/sllm_bridge.py
  [86] ○ extract_function   → src/koru/utils/shell_tool_registry_entries.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/sllm_bridge.py
  [87] ○ extract_function   → src/koruobserve/utils/cmd_providers_list.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koruobserve/providers_cli.py
  [88] ○ extract_function   → src/koru/utils/_path_is_relative_to.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous_runtime.py, src/koru/cli_cleaned.py
  [89] ○ extract_function   → src/koru/cqrs/utils/all_events.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [90] ○ extract_function   → src/koru/cqrs/utils/events_for_aggregate.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [91] ○ extract_function   → src/koruide/ides/utils/plugin.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/windsurf.py
  [92] ○ extract_function   → packages/coru/src/coru/utils/_desktop_capture_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: packages/coru/src/coru/cli.py
  [93] ○ extract_function   → packages/coru/src/coru/repair/utils/_collect_manage_issue_problems.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: packages/coru/src/coru/repair/diagnostics.py
  [94] ○ extract_function   → src/koru/utils/process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomous_process_guard.py, src/koru/autonomous_processes.py
  [95] ○ extract_function   → src/koru/autonomy/phases/utils/_scan_result_is_create_failed_only.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [96] ○ extract_function   → src/utils/_previous_serve_config.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/configurator.py, src/koru/task_dedupe.py, src/koruapi/dashboard_config.py
  [97] ○ extract_function   → src/koru/utils/_check_autopilot_chat_control.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/doctor.py
  [98] ○ extract_function   → src/koru/utils/chat_control_command_hints.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [99] ○ extract_function   → src/utils/_read_json_file.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/doctor_plugin_bundle.py, src/koruide/daemon/metadata.py
  [100] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [101] ○ extract_function   → src/koruide/ides/utils/keyboard.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruide/ides/jetbrains.py, src/koruide/ides/zed.py
  [102] ○ extract_function   → src/koruvision/utils/png_dimensions.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruvision/capture_mss.py, src/koruvision/providers/base.py
  [103] ○ extract_function   → src/koru/utils/_blocked_interface_items.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous_loop_runner.py, src/koru/doctor_autopilot_checks.py
  [104] ○ extract_function   → src/utils/_socket_inode.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomous_readiness.py, src/koruide/daemon/metadata.py
  [105] ○ extract_function   → src/koru/autonomy/utils/_build_trace_decisions_action.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/autonomy/replay_parser.py
  [106] ○ extract_function   → src/koru/utils/_package_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autopilot/install_manager.py, src/koru/self_control.py
  [107] ○ extract_function   → src/koru/utils/_command_value.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/cli_cleaned.py, src/koru/cli_parser.py
  [108] ○ extract_function   → src/koru/cqrs/utils/runtime_for_project.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/cqrs/__init__.py
  [109] ○ extract_function   → src/koru/utils/_check_autonomous_service_stream.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/doctor.py
  [110] ○ extract_function   → src/koru/utils/_check_autopilot_debug_log.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/doctor.py
  [111] ○ extract_function   → src/koru/utils/windsurf_line_mentions_chat_open_command.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [112] ○ extract_function   → src/koru/utils/_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/local_manager_client.py, src/koru/local_manager_state.py
  [113] ○ extract_function   → src/utils/planfile_dir.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/runtime.py, src/koruapi/dashboard_serve_utils.py
  [114] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [115] ○ extract_function   → src/koruide/ides/utils/detection.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/vscode.py, src/koruide/ides/windsurf.py
  [116] ○ extract_function   → src/koruide/ides/utils/aliases.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/vscode.py, src/koruide/ides/vscodium.py
  [117] ○ extract_function   → src/koru/utils/_cycle_attr.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_cycle_chat_activity.py, src/koru/autonomous_cycle_drive_retry.py
  [118] ○ extract_function   → src/koru/utils/_terminal_host_ide_id.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_plugin_wait.py, src/koru/ide_adapters/ide_reload.py
  [119] ○ extract_function   → packages/coru/src/coru/utils/_terminal_ide_hint.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/ide_detection.py
  [120] ○ extract_function   → src/koru/utils/status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_checkpoint.py, src/koru/autonomous_cycle_common.py
  [121] ○ extract_function   → src/koru/utils/_build_queue_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_cycle.py, src/koru/autonomy/phases/queue_phase.py
  [122] ○ extract_function   → src/utils/_looks_like_autonomous_up_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomous_processes.py, src/koruobserve/providers_cli.py
  [123] ○ extract_function   → src/koru/deployment_events/utils/to_json.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/deployment_events/batch.py, src/koru/deployment_events/models.py
  [124] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/local_manager_state.py
  [125] ○ extract_function   → src/utils/_bound_port.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/local_service.py, src/koruapi/dashboard_serve_utils.py
  [126] ○ extract_function   → src/koruvision/providers/utils/capture_one.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/obs_websocket.py
  [127] ○ extract_function   → packages/coru/src/coru/utils/_ide_from_vscode_pid.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/coru/src/coru/cli.py
  [128] ○ extract_function   → src/koru/utils/_normalize_autonomous_argv.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous.py, src/koru/wizard/cli.py
  [129] ○ extract_function   → src/koru/utils/_apply_auto_pipeline_flags.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous.py
  [130] ○ extract_function   → src/koru/utils/llm_needs_input_ticket_queue_name.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_chat_activity_config.py
  [131] ○ extract_function   → src/koru/utils/_auto_llm_ready_enabled.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous_cycle_skip_conditions.py, src/koru/autonomy/operator_pipeline.py
  [132] ○ extract_function   → src/koru/utils/redup_scan_command.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/redup_integration.py
  [133] ○ extract_function   → src/koruapi/utils/build_dashboard_handler.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruapi/dashboard_routes.py, src/koruapi/dashboard_serve.py
  [134] ○ extract_function   → src/koruide/utils/supported_autopilot_ide_ids.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruide/ide.py

QUICK_WINS[99] (low risk, high savings — do first):
  [2] extract_function   saved=52L  → src/koru/utils/_scan_pyqual_report.py
      FILES: scan.py
  [3] extract_function   saved=42L  → src/koru/autopilot/utils/_add_calibrate_parser.py
      FILES: cli_parser.py
  [4] extract_function   saved=42L  → src/koru/ide_adapters/utils/reuse_window_reload_enabled.py
      FILES: ide_reload.py
  [5] extract_function   saved=41L  → src/koru/autopilot/utils/check_plugin_version_mismatch_issue.py
      FILES: install_checks.py
  [6] extract_function   saved=36L  → src/koru/utils/emit_intent.py
      FILES: observability_events.py
  [8] extract_function   saved=32L  → src/koru/utils/_dsl_main.py
      FILES: cli.py, cli_cleaned.py, cli_local_serve.py +1
  [9] extract_function   saved=30L  → src/utils/activity_enabled.py
      FILES: activity_log.py, autonomous_cycle_chat_activity_config.py, autonomous_operator.py +5
  [10] extract_function   saved=30L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [11] extract_function   saved=29L  → src/utils/_build_local_serve_parser.py
      FILES: cli_local_serve.py, local.py
  [12] extract_function   saved=29L  → src/koru/utils/chat_control_result.py
      FILES: doctor_chat_control.py, doctor_reporting_checks.py

DEPENDENCY_RISK[1] (duplicates spanning multiple packages):
  resolve_coru_bin  packages=2  files=2
      packages/coru/src/coru/supervisor/systemd_unit.py
      src/koru/autopilot/systemd_cli.py

EFFORT_ESTIMATE (total ≈ 57.4h):
  hard   _bootstrap_main                     saved=52L  ~156min
  hard   _scan_pyqual_report                 saved=52L  ~104min
  hard   _add_calibrate_parser               saved=42L  ~126min
  medium reuse_window_reload_enabled         saved=42L  ~84min
  hard   check_plugin_version_mismatch_issue saved=41L  ~123min
  medium emit_intent                         saved=36L  ~72min
  hard   build_chat_control_detail_bits      saved=33L  ~99min
  medium _dsl_main                           saved=32L  ~64min
  medium activity_enabled                    saved=30L  ~60min
  medium provision_cursor                    saved=30L  ~60min
  ... +124 more (~2494min)

METRICS-TARGET:
  dup_groups:  134 → 0
  saved_lines: 1625 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 5592 func | 542f | 2026-06-07
# generated in 0.02s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           packages/coru/src/coru/cli.py
      WHY: 4053L, 3 classes, max CC=26
      EFFORT: ~4h  IMPACT: 105378

  [2] !! SPLIT           src/koru/scan.py
      WHY: 1621L, 0 classes, max CC=13
      EFFORT: ~4h  IMPACT: 21073

  [3] !  SPLIT-FUNC      _auto_ownership_gate  CC=22  fan=20
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 440

  [4] !  SPLIT-FUNC      action_status  CC=20  fan=20
      WHY: CC=20 exceeds 15
      EFFORT: ~1h  IMPACT: 400

  [5] !! SPLIT-FUNC      SharedAutopilotBridgePaste.shouldProbeInput  CC=26  fan=14
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 364

  [6] !  SPLIT-FUNC      _live_daemon_instance  CC=20  fan=18
      WHY: CC=20 exceeds 15
      EFFORT: ~1h  IMPACT: 360

  [7] !  SPLIT-FUNC      _auto_readiness_gate  CC=22  fan=16
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 352

  [8] !  SPLIT-FUNC      _installed_extension_build_sha  CC=22  fan=16
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 352

  [9] !  SPLIT-FUNC      SharedAutopilotBridgePaste.pasteText  CC=17  fan=20
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 340

  [10] !! SPLIT-FUNC      _infer_default_ide  CC=26  fan=13
      WHY: CC=26 exceeds 15
      EFFORT: ~1h  IMPACT: 338


RISKS[3]:
  ⚠ Splitting packages/coru/src/coru/cli.py may break 187 import paths
  ⚠ Splitting tree.txt may break 0 import paths
  ⚠ Splitting src/koru/scan.py may break 61 import paths

METRICS-TARGET:
  CC̄:          3.7 → ≤2.6
  max-CC:      26 → ≤13
  god-modules: 43 → 0
  high-CC(≥15): 48 → ≤24
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
  prev CC̄=3.7 → now CC̄=3.7
```

## Intent

Closed-loop automation across semcod/* repositories.
