#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
TICKET_ID="${TICKET_ID:-STARTER-009}"
MIN_SECONDS="${MIN_SECONDS:-21600}"
POLL_SECONDS="${POLL_SECONDS:-60}"
STATE_FILE="${STATE_FILE:-$PROJECT/.planfile/.koru/autonomous-state.json}"
LOG_FILE="${LOG_FILE:-$PROJECT/.planfile/.koru/soak.log}"
REPORT_FILE="${REPORT_FILE:-$PROJECT/.planfile/.koru/soak-final-report.md}"
PROCESS_PATTERN="${PROCESS_PATTERN:-autonomous up.*--max-cycles 0}"

find_pid() {
  pgrep -fo "$PROCESS_PATTERN" || true
}

pid_elapsed() {
  local pid="$1"
  ps -o etimes= -p "$pid" | awk '{print $1}'
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
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "0"
    return 0
  fi
  local matches
  matches="$(tail -n 500 "$LOG_FILE" | grep -Ei "ERROR|Traceback|exception|failed" || true)"
  printf '%s\n' "$matches" | sed '/^$/d' | wc -l | awk '{print $1}'
}

write_report() {
  local status="$1"
  local pid="$2"
  local elapsed="$3"
  local cycle="$4"
  local queue_status="$5"
  local waiting_ticket="$6"
  local errors="$7"

  mkdir -p "$(dirname "$REPORT_FILE")"
  cat > "$REPORT_FILE" <<EOF
# A7 Soak Test Final Report

Date: $(date -Iseconds)

## Result
- Status: $status
- Ticket: $TICKET_ID

## Runtime Snapshot
- PID: $pid
- Uptime seconds: $elapsed
- Current cycle: $cycle
- Queue status: $queue_status
- Waiting ticket: ${waiting_ticket:--}
- Errors in last 500 log lines: $errors

## Files
- State: $STATE_FILE
- Log: $LOG_FILE

## Acceptance Check
- Duration >= ${MIN_SECONDS}s: $([[ "$elapsed" -ge "$MIN_SECONDS" ]] && echo yes || echo no)
- Error count == 0: $([[ "$errors" -eq 0 ]] && echo yes || echo no)
- Queue not blocked: $([[ "$queue_status" != "waiting_input" ]] && echo yes || echo no)
EOF
}

cd "$PROJECT"

initial_pid="$(find_pid)"
if [[ -z "$initial_pid" ]]; then
  echo "koru-soak-monitor: no matching soak process (pattern: $PROCESS_PATTERN)" >&2
  exit 3
fi

while true; do
  pid="$(find_pid)"
  if [[ -z "$pid" ]]; then
    write_report "failed:no-process" "-" "0" "$(state_field cycle)" "$(state_field queue_status)" "$(state_field waiting_ticket)" "$(error_count)"
    exit 1
  fi

  elapsed="$(pid_elapsed "$pid")"
  cycle="$(state_field cycle)"
  queue_status="$(state_field queue_status)"
  waiting_ticket="$(state_field waiting_ticket)"
  errors="$(error_count)"

  if [[ "$elapsed" -ge "$MIN_SECONDS" ]]; then
    if [[ "$errors" -eq 0 && "$queue_status" != "waiting_input" ]]; then
      write_report "passed" "$pid" "$elapsed" "$cycle" "$queue_status" "$waiting_ticket" "$errors"
      if command -v planfile >/dev/null 2>&1; then
        planfile ticket update "$TICKET_ID" --status done >/dev/null 2>&1 || true
      fi
      exit 0
    fi
    write_report "failed:health-check" "$pid" "$elapsed" "$cycle" "$queue_status" "$waiting_ticket" "$errors"
    exit 2
  fi

  sleep "$POLL_SECONDS"
done