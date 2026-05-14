#!/bin/bash
# Autopilot Unix-socket broker without any IDE plugin (doc + smoke).
set -euo pipefail

koru --help >/dev/null
koru autopilot doctor --format json | python3 -c "import json,sys; json.load(sys.stdin)"
koru autopilot ide-list

demo="$(mktemp -d)"
trap 'rm -rf "$demo"' EXIT
cd "$demo"
git init -q
koru --init --project . --agent-lane none

sock="/tmp/koru-autopilot-e2e.sock"
rm -f "$sock"

koru autopilot --socket "$sock" daemon --no-handoff --project "$demo" &
dpid=$!
sleep 0.4

koru autopilot --socket "$sock" status
koru autopilot --socket "$sock" shutdown || true
wait "$dpid" 2>/dev/null || true

echo "koru autopilot: socket smoke OK (no IDE plugin connected — expected)."
