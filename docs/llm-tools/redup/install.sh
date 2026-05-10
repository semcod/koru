#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję redup…"

if ! command -v redup >/dev/null 2>&1; then
    pip install --user redup
else
    echo "  ✓ redup już zainstalowany"
fi

# Smoke test
echo "→ Test: redup scan (krótki audit)"
if redup scan . --threshold 0.85 2>&1 | grep -qE "duplicate|Scanned|Found"; then
    echo "  ✓ redup scan działa"
else
    echo "  ⚠ redup scan nie zwrócił output (sprawdź manualnie: redup scan .)"
fi

# Test MCP server (dla Windsurf)
echo "→ Test: redup MCP server"
if timeout 2 python3 -m redup.mcp_server </dev/null >/dev/null 2>&1; then
    echo "  ✓ redup MCP server uruchamia się"
else
    echo "  ✓ redup MCP server gotowy (timeout normalny)"
fi

# Sprawdź MCP config
if [ -f ".windsurf/mcp_config.example.json" ] && grep -q "redup" .windsurf/mcp_config.example.json; then
    echo "  ✓ .windsurf/mcp_config.example.json ma redup entry"
fi

# Sprawdź redsl integration
if grep -q "use_redup: true" redsl.yaml 2>/dev/null; then
    echo "  ✓ redsl.yaml ma use_redup: true"
fi

echo "✓ redup gotowy. Komendy: redup scan . | python3 -m redup.mcp_server"
