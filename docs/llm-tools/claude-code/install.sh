#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Konfiguruję c2004 dla Claude Code…"

# Sprawdź claude-code (wymaga npm)
if ! command -v claude-code >/dev/null 2>&1; then
    echo "  ⚠ claude-code nie zainstalowany"
    if command -v npm >/dev/null 2>&1; then
        echo "    Aby zainstalować: npm install -g @anthropic-ai/claude-code"
    else
        echo "    Wymaga npm — zainstaluj Node.js: https://nodejs.org"
    fi
fi

# Auth
if [ -f "$HOME/.claude/auth.json" ]; then
    echo "  ✓ ~/.claude/auth.json istnieje"
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "  ✓ ANTHROPIC_API_KEY ustawione w env"
else
    echo "  ⚠ Brak auth — uruchom: claude-code login"
    echo "    LUB: export ANTHROPIC_API_KEY=sk-ant-..."
fi

# Project settings (opcjonalnie)
if [ ! -d ".claude" ]; then
    echo "→ Tworzę .claude/ z domyślnymi ustawieniami…"
    mkdir -p .claude
    cat > .claude/settings.json <<EOF
{
  "model": "claude-sonnet-4-5",
  "permissions": {
    "edit_files": true,
    "run_commands": true,
    "git_commit": false
  },
  "rules_file": "docs/windsurf-agent-guide.md"
}
EOF
    echo "  ✓ .claude/settings.json"

    # gitignore
    if ! grep -q "^.claude/" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        echo "# Claude Code per-user settings" >> .gitignore
        echo ".claude/auth.json" >> .gitignore
    fi
fi

# Sprawdź że rules są dostępne
if [ -f "docs/windsurf-agent-guide.md" ]; then
    echo "  ✓ Rules file dostępny: docs/windsurf-agent-guide.md"
fi

echo "✓ Claude Code config gotowy. Komenda: claude-code 'Napraw PLF-021'"
echo "  ⚠ Anthropic API jest płatne — preferuj Windsurf gdy dostępny GUI"
