#!/usr/bin/env bash
# install.sh — idempotent installer for costs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję costs…"

scope="${COSTS_PIP_SCOPE:-user}"
case "$scope" in
  user)    pip_args=(--user); PIP=pip ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=(); PIP=venv/bin/pip
    ;;
  current) pip_args=(); PIP=pip ;;
  *) echo "  ✗ COSTS_PIP_SCOPE must be: user|venv|current" >&2; exit 2 ;;
esac

if ! command -v costs >/dev/null 2>&1 && [ ! -x venv/bin/costs ]; then
  "$PIP" install "${pip_args[@]}" --upgrade costs
else
  echo "  ✓ costs już zainstalowany (upgrade: $PIP install -U costs)"
fi

if [ -x venv/bin/costs ]; then COSTS=venv/bin/costs; else COSTS="$(command -v costs || true)"; fi
[ -z "$COSTS" ] && { echo "  ✗ costs nie w PATH" >&2; exit 3; }

if "$COSTS" --version 2>&1 | grep -qiE 'costs|version'; then
  echo "  ✓ $($COSTS --version 2>&1 | head -1)"
fi

# Smoke test: subcommands listed
if "$COSTS" --help 2>&1 | grep -qE 'analyze|badge|estimate'; then
  echo "  ✓ costs --help shows core commands (analyze/badge/estimate)"
fi

# Sprawdź czy README ma badge
if [ -f README.md ] && grep -q 'AI%20Cost' README.md 2>/dev/null; then
  echo "  ✓ README.md ma już AI Cost badge"
else
  echo "  ℹ  Brak AI Cost badge w README.md — generuj:"
  echo "     $COSTS init                 # initialize tracking"
  echo "     $COSTS analyze              # analyze git history"
  echo "     $COSTS badge                # add badge to README.md"
fi

echo "✓ costs gotowy. Quick start:  costs init && costs analyze && costs badge"
