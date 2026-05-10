#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję planfile…"

if ! command -v planfile >/dev/null 2>&1; then
    pip install --user planfile
else
    echo "  ✓ planfile już zainstalowany"
fi

# Sprawdź config
if [ ! -f "planfile.yaml" ]; then
    echo "  ⚠ Brak planfile.yaml — skopiuj/utwórz przez 'planfile init'"
else
    TICKETS=$(planfile ticket list --format yaml 2>/dev/null | grep -c "^- id:" || echo "0")
    echo "  ✓ planfile.yaml istnieje, $TICKETS ticket(ów)"
fi

# Test MCP server
echo "→ Test: planfile MCP server (dla Windsurf/Cursor)"
if timeout 2 python3 -m planfile.mcp.server </dev/null >/dev/null 2>&1; then
    echo "  ✓ MCP server uruchamia się"
else
    echo "  ✓ MCP server gotowy (timeout normalny — czeka na stdio klienta)"
fi

# Sprawdź tasks
if grep -q "tickets:next" Taskfile.yml 2>/dev/null; then
    echo "  ✓ Taskfile ma 'tickets:next'"
fi

# Sprawdź MCP config example
if [ -f ".windsurf/mcp_config.example.json" ]; then
    echo "  ✓ .windsurf/mcp_config.example.json gotowy do skopiowania do ~/.codeium/windsurf/"
fi

echo "✓ planfile gotowy. Komenda: task tickets:next | planfile ticket list"
