#!/usr/bin/env bash
# install.sh — idempotent installer for protogate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję protogate…"

scope="${PROTOGATE_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ PROTOGATE_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v protogate >/dev/null 2>&1 && [ ! -x venv/bin/protogate ]; then
  "$PIP" install "${pip_args[@]}" --upgrade protogate
else
  echo "  ✓ protogate już zainstalowany (upgrade: $PIP install -U protogate)"
fi

if [ -x venv/bin/protogate ]; then BIN=venv/bin/protogate; else BIN="$(command -v protogate || true)"; fi
[ -z "$BIN" ] && { echo "  ✗ protogate nie w PATH" >&2; exit 3; }

if "$BIN" --version 2>&1 | grep -qiE 'protogate|version'; then
  echo "  ✓ $($BIN --version 2>&1 | head -1)"
fi

if "$BIN" --help 2>&1 | head -20 | grep -qE 'Usage|Commands'; then
  echo "  ✓ protogate --help works"
fi

echo "✓ protogate gotowy. See docs/llm-tools/protogate/README.md for workflows."
