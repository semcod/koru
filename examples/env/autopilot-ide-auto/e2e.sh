#!/bin/bash
# KORU_AUTOPILOT_IDE=auto does not override explicit CLI IDE (see autonomous.py).
set -euo pipefail
export KORU_AUTOPILOT_IDE=auto

koru --help >/dev/null

demo="$(mktemp -d)"
trap 'rm -rf "$demo"' EXIT
cd "$demo"
git init -q
koru --init --project . --agent-lane none
koru --doctor --project .

tmp="$(mktemp)"
koru autonomous up \
  --project . \
  --max-cycles 1 \
  --sleep-seconds 0 \
  --ticket-sources queue \
  --no-autopilot \
  --autopilot-ide cursor \
  --emit-events jsonl \
  --agent-lane none \
  2>&1 | tee "$tmp"

grep -q SessionStarted "$tmp"
# Explicit CLI must win: env auto may not downgrade --autopilot-ide cursor.
grep -q 'autopilot IDE=cursor (from cli:cursor' "$tmp"
