#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE="${KORU_DOCKER_PY_IMAGE:-python:3.13-slim}"
TARGET_TEST="packages/coru/tests/test_coru_cli.py"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for this simulation" >&2
  exit 127
fi

echo "[simulate] image=$IMAGE"
echo "[simulate] phase=targeted lane/socket checks"

docker run --rm -v "$ROOT":/work -w /work "$IMAGE" bash -lc "
  pip install -q pytest &&
  PYTHONPATH=packages/coru/src pytest -q $TARGET_TEST \\
    -k 'workspace_socket_path_drives_default_instance or workspace_socket_path_drives_default_ide or normalize_lane_pair_prefers_instance_ide or run_with_lane_environment_sets_and_restores'
"

echo "[simulate] phase=full coru cli suite"

docker run --rm -v "$ROOT":/work -w /work "$IMAGE" bash -lc "
  pip install -q pytest &&
  PYTHONPATH=packages/coru/src pytest -q $TARGET_TEST
"

echo "[simulate] ok"
