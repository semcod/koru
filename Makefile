SHELL := /usr/bin/env bash

PYTHON ?= python3

PYTEST_WORKERS ?= auto
PYTEST_DIST ?= loadfile
PYTEST_ARGS ?=

KORU_PYTEST_ENV := KORU_PYTEST_WORKERS="$(PYTEST_WORKERS)" KORU_PYTEST_DIST="$(PYTEST_DIST)"

.PHONY: test test-fast test-parallel test-parallel-fast test-python-parallel test-api-parallel

test:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS)

test-fast:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --quick $(PYTEST_ARGS)

test-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 $(PYTEST_ARGS)

test-parallel-fast:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --changed --quick $(PYTEST_ARGS)

test-python-parallel: test-parallel

test-api-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 \
		tests/test_koruapi.py \
		tests/test_koruapi_transports.py \
		tests/test_dashboard_projects_by_ide.py \
		tests/test_dashboard_topology_post.py \
		tests/test_mcp_server.py \
		$(PYTEST_ARGS)

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
