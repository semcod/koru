#!/usr/bin/env bash
# install.sh — idempotent installer for sumd (provides both sumd + sumr CLIs).
#
# Part of koru's docs/llm-tools/sumd/ pattern. Installs into --user scope by
# default; override with SUMD_PIP_SCOPE=venv to use ./venv.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję sumd (CLIs: sumd, sumr)…"

# Allow choosing install target: user (default), venv, or current interpreter.
scope="${SUMD_PIP_SCOPE:-user}"
case "$scope" in
  user)  pip_args=(--user) ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=()
    PIP=venv/bin/pip
    ;;
  current) pip_args=() ;;
  *) echo "  ✗ SUMD_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac
PIP="${PIP:-pip}"

if ! command -v sumd >/dev/null 2>&1 && [ ! -x venv/bin/sumd ]; then
  "$PIP" install "${pip_args[@]}" --upgrade sumd
else
  echo "  ✓ sumd już zainstalowany (upgrade: pip install -U sumd)"
fi

# Which binary to smoke-test
if [ -x venv/bin/sumd ]; then
  SUMD=venv/bin/sumd
  SUMR=venv/bin/sumr
else
  SUMD="$(command -v sumd || true)"
  SUMR="$(command -v sumr || true)"
fi

if [ -z "$SUMD" ] || [ -z "$SUMR" ]; then
  echo "  ✗ sumd/sumr nie w PATH po instalacji — sprawdź pip warnings" >&2
  exit 3
fi

# Smoke test — `sumd --version` powinno zwrócić numer wersji
if "$SUMD" --version 2>&1 | grep -qE '^sumd'; then
  version="$($SUMD --version | head -1)"
  echo "  ✓ $version"
else
  echo "  ⚠ sumd --version nie zwrócił oczekiwanego output"
fi

# Smoke test — `sumr --help` powinno wspomnieć refactor profile
if "$SUMR" --help 2>&1 | grep -qi 'refactor'; then
  echo "  ✓ sumr --help działa (refactor profile dostępny)"
else
  echo "  ⚠ sumr --help nie wspomina refactor profile — niestandardowa wersja?"
fi

# Sprawdź czy repo ma już skonfigurowany debounce wrapper
if [ -x scripts/sumr-refresh.sh ]; then
  echo "  ✓ scripts/sumr-refresh.sh obecny (debounced wrapper gotowy)"
else
  echo "  ℹ  Nie ma scripts/sumr-refresh.sh — zainstaluj template:"
  echo "     cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh"
  echo "     chmod +x scripts/sumr-refresh.sh"
fi

# Sprawdź czy istnieje SUMR.md (pierwszy refresh potrzebny?)
if [ -f SUMR.md ]; then
  size=$(stat -c '%s' SUMR.md 2>/dev/null || wc -c < SUMR.md)
  echo "  ✓ SUMR.md istnieje (${size} bytes)"
else
  echo "  ℹ  Brak SUMR.md — pierwszy refresh:"
  echo "     $SUMR ."
fi

echo "✓ sumd/sumr gotowy. Pełny workflow: workflows/sumr-refresh-loop.md"
