#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
STATE_FILE="${STATE_FILE:-$PROJECT/.planfile/.koru/autonomous-state.json}"
LOG_FILE="${LOG_FILE:-$PROJECT/.planfile/.koru/soak.log}"
MONITOR_LOG_FILE="${MONITOR_LOG_FILE:-$PROJECT/.planfile/.koru/soak-monitor.log}"
FINAL_REPORT_FILE="${FINAL_REPORT_FILE:-$PROJECT/.planfile/.koru/soak-final-report.md}"
PROCESS_PATTERN="${PROCESS_PATTERN:-autonomous up.*--max-cycles 0}"
MONITOR_PATTERN="${MONITOR_PATTERN:-koru-soak-monitor.sh}"
TICKET_ID="${TICKET_ID:-STARTER-009}"

find_pid() {
  pgrep -fo "$1" || true
}

pid_etime() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    echo "-"
    return 0
  fi
  ps -o etime= -p "$pid" | awk '{$1=$1; print $0}'
}

state_field() {
  local field="$1"
  if [[ ! -f "$STATE_FILE" ]]; then
    echo ""
    return 0
  fi
  python3 - "$STATE_FILE" "$field" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
value = payload.get(field, "")
if value is None:
    value = ""
print(value)
PY
}

error_count() {
  local soak_pid="$1"
  if [[ -z "$soak_pid" ]]; then
    echo "-"
    return 0
  fi
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "0"
    return 0
  fi
  local matches
  matches="$(tail -n 500 "$LOG_FILE" | grep -Ei "ERROR|Traceback|exception|failed" || true)"
  printf '%s\n' "$matches" | sed '/^$/d' | wc -l | awk '{print $1}'
}

ticket_status() {
  if ! command -v planfile >/dev/null 2>&1; then
    echo "unknown"
    return 0
  fi
  planfile ticket show "$TICKET_ID" 2>/dev/null \
    | sed -n 's/^status:[[:space:]]*//p' \
    | head -n1 \
    || true
}

cd "$PROJECT"

soak_pid="$(find_pid "$PROCESS_PATTERN")"
monitor_pid="$(find_pid "$MONITOR_PATTERN")"
cycle="$(state_field cycle)"
queue_status="$(state_field queue_status)"
waiting_ticket="$(state_field waiting_ticket)"
errors="$(error_count "$soak_pid")"
ticket="$(ticket_status)"

echo "soak_pid=${soak_pid:--}"
echo "soak_uptime=$(pid_etime "$soak_pid")"
echo "monitor_pid=${monitor_pid:--}"
echo "monitor_uptime=$(pid_etime "$monitor_pid")"
echo "current_cycle=${cycle:--}"
echo "queue_status=${queue_status:--}"
echo "waiting_ticket=${waiting_ticket:--}"
echo "error_scan_count=${errors:--}"
echo "ticket_id=$TICKET_ID"
echo "ticket_status=${ticket:--}"
echo "state_file_present=$([[ -f "$STATE_FILE" ]] && echo yes || echo no)"
echo "log_file_present=$([[ -f "$LOG_FILE" ]] && echo yes || echo no)"
echo "monitor_log_present=$([[ -f "$MONITOR_LOG_FILE" ]] && echo yes || echo no)"
echo "final_report_present=$([[ -f "$FINAL_REPORT_FILE" ]] && echo yes || echo no)"