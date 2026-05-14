#!/usr/bin/env bash
# Run every nested Docker E2E example under examples/<category>/<name>/.
# Invoke from the koru repository root (parent of this script's directory).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; skipping examples E2E." >&2
  exit 0
fi

mapfile -t EXAMPLES < <(
  find "$ROOT/examples" -mindepth 3 -maxdepth 3 -type f -name run-docker.sh -print \
    | LC_ALL=C sort
)

if ((${#EXAMPLES[@]} == 0)); then
  echo "no examples/**/run-docker.sh found under $ROOT/examples" >&2
  exit 1
fi

failed=0
for script in "${EXAMPLES[@]}"; do
  dir="$(dirname "$script")"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "==> $(realpath --relative-to="$ROOT" "$dir")"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if (cd "$dir" && ./run-docker.sh); then
    echo "OK: $dir"
  else
    echo "FAIL: $dir" >&2
    failed=1
  fi
done

if ((failed)); then
  exit 1
fi
echo ""
echo "All example Docker E2E runs passed."
