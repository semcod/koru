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
# Env vars (every flag is optional, sane defaults applied).
# Default *names and string defaults* are duplicated in Python as
# ``koru.autonomy.env.AUTOLOOP_ENV_DEFAULTS`` — update both when adding knobs.
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
#     AUTOPILOT_ENSURE_DAEMON=true  (start plugin daemon in background before drive)
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
#     REGIX_DIAGNOSTIC_CMD='regix compare HEAD --local --format rich'
#     REDUP_DIAGNOSTIC_CMD='python3 -m redup scan . --min-lines 10'
#     TESTQL_DIAGNOSTIC_CMD="testql suite --pattern '*.testql.toon.yaml' --output console --fail-fast"
#
#   Stagnation control (avoid hammering a stuck waiting_input):
#     AUTOPILOT_SKIP_STATUSES=waiting_input   (comma-list of statuses for which
#                                              autopilot drive is skipped on the
#                                              SECOND+ consecutive cycle with the
#                                              same status+waiting_ticket_id)
#     AUTOPILOT_SKIP_DRIVE_IDLE_STREAK=0      (when >0, skip autopilot drive when
#                                              queue is idle and stagnation_streak
#                                              reaches this threshold; same counter
#                                              as BACKOFF_ON_STAGNATION)
#     BACKOFF_ON_STAGNATION=true              (when (status,waiting_id) repeats,
#                                              multiply SLEEP_SECONDS by 2^streak,
#                                              capped at MAX_SLEEP_SECONDS)
#     MAX_SLEEP_SECONDS=900                   (0 = no backoff)
#     SCAN_SKIP_IF_CLEAN=false                (skip `koru scan --apply` when
#                                              previous scan reported clean and
#                                              git HEAD has not moved)
#     SCAN_SKIP_AFTER=1                       (min consecutive clean scans
#                                              required before skipping kicks in)
#
#   Topology integration (from `.koru/topology.yaml` via `koru topology`):
#     TOPOLOGY_INTEGRATION=true
#       - when true, autoloop respects component/pipeline toggles:
#           pipeline `scan:on-change`   -> controls scan phase
#           pipeline `autoloop:queue`   -> controls queue drain phase
#           pipeline `idle-diagnostics` -> controls diagnostics phase
#           pipeline `autopilot:drive`  -> controls autopilot phase
#           component ids in diagnostics checks (regix/wup/redup/testql/redsl/sumr)
#             control each individual check
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
AUTOPILOT_ENSURE_DAEMON="${AUTOPILOT_ENSURE_DAEMON:-true}"
AUTOPILOT_DAEMON_READY_TIMEOUT_SECONDS="${AUTOPILOT_DAEMON_READY_TIMEOUT_SECONDS:-5}"
AUTOPILOT_DAEMON_LOG="${AUTOPILOT_DAEMON_LOG:-.planfile/.koru/autopilot-daemon.log}"
DRIVE_PROMPT="${DRIVE_PROMPT:-continue with the next ticket}"

ENABLE_IDLE_DIAGNOSTICS="${ENABLE_IDLE_DIAGNOSTICS:-false}"
IDLE_DIAGNOSTICS_PROFILE="${IDLE_DIAGNOSTICS_PROFILE:-quick}"
STRICT_DIAGNOSTICS="${STRICT_DIAGNOSTICS:-false}"
ENABLE_DIAGNOSTIC_TICKETS="${ENABLE_DIAGNOSTIC_TICKETS:-false}"
DIAGNOSTIC_TICKET_QUEUE="${DIAGNOSTIC_TICKET_QUEUE:-default}"
DIAGNOSTIC_TICKET_PRIORITY="${DIAGNOSTIC_TICKET_PRIORITY:-high}"
DIAG_STATE_DIR="${DIAG_STATE_DIR:-.planfile/.koru/autoloop-diag}"
REGIX_DIAGNOSTIC_CMD="${REGIX_DIAGNOSTIC_CMD:-regix compare HEAD --local --format rich}"
REDUP_DIAGNOSTIC_CMD="${REDUP_DIAGNOSTIC_CMD:-python3 -m redup scan . --min-lines 10}"
TESTQL_DIAGNOSTIC_CMD="${TESTQL_DIAGNOSTIC_CMD:-testql suite --pattern '*.testql.toon.yaml' --output console --fail-fast}"

AUTOPILOT_SKIP_STATUSES="${AUTOPILOT_SKIP_STATUSES:-waiting_input}"
AUTOPILOT_SKIP_DRIVE_IDLE_STREAK="${AUTOPILOT_SKIP_DRIVE_IDLE_STREAK:-0}"
BACKOFF_ON_STAGNATION="${BACKOFF_ON_STAGNATION:-true}"
MAX_SLEEP_SECONDS="${MAX_SLEEP_SECONDS:-900}"
SCAN_SKIP_IF_CLEAN="${SCAN_SKIP_IF_CLEAN:-false}"
SCAN_SKIP_AFTER="${SCAN_SKIP_AFTER:-1}"
TOPOLOGY_INTEGRATION="${TOPOLOGY_INTEGRATION:-true}"

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

autopilot_daemon_pid=""

ensure_autopilot_daemon() {
  if ! is_true "$AUTOPILOT_ENSURE_DAEMON"; then
    return 0
  fi

  set +e
  run_koru autopilot status >/dev/null 2>&1
  local status_rc=$?
  set -e
  if [ "$status_rc" -eq 0 ]; then
    return 0
  fi

  mkdir -p "$(dirname "$AUTOPILOT_DAEMON_LOG")"
  echo "+ koru autopilot daemon --idempotent --no-handoff (background)"
  run_koru autopilot daemon --idempotent --no-handoff --project . >"$AUTOPILOT_DAEMON_LOG" 2>&1 &
  autopilot_daemon_pid=$!

  local attempts timeout_seconds
  timeout_seconds="${AUTOPILOT_DAEMON_READY_TIMEOUT_SECONDS%.*}"
  if ! [[ "$timeout_seconds" =~ ^[0-9]+$ ]]; then
    timeout_seconds=5
  fi
  [ "$timeout_seconds" -lt 1 ] && timeout_seconds=1
  attempts=$((timeout_seconds * 5))

  while [ "$attempts" -gt 0 ]; do
    set +e
    run_koru autopilot status >/dev/null 2>&1
    status_rc=$?
    kill -0 "$autopilot_daemon_pid" >/dev/null 2>&1
    local daemon_alive=$?
    set -e
    if [ "$status_rc" -eq 0 ]; then
      return 0
    fi
    if [ "$daemon_alive" -ne 0 ]; then
      echo "! autopilot daemon exited before becoming ready (see $AUTOPILOT_DAEMON_LOG)" >&2
      return 1
    fi
    sleep 0.2
    attempts=$((attempts - 1))
  done

  echo "! autopilot daemon did not become ready within ${timeout_seconds}s (see $AUTOPILOT_DAEMON_LOG)" >&2
  return 1
}

status_in_skip_list() {
  # status_in_skip_list <status>
  local needle="$1"
  local IFS=,
  for item in $AUTOPILOT_SKIP_STATUSES; do
    item="${item// /}"
    [ -z "$item" ] && continue
    if [ "${item,,}" = "${needle,,}" ]; then
      return 0
    fi
  done
  return 1
}

current_head() {
  git -C "$PROJECT" rev-parse HEAD 2>/dev/null || echo ""
}

init_topology_support() {
  topology_supported=false
  if ! is_true "$TOPOLOGY_INTEGRATION"; then
    return
  fi
  set +e
  run_koru topology --project . --is-enabled koru >/dev/null 2>&1
  rc=$?
  set -e
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
    topology_supported=true
  fi
}

topology_is_enabled() {
  # topology_is_enabled <id> <fallback_bool>
  local key="$1" fallback="$2"
  if [ "$topology_supported" != "true" ]; then
    is_true "$fallback"
    return
  fi
  set +e
  run_koru topology --project . --is-enabled "$key" >/dev/null 2>&1
  local rc=$?
  set -e
  case "$rc" in
    0) return 0 ;;
    1) return 1 ;;
    *)
      is_true "$fallback"
      return
      ;;
  esac
}

compute_backoff_sleep() {
  # compute_backoff_sleep <base> <streak> <cap> -> echoes seconds
  local base="$1" streak="$2" cap="$3"
  if [ "$streak" -le 0 ] || ! is_true "$BACKOFF_ON_STAGNATION"; then
    echo "$base"
    return
  fi
  local mult=1 i=0 limit="$streak"
  [ "$limit" -gt 10 ] && limit=10
  while [ "$i" -lt "$limit" ]; do
    mult=$((mult * 2))
    i=$((i + 1))
  done
  local candidate=$((base * mult))
  if [ "$cap" -gt 0 ] && [ "$candidate" -gt "$cap" ]; then
    candidate="$cap"
  fi
  echo "$candidate"
}

parse_waiting_ticket_id() {
  # Extract first ticket id from `waiting:   PLF-110` line in queue output.
  printf '%s\n' "$1" \
    | sed -n 's/^[[:space:]]*waiting:[[:space:]]*\([^[:space:]]\{1,\}\).*/\1/p' \
    | head -n1
}

on_exit() {
  if [ -n "$autopilot_daemon_pid" ] && kill -0 "$autopilot_daemon_pid" >/dev/null 2>&1; then
    kill "$autopilot_daemon_pid" >/dev/null 2>&1 || true
  fi
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
  if ! topology_is_enabled "$check_id" true; then
    echo "- ${check_id} disabled in topology, skipping"
    return
  fi
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

run_check_shell() {
  # run_check_shell <check_id> <guard_cmd> <summary> <shell_cmd>
  local check_id="$1" guard="$2" summary="$3" shell_cmd="$4"
  if ! topology_is_enabled "$check_id" true; then
    echo "- ${check_id} disabled in topology, skipping"
    return
  fi
  if ! eval "$guard" >/dev/null 2>&1; then
    echo "- ${check_id} unavailable (${summary}), skipping"
    return
  fi
  echo "+ $shell_cmd"
  if ! bash -lc "$shell_cmd"; then
    echo "! ${check_id} failed (continuing loop)" >&2
    mark_diag_failure "$check_id" "$summary"
  else
    clear_diag_marker "$check_id"
  fi
}

cmd_is_disabled() {
  case "${1,,}" in
    ""|off|none|disabled|skip) return 0 ;;
    *) return 1 ;;
  esac
}

run_idle_diagnostics() {
  local profile_lc="${effective_idle_profile,,}"
  diag_failed=false
  if ! topology_is_enabled "idle-diagnostics" true; then
    echo "koru:autoloop queue idle -> idle-diagnostics disabled in topology"
    diag_status="disabled(topology)"
    return
  fi
  if [ "$profile_lc" = "off" ] || [ "$profile_lc" = "none" ]; then
    echo "koru:autoloop queue idle -> diagnostics profile=off (skipping)"
    diag_status="off"
    return
  fi
  echo "koru:autoloop queue idle -> running semcod diagnostics (profile=${profile_lc})"

  if ! cmd_is_disabled "$REGIX_DIAGNOSTIC_CMD"; then
    run_check_shell regix 'command -v regix' \
      "$REGIX_DIAGNOSTIC_CMD" \
      "$REGIX_DIAGNOSTIC_CMD"
  else
    echo "- REGIX_DIAGNOSTIC_CMD disabled, skipping regix"
  fi

  if command -v wup >/dev/null 2>&1 && [ -f wup.yaml ]; then
    run_check wup 'command -v wup' 'wup status' wup status
  else
    echo "- wup missing or wup.yaml absent, skipping"
  fi

  if [ "$profile_lc" = "full" ] || [ "$profile_lc" = "deep" ]; then
    if ! cmd_is_disabled "$REDUP_DIAGNOSTIC_CMD"; then
      run_check_shell redup 'python3 -m redup --help >/dev/null 2>&1' \
        "$REDUP_DIAGNOSTIC_CMD" \
        "$REDUP_DIAGNOSTIC_CMD"
    else
      echo "- REDUP_DIAGNOSTIC_CMD disabled, skipping redup"
    fi

    if command -v testql >/dev/null 2>&1; then
      if ! cmd_is_disabled "$TESTQL_DIAGNOSTIC_CMD"; then
        run_check_shell testql 'command -v testql' \
          "$TESTQL_DIAGNOSTIC_CMD" \
          "$TESTQL_DIAGNOSTIC_CMD"
      elif find . -name '*.testql.toon.yaml' -print -quit | grep -q .; then
        echo "- TESTQL_DIAGNOSTIC_CMD disabled, skipping testql"
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
      if ensure_autopilot_daemon && run_koru autopilot drive --ide "$AUTOPILOT_IDE" "${submit_flag[@]}" "$DRIVE_PROMPT"; then
        autopilot_status="ok"
      else
        echo "! autopilot drive failed (continuing loop)" >&2
        autopilot_status="failed"
      fi
      ;;
    handoff)
      echo "+ koru autopilot handoff --project . --ide $AUTOPILOT_IDE"
      if ensure_autopilot_daemon && run_koru autopilot handoff --project . --ide "$AUTOPILOT_IDE" "${submit_flag[@]}"; then
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
init_topology_support
echo "koru:autoloop project=$PROJECT actor=$ACTOR queue=${QUEUE_NAME:-<all>} max_iterations=$MAX_ITERATIONS"
echo "koru:autoloop scan=$ENABLE_SCAN autopilot_drive=$ENABLE_AUTOPILOT_DRIVE interactive=$ENABLE_INTERACTIVE"
echo "koru:autoloop ticket_sources=$TICKET_SOURCES -> scan=$effective_enable_scan use_all_queues=$effective_use_all_queues idle_diag=$effective_enable_idle_diagnostics profile=$effective_idle_profile"
echo "koru:autoloop diagnostic_tickets=$effective_enable_diag_tickets queue=$DIAGNOSTIC_TICKET_QUEUE priority=$DIAGNOSTIC_TICKET_PRIORITY"
echo "koru:autoloop strict_diagnostics=$STRICT_DIAGNOSTICS autopilot_skip_on_diag_fail=$AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL"
echo "koru:autoloop stagnation: skip_statuses=$AUTOPILOT_SKIP_STATUSES skip_idle_streak=${AUTOPILOT_SKIP_DRIVE_IDLE_STREAK:-0} backoff=$BACKOFF_ON_STAGNATION max_sleep=${MAX_SLEEP_SECONDS}s scan_skip_if_clean=$SCAN_SKIP_IF_CLEAN"
echo "koru:autoloop topology_integration=$TOPOLOGY_INTEGRATION topology_supported=${topology_supported}"

if [ "$INITIAL_DELAY_SECONDS" != "0" ]; then
  echo "koru:autoloop initial delay ${INITIAL_DELAY_SECONDS}s"
  sleep "$INITIAL_DELAY_SECONDS"
fi

# --------------------------------------------------------------------------- main loop
prev_signature=""
stagnation_streak=0
scan_clean_streak=0
scan_last_head=""

while true; do
  cycle=$((cycle + 1))
  echo ""
  echo "=== koru:autoloop cycle #${cycle} ==="

  # ----- scan -------------------------------------------------------------
  if is_true "$effective_enable_scan"; then
    if ! topology_is_enabled "scan:on-change" true; then
      echo "- koru scan --apply skipped (scan:on-change disabled in topology)"
    else
      head_now=$(current_head)
      if is_true "$SCAN_SKIP_IF_CLEAN" \
         && [ "$scan_clean_streak" -ge "$SCAN_SKIP_AFTER" ] \
         && [ -n "$head_now" ] \
         && [ "$head_now" = "$scan_last_head" ]; then
        echo "- koru scan --apply skipped (clean_streak=$scan_clean_streak, HEAD unchanged)"
      else
        echo "+ koru scan --apply"
        set +e
        scan_output=$(run_koru scan --project . --apply 2>&1)
        scan_rc=$?
        set -e
        printf '%s\n' "$scan_output"
        if [ "$scan_rc" -ne 0 ]; then
          echo "! scan failed (continuing loop)" >&2
          scan_clean_streak=0
        elif printf '%s\n' "$scan_output" | grep -q 'no suggestions'; then
          scan_clean_streak=$((scan_clean_streak + 1))
          scan_last_head="$head_now"
        else
          scan_clean_streak=0
          scan_last_head="$head_now"
        fi
      fi
    fi
  fi

  # ----- queue ------------------------------------------------------------
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
  if ! topology_is_enabled "autoloop:queue" true; then
    echo "- autoloop queue phase skipped (autoloop:queue disabled in topology)"
    queue_output=""
    queue_last_status="disabled"
  else
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
  fi
  waiting_ticket_id=$(parse_waiting_ticket_id "$queue_output")

  # ----- stagnation tracking ---------------------------------------------
  cur_signature="${queue_last_status}:${waiting_ticket_id}"
  if [ -n "$prev_signature" ] && [ "$cur_signature" = "$prev_signature" ]; then
    stagnation_streak=$((stagnation_streak + 1))
  else
    stagnation_streak=0
  fi
  prev_signature="$cur_signature"

  # ----- diagnostics ------------------------------------------------------
  diag_status="skipped"
  if is_true "$effective_enable_idle_diagnostics" && [ "$queue_idle" = "true" ]; then
    run_idle_diagnostics
  fi

  if is_true "$STRICT_DIAGNOSTICS" && [ "$diag_status" = "failed" ]; then
    echo "koru:autoloop strict diagnostics enabled -> stopping on diagnostics failure" >&2
    echo "koru:autoloop summary cycle=${cycle} queue=${queue_last_status} diagnostics=${diag_status} autopilot=skipped(strict)" >&2
    exit 2
  fi

  # ----- autopilot --------------------------------------------------------
  autopilot_status="skipped"
  if is_true "$ENABLE_AUTOPILOT_DRIVE"; then
    if ! topology_is_enabled "autopilot:drive" true; then
      echo "- autopilot skipped (autopilot:drive disabled in topology)"
      autopilot_status="skipped(topology)"
    else
      should_run=true
      skip_reason=""
      if is_true "$AUTOPILOT_ON_IDLE_ONLY" && [ "$queue_idle" != "true" ]; then
        should_run=false; skip_reason="idle_only"
      fi
      if is_true "$AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL" && [ "$diag_status" = "failed" ]; then
        should_run=false; skip_reason="diagnostics_fail"
      fi
      if [ "$stagnation_streak" -gt 0 ] && status_in_skip_list "$queue_last_status"; then
        should_run=false
        skip_reason="stuck_${queue_last_status}_streak_${stagnation_streak}"
      fi
      if [ "$should_run" = "true" ] \
        && [ "${AUTOPILOT_SKIP_DRIVE_IDLE_STREAK:-0}" -gt 0 ] \
        && [ "$queue_idle" = "true" ] \
        && [ "$stagnation_streak" -ge "$AUTOPILOT_SKIP_DRIVE_IDLE_STREAK" ]; then
        should_run=false
        skip_reason="idle_streak"
      fi
      if [ "$should_run" = "true" ]; then
        run_autopilot
      elif [ -n "$skip_reason" ]; then
        echo "- autopilot skipped (${skip_reason})"
        autopilot_status="skipped(${skip_reason})"
      fi
    fi
  fi

  # ----- summary + backoff sleep -----------------------------------------
  effective_sleep=$(compute_backoff_sleep "$SLEEP_SECONDS" "$stagnation_streak" "$MAX_SLEEP_SECONDS")
  echo "koru:autoloop summary cycle=${cycle} queue=${queue_last_status} waiting=${waiting_ticket_id:-none} streak=${stagnation_streak} diagnostics=${diag_status} autopilot=${autopilot_status} sleep=${effective_sleep}s"

  if [ "$MAX_CYCLES" != "0" ] && [ "${cycle}" -ge "$MAX_CYCLES" ]; then
    echo "koru:autoloop reached MAX_CYCLES=${MAX_CYCLES} — stopping"
    break
  fi

  echo "... sleeping ${effective_sleep}s"
  sleep "$effective_sleep"
done
