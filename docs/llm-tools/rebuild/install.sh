#!/usr/bin/env bash
# install.sh — idempotent installer for rebuild.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję rebuild…"

scope="${REBUILD_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ REBUILD_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v rebuild >/dev/null 2>&1 && [ ! -x venv/bin/rebuild ]; then
  "$PIP" install "${pip_args[@]}" --upgrade rebuild
else
  echo "  ✓ rebuild już zainstalowany (upgrade: $PIP install -U rebuild)"
fi

if [ -x venv/bin/rebuild ]; then BIN=venv/bin/rebuild; else BIN="$(command -v rebuild || true)"; fi
[ -z "$BIN" ] && { echo "  ✗ rebuild nie w PATH" >&2; exit 3; }

if "$BIN" --version 2>&1 | grep -qiE 'rebuild|version'; then
  echo "  ✓ $($BIN --version 2>&1 | head -1)"
fi

if "$BIN" --help 2>&1 | head -20 | grep -qE 'Usage|Commands'; then
  echo "  ✓ rebuild --help works"
fi

echo "✓ rebuild gotowy. See docs/llm-tools/rebuild/README.md for workflows."
