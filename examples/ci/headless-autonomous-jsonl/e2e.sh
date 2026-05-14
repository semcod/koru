#!/bin/bash
# Headless CI: one autonomous cycle, autopilot off, NDJSON on stdout.
set -euo pipefail

koru --help >/dev/null
koru --doctor --project /tmp 2>/dev/null || true

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
  --emit-events jsonl \
  --agent-lane none \
  | tee "$tmp"

grep -q '"type": "SessionStarted"' "$tmp" || grep -q '"type":"SessionStarted"' "$tmp"
