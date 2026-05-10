#!/usr/bin/env bash
# install.sh — idempotent installer for metrun.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję metrun…"

scope="${METRUN_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ METRUN_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v metrun >/dev/null 2>&1 && [ ! -x venv/bin/metrun ]; then
  "$PIP" install "${pip_args[@]}" --upgrade metrun
else
  echo "  ✓ metrun już zainstalowany (upgrade: $PIP install -U metrun)"
fi

if [ -x venv/bin/metrun ]; then BIN=venv/bin/metrun; else BIN="$(command -v metrun || true)"; fi
[ -z "$BIN" ] && { echo "  ✗ metrun nie w PATH" >&2; exit 3; }

if "$BIN" --version 2>&1 | grep -qiE 'metrun|version'; then
  echo "  ✓ $($BIN --version 2>&1 | head -1)"
fi

if "$BIN" --help 2>&1 | head -20 | grep -qE 'Usage|Commands'; then
  echo "  ✓ metrun --help works"
fi

echo "✓ metrun gotowy. See docs/llm-tools/metrun/README.md for workflows."
