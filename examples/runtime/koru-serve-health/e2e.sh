#!/bin/bash
# koru serve — local dashboard /health probe (stdlib http.server stack).
set -euo pipefail

koru --help >/dev/null

demo="$(mktemp -d)"
cd "$demo"
git init -q
koru --init --project . --agent-lane none
koru --doctor --project .

koru serve --project . --host 127.0.0.1 --port 18765 --no-open &
spid=$!
sleep 0.6

curl -fsS http://127.0.0.1:18765/health | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('ok') is True"

kill "$spid"
wait "$spid" 2>/dev/null || true
rm -rf "$demo"
