#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Konfiguruję c2004 dla Cursor IDE…"

# Sprawdź czy Cursor zainstalowany
CURSOR_BIN=$(command -v cursor 2>/dev/null || echo "")
if [ -z "$CURSOR_BIN" ]; then
    echo "  ⚠ Cursor IDE nie zainstalowany (https://cursor.sh)"
    echo "    Mimo to, możesz utworzyć .cursorrules + ~/.cursor/mcp.json"
fi

# .cursorrules — adapter z .windsurf/rules.md
if [ -f ".cursorrules" ]; then
    echo "  ✓ .cursorrules istnieje"
else
    echo "→ Tworzę .cursorrules (na bazie .windsurf/rules.md)…"
    cat > .cursorrules <<'EOF'
# Cursor Rules — c2004

c2004 monorepo uses ticket-driven workflow. Use YOUR LLM (Cursor's), not OpenRouter.

## Workflow
1. `task tickets:next` → highest-priority ticket
2. Read "📂 Likely-affected areas" section
3. Edit code, add regression test (mandatory)
4. `task quality:regix:local` (must show 0 errors)
5. git commit (pre-commit validates LLM-free)
6. `task tickets:done -- PLF-XXX`

## Constraints
- Do NOT modify generated code: **/*_pb2*.py, archive/**
- Do NOT call `redsl improve`, `llx fix`, shell clients via `sllm` (those use external LLM automation)
- Always include regression test
- Patch ≤ 80 lines diff per ticket

## Tools available
- `task tickets:list/next/show/done` — backlog management
- `task quality:regix:local` — regression check (LLM-free)
- `task quality:gate` — quality gate (LLM-free)

## Full guide
See: docs/windsurf-agent-guide.md (Cursor uses identical workflow)
EOF
    echo "  ✓ Utworzono .cursorrules"
fi

# MCP config
CURSOR_MCP="$HOME/.cursor/mcp.json"
if [ -f "$CURSOR_MCP" ]; then
    echo "  ✓ ~/.cursor/mcp.json istnieje (NIE nadpisuję)"
    echo "    Aby dodać c2004 MCP servers, scal ręcznie z:"
    echo "    $REPO_ROOT/docs/llm-tools/cursor/mcp.json.example"
else
    echo "  ⚠ Brak ~/.cursor/mcp.json — Cursor jeszcze nie skonfigurowany"
fi

# Generate example MCP config
cat > /tmp/cursor-mcp-example.json <<EOF
{
  "mcpServers": {
    "planfile": {
      "command": "python3",
      "args": ["-m", "planfile.mcp.server"],
      "env": {"PLANFILE_PROJECT": "$REPO_ROOT"}
    },
    "testql": {
      "command": "python3",
      "args": ["-m", "testql.mcp.server"],
      "env": {"TESTQL_PROJECT": "$REPO_ROOT", "TESTQL_BASE_URL": "http://localhost:8101"}
    },
    "redup": {
      "command": "python3",
      "args": ["-m", "redup.mcp_server"],
      "env": {"REDUP_ROOT": "$REPO_ROOT"}
    }
  }
}
EOF
mkdir -p docs/llm-tools/cursor
cp /tmp/cursor-mcp-example.json docs/llm-tools/cursor/mcp.json.example
rm /tmp/cursor-mcp-example.json
echo "  ✓ docs/llm-tools/cursor/mcp.json.example utworzony"

echo "✓ Cursor config gotowy. Skopiuj mcp.json.example do ~/.cursor/mcp.json"
