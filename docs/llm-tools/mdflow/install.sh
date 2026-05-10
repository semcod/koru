#!/usr/bin/env bash
# install.sh — idempotent installer for mdflow.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję mdflow…"

scope="${MDFLOW_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ MDFLOW_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v mdflow >/dev/null 2>&1 && [ ! -x venv/bin/mdflow ]; then
  "$PIP" install "${pip_args[@]}" --upgrade mdflow
else
  echo "  ✓ mdflow już zainstalowany (upgrade: $PIP install -U mdflow)"
fi

if [ -x venv/bin/mdflow ]; then BIN=venv/bin/mdflow; else BIN="$(command -v mdflow || true)"; fi
[ -z "$BIN" ] && { echo "  ✗ mdflow nie w PATH" >&2; exit 3; }

if "$BIN" --version 2>&1 | grep -qiE 'mdflow|version'; then
  echo "  ✓ $($BIN --version 2>&1 | head -1)"
fi

if "$BIN" --help 2>&1 | head -20 | grep -qE 'Usage|Commands'; then
  echo "  ✓ mdflow --help works"
fi

echo "✓ mdflow gotowy. See docs/llm-tools/mdflow/README.md for workflows."
