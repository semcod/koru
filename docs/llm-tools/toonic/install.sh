#!/usr/bin/env bash
# install.sh — idempotent installer for toonic.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję toonic…"

scope="${TOONIC_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ TOONIC_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v toonic >/dev/null 2>&1 && [ ! -x venv/bin/toonic ]; then
  "$PIP" install "${pip_args[@]}" --upgrade toonic
else
  echo "  ✓ toonic już zainstalowany (upgrade: $PIP install -U toonic)"
fi

if [ -x venv/bin/toonic ]; then TOONIC=venv/bin/toonic; else TOONIC="$(command -v toonic || true)"; fi
[ -z "$TOONIC" ] && { echo "  ✗ toonic nie w PATH" >&2; exit 3; }

if "$TOONIC" --version 2>&1 | grep -qiE 'toonic|version'; then
  echo "  ✓ $($TOONIC --version 2>&1 | head -1)"
fi

# Smoke test: subcommands
if "$TOONIC" --help 2>&1 | grep -qE 'convert|validate|render'; then
  echo "  ✓ toonic --help shows core commands (convert/validate/render)"
fi

# Sprawdź czy projekt ma TOON files
toon_count=$(find . -name '*.toon.yaml' -o -name '*.toon' 2>/dev/null | grep -v -E 'venv/|node_modules/|\.git/' | wc -l)
if [ "$toon_count" -gt 0 ]; then
  echo "  ✓ TOON files w repo: $toon_count"
else
  echo "  ℹ  Brak *.toon.yaml — wygeneruj np.:"
  echo "     redup scan . --format toon --output redup.toon.yaml"
  echo "     code2llm . -f toon -o project.toon.yaml"
fi

echo "✓ toonic gotowy. Quick start:  toonic convert input.yaml -o output.toon.yaml"
