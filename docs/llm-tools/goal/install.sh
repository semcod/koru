#!/usr/bin/env bash
# install.sh — idempotent installer for goal (PyPI: goal>=2.1.218).
#
# Part of koru's docs/llm-tools/goal/ pattern. Installs into --user scope by
# default; override with GOAL_PIP_SCOPE=venv to use ./venv.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję goal…"

scope="${GOAL_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ GOAL_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v goal >/dev/null 2>&1 && [ ! -x venv/bin/goal ]; then
  "$PIP" install "${pip_args[@]}" --upgrade goal
else
  echo "  ✓ goal już zainstalowany (upgrade: $PIP install -U goal)"
fi

# Smoke test
if [ -x venv/bin/goal ]; then GOAL=venv/bin/goal; else GOAL="$(command -v goal || true)"; fi
[ -z "$GOAL" ] && { echo "  ✗ goal nie w PATH" >&2; exit 3; }

if "$GOAL" --version 2>&1 | grep -qiE 'goal|version'; then
  echo "  ✓ $($GOAL --version 2>&1 | head -1)"
else
  echo "  ⚠ goal --version nie zwrócił oczekiwanego output"
fi

# Sprawdź czy repo ma goal.yaml
if [ -f goal.yaml ]; then
  echo "  ✓ goal.yaml obecny ($(wc -l < goal.yaml) linii)"
else
  echo "  ℹ  Brak goal.yaml — initialize:"
  echo "     $GOAL config init           # generate baseline goal.yaml"
fi

# Quick check-versions na repo (jeśli ma pyproject.toml)
if [ -f pyproject.toml ] && [ -n "$GOAL" ]; then
  echo "  ℹ  Run check-versions:  $GOAL check-versions"
fi

echo "✓ goal gotowy. Quick start:  goal commit  (smart conventional commit)"
