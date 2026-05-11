#!/usr/bin/env bash
# scripts/koru-autoloop.sh — unattended intake/execution loop for koru projects.
#
# Per cycle:
#   1) optional `koru scan --apply`                   (ENABLE_SCAN / TICKET_SOURCES)
#   2) `koru --queue --loop` drain pass               (parses last_status=idle|…)
#   3) optional idle diagnostics                      (ENABLE_IDLE_DIAGNOSTICS)
#        regix / wup / redup / testql / redsl / sumr
#        on failure: optional [AUTO-DIAG] ticket      (ENABLE_DIAGNOSTIC_TICKETS)
#   4) optional autopilot drive|handoff               (ENABLE_AUTOPILOT_DRIVE)
#   5) sleep SLEEP_SECONDS
# Stops when MAX_CYCLES reached (0 = infinite) or Ctrl-C.
#
# Env vars (every flag is optional, sane defaults applied):
#
#   Core:
#     PROJECT=/path/to/repo          (default: cwd)
#     ACTOR=koru-shell               (alias: ACTOR_NAME)
#     QUEUE_NAME=                    (empty + USE_ALL_QUEUES=false => default queue)
#     USE_ALL_QUEUES=false
#     MAX_ITERATIONS=50              (inner --loop iterations)
#     MAX_CYCLES=0                   (outer cycles; 0 = infinite)
#     SLEEP_SECONDS=120
#     INITIAL_DELAY_SECONDS=0
#
#   Intake:
#     ENABLE_SCAN=true
#     TICKET_SOURCES=queue           (queue|scan|all; 'all' forces scan + all-queues
#                                     + full idle diagnostics + diag tickets)
#
#   Execution:
#     ENABLE_INTERACTIVE=false
#
#   Autopilot:
#     ENABLE_AUTOPILOT_DRIVE=true
#     AUTOPILOT_ACTION=drive         (drive|handoff|off)
#     AUTOPILOT_IDE=auto
#     AUTOPILOT_SUBMIT=true
#     AUTOPILOT_ON_IDLE_ONLY=false
#     AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL=true
#     DRIVE_PROMPT='continue with the next ticket'
#
#   Diagnostics (only run when queue drained to idle):
#     ENABLE_IDLE_DIAGNOSTICS=false
#     IDLE_DIAGNOSTICS_PROFILE=quick (off|quick|full)
#     STRICT_DIAGNOSTICS=false       (exit 2 on diag failure)
#     ENABLE_DIAGNOSTIC_TICKETS=false
#     DIAGNOSTIC_TICKET_QUEUE=default
#     DIAGNOSTIC_TICKET_PRIORITY=high
#     DIAG_STATE_DIR=.planfile/.koru/autoloop-diag
#
#   Command overrides (for source installs / monorepos):
#     KORU_CMD='koru'                 (or 'python3 -m koru.cli')
#     KORU_PLANFILE_CMD='planfile'    (or 'python3 -m planfile.cli')
#     KORU_PYTHONPATH=...             (prepended to PYTHONPATH)

set -euo pipefail

# --------------------------------------------------------------------------- env
PROJECT="${PROJECT:-$(pwd)}"
ACTOR="${ACTOR:-${ACTOR_NAME:-koru-shell}}"
QUEUE_NAME="${QUEUE_NAME:-}"
USE_ALL_QUEUES="${USE_ALL_QUEUES:-false}"
MAX_ITERATIONS="${MAX_ITERATIONS:-50}"
MAX_CYCLES="${MAX_CYCLES:-0}"
SLEEP_SECONDS="${SLEEP_SECONDS:-120}"
INITIAL_DELAY_SECONDS="${INITIAL_DELAY_SECONDS:-0}"

ENABLE_SCAN="${ENABLE_SCAN:-true}"
TICKET_SOURCES="${TICKET_SOURCES:-queue}"

ENABLE_INTERACTIVE="${ENABLE_INTERACTIVE:-false}"

ENABLE_AUTOPILOT_DRIVE="${ENABLE_AUTOPILOT_DRIVE:-true}"
AUTOPILOT_ACTION="${AUTOPILOT_ACTION:-drive}"
AUTOPILOT_IDE="${AUTOPILOT_IDE:-auto}"
AUTOPILOT_SUBMIT="${AUTOPILOT_SUBMIT:-true}"
AUTOPILOT_ON_IDLE_ONLY="${AUTOPILOT_ON_IDLE_ONLY:-false}"
AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL="${AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL:-true}"
DRIVE_PROMPT="${DRIVE_PROMPT:-continue with the next ticket}"

ENABLE_IDLE_DIAGNOSTICS="${ENABLE_IDLE_DIAGNOSTICS:-false}"
IDLE_DIAGNOSTICS_PROFILE="${IDLE_DIAGNOSTICS_PROFILE:-quick}"
STRICT_DIAGNOSTICS="${STRICT_DIAGNOSTICS:-false}"
ENABLE_DIAGNOSTIC_TICKETS="${ENABLE_DIAGNOSTIC_TICKETS:-false}"
DIAGNOSTIC_TICKET_QUEUE="${DIAGNOSTIC_TICKET_QUEUE:-default}"
DIAGNOSTIC_TICKET_PRIORITY="${DIAGNOSTIC_TICKET_PRIORITY:-high}"
DIAG_STATE_DIR="${DIAG_STATE_DIR:-.planfile/.koru/autoloop-diag}"

KORU_CMD="${KORU_CMD:-koru}"
KORU_PLANFILE_CMD="${KORU_PLANFILE_CMD:-planfile}"
export KORU_PLANFILE_CMD
if [ -n "${KORU_PYTHONPATH:-}" ]; then
  export PYTHONPATH="${KORU_PYTHONPATH}:${PYTHONPATH:-}"
fi

read -ra KORU_INVOKE <<< "$KORU_CMD"

# --------------------------------------------------------------------------- helpers
is_true() {
  case "${1,,}" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

run_koru() {
  "${KORU_INVOKE[@]}" "$@"
}

on_exit() {
  echo ""
  echo "koru-autoloop: stopped"
}
trap on_exit EXIT

if [ ! -d "$PROJECT" ]; then
  echo "koru-autoloop: project directory not found: $PROJECT" >&2
  exit 1
fi
cd "$PROJECT"

# Resolve ticket_sources preset -> effective flags
effective_enable_scan="$ENABLE_SCAN"
effective_use_all_queues="$USE_ALL_QUEUES"
effective_enable_idle_diagnostics="$ENABLE_IDLE_DIAGNOSTICS"
effective_idle_profile="$IDLE_DIAGNOSTICS_PROFILE"
effective_enable_diag_tickets="$ENABLE_DIAGNOSTIC_TICKETS"
ticket_sources_lc="${TICKET_SOURCES,,}"
case "$ticket_sources_lc" in
  queue|default|none) ;;
  scan)
    effective_enable_scan=true
    ;;
  all)
    effective_enable_scan=true
    effective_use_all_queues=true
    effective_enable_idle_diagnostics=true
    effective_idle_profile=full
    effective_enable_diag_tickets=true
    ;;
  *)
    echo "! unknown TICKET_SOURCES=$TICKET_SOURCES (expected: queue|scan|all), using queue" >&2
    ;;
esac

mkdir -p "$DIAG_STATE_DIR"

clear_diag_marker() {
  rm -f "$DIAG_STATE_DIR/${1}.failed"
}

mark_diag_failure() {
  local check_id="$1"
  local summary="$2"
  diag_failed=true
  if ! is_true "$effective_enable_diag_tickets"; then
    return
  fi
  local marker="$DIAG_STATE_DIR/${check_id}.failed"
  if [ -f "$marker" ]; then
    echo "- diagnostic ticket marker exists for ${check_id}, skipping create"
    return
  fi
  local title="[AUTO-DIAG] ${check_id} needs attention"
  local prompt="${title} in cycle ${cycle}. queue_status=${queue_last_status}. Check: ${summary}. Investigate and fix regression, stale quality artifact, or broken diagnostic gate."
  if run_koru task "$prompt" --project . --queue-name "$DIAGNOSTIC_TICKET_QUEUE" --priority "$DIAGNOSTIC_TICKET_PRIORITY"; then
    touch "$marker"
    echo "+ created diagnostic ticket for ${check_id} (queue=${DIAGNOSTIC_TICKET_QUEUE})"
  else
    echo "! failed to create diagnostic ticket for ${check_id}" >&2
  fi
}

run_check() {
  # run_check <check_id> <guard_cmd> <summary> <cmd...>
  local check_id="$1" guard="$2" summary="$3"; shift 3
  if ! eval "$guard" >/dev/null 2>&1; then
    echo "- ${check_id} unavailable (${summary}), skipping"
    return
  fi
  echo "+ $*"
  if ! "$@"; then
    echo "! ${check_id} failed (continuing loop)" >&2
    mark_diag_failure "$check_id" "$summary"
  else
    clear_diag_marker "$check_id"
  fi
}

run_idle_diagnostics() {
  local profile_lc="${effective_idle_profile,,}"
  diag_failed=false
  if [ "$profile_lc" = "off" ] || [ "$profile_lc" = "none" ]; then
    echo "koru:autoloop queue idle -> diagnostics profile=off (skipping)"
    diag_status="off"
    return
  fi
  echo "koru:autoloop queue idle -> running semcod diagnostics (profile=${profile_lc})"

  run_check regix 'command -v regix' \
    'regix compare HEAD --local --format rich' \
    regix compare HEAD --local --format rich

  if command -v wup >/dev/null 2>&1 && [ -f wup.yaml ]; then
    run_check wup 'command -v wup' 'wup status' wup status
  else
    echo "- wup missing or wup.yaml absent, skipping"
  fi

  if [ "$profile_lc" = "full" ] || [ "$profile_lc" = "deep" ]; then
    run_check redup 'command -v redup' \
      'redup scan . --min-lines 10' \
      redup scan . --min-lines 10

    if command -v testql >/dev/null 2>&1; then
      if find . -name '*.testql.toon.yaml' -print -quit | grep -q .; then
        run_check testql 'command -v testql' \
          'testql suite --pattern *.testql.toon.yaml --output console --fail-fast' \
          testql suite --pattern '*.testql.toon.yaml' --output console --fail-fast
      else
        echo "- no *.testql.toon.yaml scenarios found, skipping"
      fi
    else
      echo "- testql not found, skipping"
    fi

    run_check redsl 'command -v redsl' 'redsl gate check .' redsl gate check .

    if [ -f scripts/sumr-refresh.sh ]; then
      run_check sumr 'test -f scripts/sumr-refresh.sh' \
        'bash scripts/sumr-refresh.sh --status' \
        bash scripts/sumr-refresh.sh --status
    else
      echo "- scripts/sumr-refresh.sh not found, skipping"
    fi
  fi

  if [ "$diag_failed" = "true" ]; then
    diag_status="failed"
  else
    diag_status="ok"
  fi
}

run_autopilot() {
  local submit_flag=()
  if ! is_true "$AUTOPILOT_SUBMIT"; then
    submit_flag=(--no-submit)
  fi
  local action_lc="${AUTOPILOT_ACTION,,}"
  case "$action_lc" in
    drive)
      echo "+ koru autopilot drive --ide $AUTOPILOT_IDE '$DRIVE_PROMPT'"
      if run_koru autopilot drive --ide "$AUTOPILOT_IDE" "${submit_flag[@]}" "$DRIVE_PROMPT"; then
        autopilot_status="ok"
      else
        echo "! autopilot drive failed (continuing loop)" >&2
        autopilot_status="failed"
      fi
      ;;
    handoff)
      echo "+ koru autopilot handoff --project . --ide $AUTOPILOT_IDE"
      if run_koru autopilot handoff --project . --ide "$AUTOPILOT_IDE" "${submit_flag[@]}"; then
        autopilot_status="ok"
      else
        echo "! autopilot handoff failed (continuing loop)" >&2
        autopilot_status="failed"
      fi
      ;;
    off|none|disabled)
      echo "- autopilot action set to $action_lc, skipping"
      autopilot_status="skipped"
      ;;
    *)
      echo "! unknown AUTOPILOT_ACTION=$AUTOPILOT_ACTION (expected: drive|handoff|off)" >&2
      autopilot_status="failed"
      ;;
  esac
}

# --------------------------------------------------------------------------- banner
cycle=0
echo "koru:autoloop project=$PROJECT actor=$ACTOR queue=${QUEUE_NAME:-<all>} max_iterations=$MAX_ITERATIONS"
echo "koru:autoloop scan=$ENABLE_SCAN autopilot_drive=$ENABLE_AUTOPILOT_DRIVE interactive=$ENABLE_INTERACTIVE"
echo "koru:autoloop ticket_sources=$TICKET_SOURCES -> scan=$effective_enable_scan use_all_queues=$effective_use_all_queues idle_diag=$effective_enable_idle_diagnostics profile=$effective_idle_profile"
echo "koru:autoloop diagnostic_tickets=$effective_enable_diag_tickets queue=$DIAGNOSTIC_TICKET_QUEUE priority=$DIAGNOSTIC_TICKET_PRIORITY"
echo "koru:autoloop strict_diagnostics=$STRICT_DIAGNOSTICS autopilot_skip_on_diag_fail=$AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL"

if [ "$INITIAL_DELAY_SECONDS" != "0" ]; then
  echo "koru:autoloop initial delay ${INITIAL_DELAY_SECONDS}s"
  sleep "$INITIAL_DELAY_SECONDS"
fi

# --------------------------------------------------------------------------- main loop
while true; do
  cycle=$((cycle + 1))
  echo ""
  echo "=== koru:autoloop cycle #${cycle} ==="

  if is_true "$effective_enable_scan"; then
    echo "+ koru scan --apply"
    if ! run_koru scan --project . --apply; then
      echo "! scan failed (continuing loop)" >&2
    fi
  fi

  queue_cmd=(
    "${KORU_INVOKE[@]}"
    --queue
    --project .
    --actor "$ACTOR"
    --loop
    --max-iterations "$MAX_ITERATIONS"
  )
  if ! is_true "$effective_use_all_queues" && [ -n "$QUEUE_NAME" ]; then
    queue_cmd+=(--queue-name "$QUEUE_NAME")
  fi
  if is_true "$ENABLE_INTERACTIVE"; then
    queue_cmd+=(--interactive)
  fi

  queue_last_status="unknown"
  queue_idle=false
  echo "+ ${queue_cmd[*]}"
  set +e
  queue_output=$("${queue_cmd[@]}" 2>&1)
  queue_status=$?
  set -e
  printf '%s\n' "$queue_output"
  if [ "$queue_status" -ne 0 ]; then
    echo "! queue loop returned non-zero (continuing loop)" >&2
  fi
  queue_last_status=$(printf '%s\n' "$queue_output" | sed -n 's/.*last_status=\([^ ]*\).*/\1/p' | tail -n1)
  [ -z "$queue_last_status" ] && queue_last_status="unknown"
  if printf '%s\n' "$queue_output" | grep -q 'last_status=idle'; then
    queue_idle=true
  fi

  diag_status="skipped"
  if is_true "$effective_enable_idle_diagnostics" && [ "$queue_idle" = "true" ]; then
    run_idle_diagnostics
  fi

  if is_true "$STRICT_DIAGNOSTICS" && [ "$diag_status" = "failed" ]; then
    echo "koru:autoloop strict diagnostics enabled -> stopping on diagnostics failure" >&2
    echo "koru:autoloop summary cycle=${cycle} queue=${queue_last_status} diagnostics=${diag_status} autopilot=skipped(strict)" >&2
    exit 2
  fi

  autopilot_status="skipped"
  if is_true "$ENABLE_AUTOPILOT_DRIVE"; then
    should_run=true
    if is_true "$AUTOPILOT_ON_IDLE_ONLY" && [ "$queue_idle" != "true" ]; then
      should_run=false
    fi
    if is_true "$AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL" && [ "$diag_status" = "failed" ]; then
      should_run=false
    fi
    if [ "$should_run" = "true" ]; then
      run_autopilot
    fi
  fi

  echo "koru:autoloop summary cycle=${cycle} queue=${queue_last_status} diagnostics=${diag_status} autopilot=${autopilot_status}"

  if [ "$MAX_CYCLES" != "0" ] && [ "${cycle}" -ge "$MAX_CYCLES" ]; then
    echo "koru:autoloop reached MAX_CYCLES=${MAX_CYCLES} — stopping"
    break
  fi

  echo "... sleeping ${SLEEP_SECONDS}s"
  sleep "$SLEEP_SECONDS"
done
