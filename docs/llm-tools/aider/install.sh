#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję aider (dockerised w c2004)…"

# Sprawdź docker
if ! command -v docker >/dev/null 2>&1; then
    echo "  ✗ docker nie zainstalowany — wymagany dla aider"
    exit 1
fi

# Sprawdź docker-compose.yml
if [ ! -f ".aider/docker-compose.yml" ]; then
    echo "  ⚠ Brak .aider/docker-compose.yml — patrz README.md"
    exit 1
fi

# Env
if [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  ✗ Brak OPENROUTER_API_KEY — aider tego wymaga"
    exit 1
fi

# Sprawdź AIDER_MODEL (powinno być deepseek-v4-pro)
if grep -q "openrouter/deepseek/deepseek-v4-pro" .aider/docker-compose.yml 2>/dev/null; then
    echo "  ✓ AIDER_MODEL: deepseek-v4-pro (minimum baseline)"
else
    echo "  ⚠ AIDER_MODEL nie ustawione na deepseek-v4-pro"
fi

# Build image
echo "→ Buduję aider image…"
docker compose -f .aider/docker-compose.yml config >/dev/null  # validate yaml
echo "  ✓ docker-compose.yml OK"

# Sprawdź workflows
for wf in .windsurf/workflows/aider-docker-autoloop.md .windsurf/workflows/testql-autoloop.md; do
    if [ -f "$wf" ]; then
        echo "  ✓ workflow $wf"
    fi
done

# Sprawdź Taskfile
if grep -q "aider:loop" Taskfile.yml 2>/dev/null; then
    echo "  ✓ Taskfile ma aider:loop"
fi

echo "✓ aider gotowy. Komenda: task aider:loop (lub docker compose -f .aider/docker-compose.yml run --rm aider)"
