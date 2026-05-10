#!/usr/bin/env bash
# install.sh — idempotent installer for redeploy (PyPI: redeploy>=0.2.74).
#
# Part of koru's docs/llm-tools/redeploy/ pattern. Installs into --user
# scope by default; override with REDEPLOY_PIP_SCOPE=venv to use ./venv.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "→ Instaluję redeploy…"

scope="${REDEPLOY_PIP_SCOPE:-user}"
case "$scope" in
  user)
    pip_args=(--user)
    PIP=pip
    ;;
  venv)
    [ -x venv/bin/pip ] || python3 -m venv venv
    pip_args=()
    PIP=venv/bin/pip
    ;;
  current)
    pip_args=()
    PIP=pip
    ;;
  *)
    echo "  ✗ REDEPLOY_PIP_SCOPE must be: user|venv|current" >&2
    exit 2
    ;;
esac

if ! command -v redeploy >/dev/null 2>&1 && [ ! -x venv/bin/redeploy ]; then
  "$PIP" install "${pip_args[@]}" --upgrade redeploy
else
  echo "  ✓ redeploy już zainstalowany (upgrade: $PIP install -U redeploy)"
fi

# Which binary to smoke-test
if [ -x venv/bin/redeploy ]; then
  REDEPLOY=venv/bin/redeploy
else
  REDEPLOY="$(command -v redeploy || true)"
fi

if [ -z "$REDEPLOY" ]; then
  echo "  ✗ redeploy nie w PATH po instalacji — sprawdź pip warnings" >&2
  exit 3
fi

# Smoke test — `redeploy --version`
if "$REDEPLOY" --version 2>&1 | grep -qE 'redeploy|version'; then
  version="$($REDEPLOY --version 2>&1 | head -1)"
  echo "  ✓ $version"
else
  echo "  ⚠ redeploy --version nie zwrócił oczekiwanego output"
fi

# Smoke test — `redeploy run --help`
if "$REDEPLOY" run --help 2>&1 | grep -qiE 'plan-only|dry-run|from-step'; then
  echo "  ✓ redeploy run --help działa (markpact runner ready)"
else
  echo "  ⚠ redeploy run --help nie wspomina markpact opcji — sprawdź wersję"
fi

# Sprawdź czy repo ma już skonfigurowane redeploy/
if [ -d redeploy ]; then
  count=$(find redeploy -maxdepth 2 -name '*.md' -o -name '*.yaml' 2>/dev/null | wc -l)
  echo "  ✓ redeploy/ obecny ($count specs)"
else
  echo "  ℹ  Brak redeploy/ — skopiuj templates:"
  echo "     task template:install:redeploy           # local + device baseline"
  echo "     # albo ręcznie:"
  echo "     mkdir -p redeploy/local redeploy/device"
  echo "     cp templates/redeploy/local/deployment.md.template redeploy/local/deployment.md"
  echo "     cp templates/redeploy/device/* redeploy/device/"
fi

# Companion: doql (drift detection)
if command -v doql >/dev/null 2>&1; then
  echo "  ✓ companion: doql obecny ($(doql --version 2>&1 | head -1))"
else
  echo "  ℹ  companion doql brak — instalacja: pip install --user doql"
fi

echo "✓ redeploy gotowy. Pełny workflow: workflows/redeploy-multi-device.md"
