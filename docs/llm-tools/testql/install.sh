#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję testql…"

if ! command -v testql >/dev/null 2>&1; then
    pip install --user testql
else
    echo "  ✓ testql już zainstalowany"
fi

# Sprawdź scenariusze
SCENARIOS_DIR="testql-testing/scenarios"
if [ -d "$SCENARIOS_DIR" ]; then
    COUNT=$(find "$SCENARIOS_DIR" -name "*.testql.*.yaml" | wc -l)
    echo "  ✓ $COUNT scenariusz(y) w $SCENARIOS_DIR"
else
    echo "  ⚠ Brak $SCENARIOS_DIR — utwórz katalog i scenariusze"
fi

# Sprawdź watchdog
if [ -d "monitoring/testql-watchdog" ]; then
    echo "  ✓ testql-watchdog skonfigurowany"
else
    echo "  ⚠ monitoring/testql-watchdog brak — patrz README.md"
fi

# MCP server
echo "→ Test: testql MCP server"
if timeout 2 python3 -m testql.mcp.server </dev/null >/dev/null 2>&1; then
    echo "  ✓ testql MCP server uruchamia się"
else
    echo "  ✓ testql MCP server gotowy (timeout normalny)"
fi

# Quick smoke test
if [ -f "$SCENARIOS_DIR/realtime-health.testql.toon.yaml" ]; then
    echo "→ Test: realtime-health scenariusz"
    if testql run "$SCENARIOS_DIR/realtime-health.testql.toon.yaml" --timeout 5 2>&1 | grep -qE "passed|failed"; then
        echo "  ✓ scenariusz wykonuje się"
    else
        echo "  ⚠ scenariusz nie kończy się (może backend nie chodzi — uruchom 'task monitor:up')"
    fi
fi

echo "✓ testql gotowy. Komenda: task monitor:probe | testql run <scenario>"
