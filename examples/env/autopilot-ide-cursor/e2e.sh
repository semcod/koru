#!/bin/bash
# Env matrix: KORU_AUTOPILOT_IDE=cursor overrides CLI autopilot-ide when not "auto".
set -euo pipefail
export KORU_AUTOPILOT_IDE=cursor

koru --help >/dev/null

demo="$(mktemp -d)"
trap 'rm -rf "$demo"' EXIT
cd "$demo"
git init -q
koru --init --project . --agent-lane none
koru --doctor --project .

tmp="$(mktemp)"
# CLI says auto; env forces cursor for autopilot resolution (see autonomous._resolve_autopilot_ide).
koru autonomous up \
  --project . \
  --max-cycles 1 \
  --sleep-seconds 0 \
  --ticket-sources queue \
  --no-autopilot \
  --autopilot-ide auto \
  --emit-events jsonl \
  --agent-lane none \
  2>&1 | tee "$tmp"

grep -q SessionStarted "$tmp"
# Env must win over CLI "auto": resolution has to land on cursor.
grep -qE 'autopilot IDE=cursor \(from ' "$tmp"
