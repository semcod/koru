SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

IMGL_ROOT ?= $(HOME)/github/semcod/imgl
IMGL_IMAGE ?= /tmp/koru-imgl-screen.png
IMGL_WINDOW ?= region-bottom

PYTEST_WORKERS ?= auto
PYTEST_DIST ?= loadfile
PYTEST_ARGS ?=

KORU_PYTEST_ENV := KORU_PYTEST_WORKERS="$(PYTEST_WORKERS)" KORU_PYTEST_DIST="$(PYTEST_DIST)"

.PHONY: help test test-fast test-parallel test-parallel-fast test-python-parallel test-api-parallel
.PHONY: install-imgl-bridge test-imgl imgl-capture imgl-capture-interactive imgl-key imgl-type imgl-chat imgl-execute imgl-execute-dry imgl-doctor imgl-shot imgl-serve-rest

help:
	@echo "koru — Makefile"
	@echo ""
	@echo "Testy:"
	@echo "  make test                 pełny pytest"
	@echo "  make test-fast            krytyczne / szybkie"
	@echo "  make test-imgl            integracja imgl"
	@echo ""
	@echo "imgl bridge (vision UI):"
	@echo "  make install-imgl-bridge  koru/.venv + imgl + dsl2coru"
	@echo "  make imgl-capture         zrzut → $(IMGL_IMAGE) (bez dialogu)"
	@echo "  make imgl-capture-interactive  portal GNOME — wybierz obszar"
	@echo "  make imgl-key             UI_KEY ctrl+Return (dry-run)"
	@echo "  make imgl-type            wpisz test w Chat input (dry-run)"
	@echo "  make imgl-chat            TYPE + KEY (dry-run)"
	@echo "  make imgl-shot PROMPT='wpisz hello'          capture-interactive + execute (szybko)"
	@echo "  make imgl-execute PROMPT='wpisz hello'       wpisuje na pulpit (zrzut <60s)"
	@echo "  make imgl-execute-dry PROMPT='wpisz hello'   tylko plan (dry-run)"
	@echo "  make imgl-doctor          autodiagnostyka zrzutu (img2nl)"
	@echo "  make imgl-serve-rest      rest2imgl :8219 (w IMGL_ROOT)"
	@echo ""
	@echo "Release: make build | publish | packages-build"

test:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS)

test-fast:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --quick $(PYTEST_ARGS)

test-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --fast --maxfail=1 $(PYTEST_ARGS)

test-parallel-fast:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --changed --critical --quick $(PYTEST_ARGS)

test-python-parallel: test-parallel

test-api-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 \
		tests/test_koruapi.py \
		tests/test_koruapi_transports.py \
		tests/test_dashboard_projects_by_ide.py \
		tests/test_dashboard_topology_post.py \
		tests/test_mcp_server.py \
		$(PYTEST_ARGS)

install-imgl-bridge: $(VENV)/.imgl-bridge-installed

$(VENV)/.imgl-bridge-installed:
	@test -x "$(VENV)/bin/python" || (echo "Brak $(VENV) — uruchom make install-dev lub python -m venv .venv" && exit 1)
	IMGL_ROOT="$(IMGL_ROOT)" bash scripts/install-imgl-bridge.sh
	@touch "$(VENV)/.imgl-bridge-installed"

test-imgl:
	$(PY) -m pytest tests/test_imgl_integration.py packages/dsl2coru/tests/test_dsl2coru_ui.py -q

imgl-capture:
	@test -x "$(IMGL_ROOT)/.venv/bin/imgl" || (echo "Brak $(IMGL_ROOT)/.venv — cd $(IMGL_ROOT) && make install-dev" && exit 1)
	@$(IMGL_ROOT)/.venv/bin/imgl capture --smart -o "$(IMGL_IMAGE)"
	@echo "export KORU_IMGL_IMAGE=$(IMGL_IMAGE)"

imgl-capture-interactive:
	@test -x "$(IMGL_ROOT)/.venv/bin/imgl" || (echo "Brak $(IMGL_ROOT)/.venv — cd $(IMGL_ROOT) && make install-dev" && exit 1)
	@rm -f "$(IMGL_IMAGE:.png=.vql.imgl.json)" "$(IMGL_IMAGE:.png=.vql.json)" "$(IMGL_IMAGE:.png=.captured_at)" "$(IMGL_IMAGE)"
	@$(IMGL_ROOT)/.venv/bin/imgl capture -o "$(IMGL_IMAGE)" --verify
	@rm -f "$(IMGL_IMAGE:.png=.vql.imgl.json)" "$(IMGL_IMAGE:.png=.vql.json)"
	@echo "export KORU_IMGL_IMAGE=$(IMGL_IMAGE)"

imgl-key: install-imgl-bridge
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_KEY ctrl+Return'

imgl-type: install-imgl-bridge imgl-capture
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_TYPE "test" IN "Chat input" WINDOW $(IMGL_WINDOW)'

imgl-chat: install-imgl-bridge imgl-capture
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_TYPE "demo" IN "Chat input" WINDOW $(IMGL_WINDOW)'
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_KEY ctrl+Return'

imgl-execute: $(VENV)/.imgl-bridge-installed
	@test -f "$(IMGL_IMAGE)" || (echo "Brak zrzutu — najpierw: make imgl-capture-interactive" && exit 1)
	@test -n "$(PROMPT)" || (echo "Użycie: make imgl-execute PROMPT='wpisz test w Chat input'" && exit 1)
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl execute "$(PROMPT)" --image $(IMGL_IMAGE) --window $(IMGL_WINDOW) --execute --format $(or $(FORMAT),markdown)

imgl-execute-dry: $(VENV)/.imgl-bridge-installed
	@test -f "$(IMGL_IMAGE)" || (echo "Brak zrzutu — najpierw: make imgl-capture-interactive" && exit 1)
	@test -n "$(PROMPT)" || (echo "Użycie: make imgl-execute-dry PROMPT='wpisz test w Chat input'" && exit 1)
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl execute "$(PROMPT)" --image $(IMGL_IMAGE) --window $(IMGL_WINDOW) --dry-run --format $(or $(FORMAT),markdown)

imgl-shot: imgl-capture-interactive imgl-execute

imgl-doctor: $(VENV)/.imgl-bridge-installed
	IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl doctor --image $(IMGL_IMAGE) --format $(or $(FORMAT),auto)

imgl-serve-rest:
	@test -x "$(IMGL_ROOT)/.venv/bin/rest2imgl" || (cd "$(IMGL_ROOT)" && make install-control)
	$(IMGL_ROOT)/.venv/bin/rest2imgl serve --port 8219

sync-plugin-version:
	python3 scripts/sync-plugin-version.py --ide vscode
	python3 scripts/sync-plugin-version.py --ide cursor

sync-plugin-shared:
	python3 scripts/sync-plugin-shared.py


# =============================================================================
# Release
# =============================================================================

VERSION = $(shell $(PYTHON) scripts/bump_version.py --show)

.PHONY: build clean-dist bump-patch bump-minor bump-major publish publish-test check-dist
.PHONY: packages-build packages-check packages-publish-test packages-publish

PACKAGE_DIRS := $(shell find packages -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)

clean-dist:
	rm -f dist/koru-*

build: clean-dist
	rm -rf build/ *.egg-info src/*.egg-info
	$(PYTHON) -m pip install -q build
	$(PYTHON) -m build
	@echo "✓ Built dist/koru-$(VERSION)*"

check-dist:
	@test -n "$(VERSION)" || (echo "Could not read version from pyproject.toml" && exit 1)
	@test -n "$$(ls dist/koru-$(VERSION)* 2>/dev/null)" || (echo "No artifacts for $(VERSION) in dist/ — run make build" && exit 1)
	@$(PYTHON) -m pip install -q twine
	@$(PYTHON) -m twine check dist/koru-$(VERSION)*

bump-patch:
	@echo "🔢 Bumping patch version..."
	$(PYTHON) scripts/bump_version.py patch

bump-minor:
	@echo "🔢 Bumping minor version..."
	$(PYTHON) scripts/bump_version.py minor

bump-major:
	@echo "🔢 Bumping major version..."
	$(PYTHON) scripts/bump_version.py major

publish-test: build check-dist
	@echo "🚀 Publishing to TestPyPI..."
	@bash -c '\
	if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \
	fi; \
	if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \
		echo "   Skipping upload (dist/koru-$(VERSION)* built and twine-checked)."; \
	else \
		$(PYTHON) -m pip install -q twine && \
		$(PYTHON) -m twine upload --repository testpypi dist/koru-$(VERSION)* && \
		echo "✓ Published koru $(VERSION) to TestPyPI"; \
	fi'

publish:
	@echo "🚀 Publishing to PyPI..."
	@bash -c '\
	if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \
	fi; \
	if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \
		echo "   Example: PYPI_API_TOKEN=pypi-xxx make publish"; \
		exit 1; \
	fi'
	@$(MAKE) bump-patch
	@$(MAKE) build
	@$(MAKE) check-dist
	@echo "📦 Uploading dist/koru-$(VERSION)* to PyPI..."
	@$(PYTHON) -m pip install -q twine
	@$(PYTHON) -m twine upload dist/koru-$(VERSION)*
	@echo "✓ Published koru $(VERSION) to PyPI"


# =============================================================================
# Packages/* release helpers (coru, koruenv, ...)
# =============================================================================

packages-build:
	@set -euo pipefail; \
	if [ -z "$(PACKAGE_DIRS)" ]; then \
		echo "No package directories found under packages/"; \
		exit 1; \
	fi; \
	$(PYTHON) -m pip install -q build; \
	for pkg in $(PACKAGE_DIRS); do \
		if [ ! -f "$$pkg/pyproject.toml" ]; then \
			echo "- skipping $$pkg (no pyproject.toml)"; \
			continue; \
		fi; \
		echo "📦 building $$pkg"; \
		rm -rf "$$pkg/dist" "$$pkg/build" "$$pkg"/*.egg-info "$$pkg/src"/*.egg-info; \
		$(PYTHON) -m build "$$pkg"; \
	done

packages-check:
	@set -euo pipefail; \
	$(PYTHON) -m pip install -q twine; \
	for pkg in $(PACKAGE_DIRS); do \
		if [ ! -f "$$pkg/pyproject.toml" ]; then \
			continue; \
		fi; \
		if ls "$$pkg"/dist/* >/dev/null 2>&1; then \
			echo "🔎 twine check $$pkg/dist/*"; \
			$(PYTHON) -m twine check "$$pkg"/dist/*; \
		else \
			echo "No artifacts in $$pkg/dist (run: make packages-build)"; \
			exit 1; \
		fi; \
	done

packages-publish-test: packages-build packages-check
	@echo "🚀 Publishing packages/* to TestPyPI..."
	@bash -c '\
	if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \
	fi; \
	if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \
		echo "   Skipping upload (artifacts are built and twine-checked)."; \
		exit 0; \
	fi; \
	for pkg in $(PACKAGE_DIRS); do \
		if [ ! -f "$$pkg/pyproject.toml" ]; then \
			continue; \
		fi; \
		echo "⬆️  testpypi upload $$pkg/dist/*"; \
		$(PYTHON) -m twine upload --repository testpypi "$$pkg"/dist/*; \
	done; \
	echo "✓ Published all packages/* to TestPyPI"'

packages-publish: packages-build packages-check
	@echo "🚀 Publishing packages/* to PyPI..."
	@bash -c '\
	if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \
	fi; \
	if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \
		echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \
		exit 1; \
	fi; \
	for pkg in $(PACKAGE_DIRS); do \
		if [ ! -f "$$pkg/pyproject.toml" ]; then \
			continue; \
		fi; \
		echo "⬆️  pypi upload $$pkg/dist/*"; \
		$(PYTHON) -m twine upload "$$pkg"/dist/*; \
	done; \
	echo "✓ Published all packages/* to PyPI"'
