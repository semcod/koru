#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
STATE_FILE="${STATE_FILE:-$PROJECT/.planfile/.koru/autonomous-state.json}"
LOG_FILE="${LOG_FILE:-$PROJECT/.planfile/.koru/soak.log}"
REPORT_FILE="${REPORT_FILE:-$PROJECT/.planfile/.koru/soak-stop-report.md}"
PROCESS_PATTERN="${PROCESS_PATTERN:-autonomous up.*--max-cycles 0}"
MONITOR_PATTERN="${MONITOR_PATTERN:-koru-soak-monitor.sh}"
TICKET_ID="${TICKET_ID:-STARTER-009}"
MARK_DONE="${MARK_DONE:-false}"
FORCE_REPORT_OVERWRITE="${FORCE_REPORT_OVERWRITE:-false}"

find_pid() {
  pgrep -fo "$1" || true
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

pid_elapsed() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    echo "0"
    return 0
  fi
  ps -o etimes= -p "$pid" | awk '{print $1}'
}

write_report() {
  local soak_pid="$1"
  local monitor_pid="$2"
  local elapsed="$3"
  local cycle="$4"
  local queue_status="$5"
  local waiting_ticket="$6"

  mkdir -p "$(dirname "$REPORT_FILE")"
  cat > "$REPORT_FILE" <<EOF
# Soak Stop Report

Date: $(date -Iseconds)

- Ticket: $TICKET_ID
- Soak PID: ${soak_pid:--}
- Monitor PID: ${monitor_pid:--}
- Soak uptime seconds: $elapsed
- Current cycle: ${cycle:--}
- Queue status: ${queue_status:--}
- Waiting ticket: ${waiting_ticket:--}
- State file: $STATE_FILE
- Log file: $LOG_FILE
- Mark done requested: $MARK_DONE
EOF
}

cd "$PROJECT"

soak_pid="$(find_pid "$PROCESS_PATTERN")"
monitor_pid="$(find_pid "$MONITOR_PATTERN")"
elapsed="$(pid_elapsed "$soak_pid")"
cycle="$(state_field cycle)"
queue_status="$(state_field queue_status)"
waiting_ticket="$(state_field waiting_ticket)"

if [[ -z "$soak_pid" && -z "$monitor_pid" && -f "$REPORT_FILE" && "$FORCE_REPORT_OVERWRITE" != "true" ]]; then
  echo "soak_pid=-"
  echo "monitor_pid=-"
  echo "elapsed_seconds=0"
  echo "cycle=${cycle:--}"
  echo "queue_status=${queue_status:--}"
  echo "waiting_ticket=${waiting_ticket:--}"
  echo "report_file=$REPORT_FILE"
  echo "note=existing_report_preserved"
  if [[ "$MARK_DONE" == "true" ]] && command -v planfile >/dev/null 2>&1; then
    planfile ticket update "$TICKET_ID" --status done >/dev/null 2>&1 || true
  fi
  exit 0
fi

if [[ -n "$monitor_pid" ]]; then
  kill "$monitor_pid" || true
fi

if [[ -n "$soak_pid" ]]; then
  kill "$soak_pid" || true
fi

write_report "$soak_pid" "$monitor_pid" "$elapsed" "$cycle" "$queue_status" "$waiting_ticket"

if [[ "$MARK_DONE" == "true" ]] && command -v planfile >/dev/null 2>&1; then
  planfile ticket update "$TICKET_ID" --status done >/dev/null 2>&1 || true
fi

echo "soak_pid=${soak_pid:--}"
echo "monitor_pid=${monitor_pid:--}"
echo "elapsed_seconds=$elapsed"
echo "cycle=${cycle:--}"
echo "queue_status=${queue_status:--}"
echo "waiting_ticket=${waiting_ticket:--}"
echo "report_file=$REPORT_FILE"
