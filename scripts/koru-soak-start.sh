#!/usr/bin/env bash
# Start a long-running ``koru autonomous up --max-cycles 0`` soak in the background.
set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
cd "$PROJECT"
LOG_FILE="${LOG_FILE:-$PROJECT/.planfile/.koru/soak.log}"
PROCESS_PATTERN="${PROCESS_PATTERN:-autonomous up.*--max-cycles 0}"

find_soak_pid() {
  pgrep -fo "$PROCESS_PATTERN" || true
}

if [[ -n "$(find_soak_pid)" ]]; then
  echo "! soak already running (pid=$(find_soak_pid))"
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"

if command -v koru >/dev/null 2>&1; then
  KORU=(koru)
elif [[ -x "$PROJECT/.venv/bin/koru" ]]; then
  KORU=("$PROJECT/.venv/bin/koru")
elif [[ -x "$PROJECT/venv/bin/koru" ]]; then
  KORU=("$PROJECT/venv/bin/koru")
else
  KORU=(python3 -m koru.cli)
fi

nohup "${KORU[@]}" autonomous up --project "$PROJECT" --max-cycles 0 \
  >>"$LOG_FILE" 2>&1 &
soak_pid=$!
disown "$soak_pid" 2>/dev/null || true

echo "soak_pid=$soak_pid"
echo "log_file=$LOG_FILE"
echo "koru_cmd=${KORU[*]} autonomous up --project $PROJECT --max-cycles 0"
echo "next: task scripts:soak:monitor"
