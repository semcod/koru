#!/usr/bin/env bash
# install.sh — idempotent installer for op3.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję op3…"

scope="${OP3_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ OP3_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v op3 >/dev/null 2>&1 && [ ! -x venv/bin/op3 ]; then
  "$PIP" install "${pip_args[@]}" --upgrade op3
else
  echo "  ✓ op3 już zainstalowany (upgrade: $PIP install -U op3)"
fi

if [ -x venv/bin/op3 ]; then OP3=venv/bin/op3; else OP3="$(command -v op3 || true)"; fi
[ -z "$OP3" ] && { echo "  ✗ op3 nie w PATH" >&2; exit 3; }

if "$OP3" --version 2>&1 | grep -qiE 'op3|version'; then
  echo "  ✓ $($OP3 --version 2>&1 | head -1)"
fi

# Smoke test: scan/diff commands available
if "$OP3" --help 2>&1 | grep -qE 'scan|diff'; then
  echo "  ✓ op3 --help shows core commands (scan/diff)"
fi

# Sprawdź Python API import
if python3 -c "from opstree import LayerTree, scan_device" 2>/dev/null; then
  echo "  ✓ Python API import OK (opstree.LayerTree, scan_device)"
else
  echo "  ⚠ Python API nie importuje się — sprawdź pip install"
fi

# Companion: doql obecny?
if command -v doql >/dev/null 2>&1; then
  echo "  ✓ companion: doql obecny ($(doql --version 2>&1 | head -1))"
else
  echo "  ℹ  companion doql brak — instalacja: pip install --user doql"
fi

echo "✓ op3 gotowy. Quick start:  op3 scan localhost --layers physical,service"
