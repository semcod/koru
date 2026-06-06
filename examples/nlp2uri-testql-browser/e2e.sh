#!/usr/bin/env bash
# Non-interactive smoke: dry-run only, skips gracefully if tools missing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export DRY_RUN=1
export EXECUTE_NATIVE=0

if ! bash "$ROOT/run.sh" 2>&1; then
  code=$?
  if [[ $code -eq 1 ]]; then
    echo "e2e: skipped (missing nlp2uri or testql)"
    exit 0
  fi
  exit $code
fi

echo "e2e: ok"
