#!/usr/bin/env bash
# install.sh — idempotent installer for doql.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję doql…"

scope="${DOQL_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ DOQL_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v doql >/dev/null 2>&1 && [ ! -x venv/bin/doql ]; then
  "$PIP" install "${pip_args[@]}" --upgrade doql
else
  echo "  ✓ doql już zainstalowany (upgrade: $PIP install -U doql)"
fi

if [ -x venv/bin/doql ]; then DOQL=venv/bin/doql; else DOQL="$(command -v doql || true)"; fi
[ -z "$DOQL" ] && { echo "  ✗ doql nie w PATH" >&2; exit 3; }

if "$DOQL" --version 2>&1 | grep -qiE 'doql|version'; then
  echo "  ✓ $($DOQL --version 2>&1 | head -1)"
fi

# Smoke test: subcommands listed
if "$DOQL" --help 2>&1 | grep -qE 'adopt|drift|build'; then
  echo "  ✓ doql --help shows core commands (adopt/drift/build)"
else
  echo "  ⚠ doql --help nie pokazuje oczekiwanych komend"
fi

# Sprawdź czy projekt ma app.doql.less
if [ -f app.doql.less ]; then
  echo "  ✓ app.doql.less obecny ($(wc -l < app.doql.less) linii)"
else
  echo "  ℹ  Brak app.doql.less — wygeneruj baseline:"
  echo "     $DOQL adopt . -f         # auto-detect z istniejącego repo"
  echo "     $DOQL init               # interactive template wizard"
  echo "     # albo via sumd:"
  echo "     sumd .                  # generates SUMR.md + app.doql.less"
fi

echo "✓ doql gotowy. Quick start:  doql validate  →  doql plan  →  doql build"
