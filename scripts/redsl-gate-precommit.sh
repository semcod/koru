#!/usr/bin/env bash
# scripts/redsl-gate-precommit.sh
#
# Pre-commit gate driver — runs `redsl gate check` against the working tree
# inside the dockerised quality stack. Wired from .pre-commit-config.yaml.
#
# Behaviour:
#   • If the semcod/redsl:local image is present → run the gate; commit
#     fails on any violation. This is the green-path for engineers who ran
#     `task quality:up` at least once.
#   • Otherwise → print a friendly hint and exit 0 so fresh clones aren't
#     blocked from committing before the quality stack is built.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.quality.yml"

if ! docker image inspect semcod/redsl:local >/dev/null 2>&1; then
  echo "[redsl-gate] semcod/redsl:local not built — skipping."
  echo "[redsl-gate] Run \`task quality:up\` once to enable the pre-commit gate."
  exit 0
fi

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "[redsl-gate] docker-compose.quality.yml missing at ${COMPOSE_FILE}"
  exit 0
fi

exec docker compose -f "${COMPOSE_FILE}" run --rm --no-deps redsl-agent \
  python -m redsl gate check /mnt/project
