#!/usr/bin/env bash
# scripts/koru-autoloop.sh — unattended intake/execution loop for koru projects.
#
# Runs forever until Ctrl-C:
#   1) optional `koru scan --apply`
#   2) `koru --queue --loop` drain pass
#   3) optional `koru autopilot drive` handoff ping
#   4) sleep
#
# Configure via env vars (Taskfile wrapper sets sane defaults):
#   PROJECT=/path/to/repo
#   ACTOR=koru-shell
#   QUEUE_NAME=default
#   MAX_ITERATIONS=50
#   SLEEP_SECONDS=120
#   ENABLE_SCAN=true
#   ENABLE_AUTOPILOT_DRIVE=true
#   ENABLE_INTERACTIVE=false
#   DRIVE_PROMPT='continue with the next ticket'

set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
ACTOR="${ACTOR:-koru-shell}"
QUEUE_NAME="${QUEUE_NAME:-}"
MAX_ITERATIONS="${MAX_ITERATIONS:-50}"
SLEEP_SECONDS="${SLEEP_SECONDS:-120}"
ENABLE_SCAN="${ENABLE_SCAN:-true}"
ENABLE_AUTOPILOT_DRIVE="${ENABLE_AUTOPILOT_DRIVE:-true}"
ENABLE_INTERACTIVE="${ENABLE_INTERACTIVE:-false}"
DRIVE_PROMPT="${DRIVE_PROMPT:-continue with the next ticket}"

is_true() {
  case "${1,,}" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "koru-autoloop: missing required command: $1" >&2
    exit 1
  fi
}

on_exit() {
  echo ""
  echo "koru-autoloop: stopped"
}

trap on_exit EXIT

require_cmd koru

if [ ! -d "$PROJECT" ]; then
  echo "koru-autoloop: project directory not found: $PROJECT" >&2
  exit 1
fi

cd "$PROJECT"

echo "koru-autoloop: project=$PROJECT actor=$ACTOR queue=${QUEUE_NAME:-<all>}"
echo "koru-autoloop: max_iterations=$MAX_ITERATIONS sleep=${SLEEP_SECONDS}s"
echo "koru-autoloop: scan=$ENABLE_SCAN autopilot_drive=$ENABLE_AUTOPILOT_DRIVE interactive=$ENABLE_INTERACTIVE"

iteration=0
while true; do
  iteration=$((iteration + 1))
  echo ""
  echo "=== koru-autoloop iteration #$iteration ==="

  if is_true "$ENABLE_SCAN"; then
    echo "+ koru scan --apply"
    if ! koru scan --apply; then
      echo "! scan failed (continuing loop)" >&2
    fi
  fi

  queue_cmd=(
    koru
    --queue
    --project "$PROJECT"
    --loop
    --max-iterations "$MAX_ITERATIONS"
    --actor "$ACTOR"
  )

  if [ -n "$QUEUE_NAME" ]; then
    queue_cmd+=(--queue-name "$QUEUE_NAME")
  fi

  if is_true "$ENABLE_INTERACTIVE"; then
    queue_cmd+=(--interactive)
  fi

  echo "+ ${queue_cmd[*]}"
  if ! "${queue_cmd[@]}"; then
    echo "! queue loop returned non-zero (continuing loop)" >&2
  fi

  if is_true "$ENABLE_AUTOPILOT_DRIVE"; then
    echo "+ koru autopilot drive '<prompt>'"
    if ! koru autopilot drive "$DRIVE_PROMPT"; then
      echo "! autopilot drive failed (continuing loop)" >&2
    fi
  fi

  echo "... sleeping ${SLEEP_SECONDS}s"
  sleep "$SLEEP_SECONDS"
done
