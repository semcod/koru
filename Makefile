SHELL := /usr/bin/env bash

PYTEST_WORKERS ?= auto
PYTEST_DIST ?= loadfile
PYTEST_ARGS ?=

KORU_PYTEST_ENV := KORU_PYTEST_WORKERS="$(PYTEST_WORKERS)" KORU_PYTEST_DIST="$(PYTEST_DIST)"

.PHONY: test test-fast test-parallel test-python-parallel test-api-parallel

test:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS)

test-fast:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --quick $(PYTEST_ARGS)

test-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 $(PYTEST_ARGS)

test-python-parallel: test-parallel

test-api-parallel:
	$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 \
		tests/test_koruapi.py \
		tests/test_koruapi_transports.py \
		tests/test_dashboard_projects_by_ide.py \
		tests/test_dashboard_topology_post.py \
		tests/test_mcp_server.py \
		$(PYTEST_ARGS)
