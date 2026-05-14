#!/bin/bash
# Optional: planfile HTTP API + curl (skips if module layout unavailable).
set -euo pipefail

koru --help >/dev/null
planfile --version

if ! python3 -c "from planfile.api.server import app" 2>/dev/null; then
  echo "SKIP: planfile.api.server not importable in this environment."
  exit 0
fi

uvicorn planfile.api.server:app --host 127.0.0.1 --port 18888 &
apid=$!
cleanup() { kill "$apid" 2>/dev/null || true; }
trap cleanup EXIT
sleep 1

curl -fsS http://127.0.0.1:18888/health
