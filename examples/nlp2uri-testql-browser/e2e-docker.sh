#!/usr/bin/env bash
# Docker smoke: nlp2uri plan/execute + testql OQL/TestTOON, all in --dry-run.
# Live DOM mode still needs a native browser + playwright (see README.md).
set -euo pipefail

export DRY_RUN=1
export EXECUTE_NATIVE=0

bash /opt/koru/examples/nlp2uri-testql-browser/run.sh

echo "e2e: ok"
