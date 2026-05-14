#!/usr/bin/env bash
# scripts/koru-queue-diagnose.sh — run a single queue pass and report
# how many tickets matching the given filter were processed, are still open,
# or are stuck in waiting_input.
#
# Usage:
#   ./scripts/koru-queue-diagnose.sh [--label LABEL] [--max-iterations N]
#
# Env:
#   PROJECT      project root (default: cwd)
#   LABEL        ticket label filter (e.g. "must-run") - optional
#   QUEUE_NAME   queue name (default: all queues)
#   MAX_ITERATIONS  max --loop iterations (default: 50)
#
# Exit codes:
#   0  all tickets matching filter are done
#   1  some tickets remain open / waiting_input
#   2  CLI/tooling error

set -euo pipefail

PROJECT="${PROJECT:-$(pwd)}"
LABEL="${LABEL:-}"
QUEUE_NAME="${QUEUE_NAME:-}"
MAX_ITERATIONS="${MAX_ITERATIONS:-50}"

KORU_CMD="${KORU_CMD:-koru}"
PLANFILE_CMD="${PLANFILE_CMD:-planfile}"

# --------------------------------------------------------------------- args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --label) LABEL="$2"; shift 2 ;;
        --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
        --queue-name) QUEUE_NAME="$2"; shift 2 ;;
        --project) PROJECT="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,18p' "$0"; exit 0 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

cd "$PROJECT"

echo "=== koru-queue-diagnose ==="
echo "  project:        $PROJECT"
echo "  label filter:   ${LABEL:-<none>}"
echo "  queue:          ${QUEUE_NAME:-<all>}"
echo "  max iterations: $MAX_ITERATIONS"
echo

# ----------------------------------------------------------- snapshot before
echo "--- BEFORE: open tickets ---"
BEFORE_OPEN=$($PLANFILE_CMD ticket list --status open --format json 2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
items = data.get('items', data) if isinstance(data, dict) else data
label = '${LABEL}'
if label:
    items = [t for t in items if label in (t.get('labels') or [])]
print(json.dumps([t.get('id') for t in items]))
" || echo "[]")
BEFORE_COUNT=$(echo "$BEFORE_OPEN" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
echo "  open matching: $BEFORE_COUNT"
echo "  ids: $BEFORE_OPEN"
echo

# ----------------------------------------------------------- queue pass
echo "--- RUNNING queue pass (--max-iterations $MAX_ITERATIONS, --no-autopilot) ---"
QUEUE_ARGS=("--queue" "--loop" "--max-iterations" "$MAX_ITERATIONS")
if [[ -n "$QUEUE_NAME" ]]; then
    QUEUE_ARGS+=("--queue-name" "$QUEUE_NAME")
else
    QUEUE_ARGS+=("--all-queues")
fi

QUEUE_OUTPUT=$($KORU_CMD "${QUEUE_ARGS[@]}" 2>&1 || true)
echo "$QUEUE_OUTPUT" | tail -20
echo

# Parse summary line: "queue: iterations=N completed=N failed=N waiting=N last_status=..."
LAST_STATUS=$(echo "$QUEUE_OUTPUT" | grep -oE 'last_status=[a-z_]+' | tail -1 | cut -d= -f2 || echo "unknown")
COMPLETED=$(echo "$QUEUE_OUTPUT" | grep -oE 'completed=[0-9]+' | tail -1 | cut -d= -f2 || echo "0")
WAITING=$(echo "$QUEUE_OUTPUT" | grep -oE 'waiting=[0-9]+' | tail -1 | cut -d= -f2 || echo "0")
FAILED=$(echo "$QUEUE_OUTPUT" | grep -oE 'failed=[0-9]+' | tail -1 | cut -d= -f2 || echo "0")

echo "--- AFTER: open tickets ---"
AFTER_OPEN=$($PLANFILE_CMD ticket list --status open --format json 2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
items = data.get('items', data) if isinstance(data, dict) else data
label = '${LABEL}'
if label:
    items = [t for t in items if label in (t.get('labels') or [])]
print(json.dumps([t.get('id') for t in items]))
" || echo "[]")
AFTER_COUNT=$(echo "$AFTER_OPEN" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")

echo "  open matching: $AFTER_COUNT"
echo "  ids: $AFTER_OPEN"
echo

PROCESSED=$((BEFORE_COUNT - AFTER_COUNT))

# ----------------------------------------------------------- report
echo "=== SUMMARY ==="
echo "  before:    $BEFORE_COUNT open ticket(s)"
echo "  processed: $PROCESSED ticket(s) (no longer open)"
echo "  remaining: $AFTER_COUNT ticket(s)"
echo "  queue:     completed=$COMPLETED failed=$FAILED waiting=$WAITING last_status=$LAST_STATUS"
echo

if [[ "$AFTER_COUNT" -eq 0 ]]; then
    echo "OK: all tickets matching filter are done"
    exit 0
elif [[ "$LAST_STATUS" == "waiting_input" ]]; then
    echo "WARN: $AFTER_COUNT ticket(s) blocked on waiting_input - need IDE/autopilot"
    exit 1
else
    echo "WARN: $AFTER_COUNT ticket(s) still open after queue pass"
    exit 1
fi
