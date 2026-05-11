#!/usr/bin/env bash
# scripts/koru-autoloop-reset-diag-markers.sh — clear [AUTO-DIAG] dedup markers
# and optionally close the matching open planfile tickets.
#
# Companion to scripts/koru-autoloop.sh: when the autoloop creates a diagnostic
# ticket it drops a marker file under $MARKER_DIR (default
# .planfile/.koru/autoloop-diag/<check>.failed) so subsequent cycles do not
# duplicate the ticket. Use this script after a human (or the autoloop itself)
# has closed the ticket and you want the autoloop to be allowed to recreate it
# on the next failure.
#
# Env vars:
#   MARKER_DIR=.planfile/.koru/autoloop-diag
#   CHECK=all                       (all | regix | wup | redup | testql | redsl | sumr)
#   CLOSE_TICKETS=false             (true => also close open [AUTO-DIAG] tickets)
#   CLOSE_STATUS=done               (done|canceled|blocked|review|open|in_progress)
#   KORU_PLANFILE_CMD=planfile      (or 'python3 -m planfile.cli')
#   KORU_PYTHONPATH=                (prepended to PYTHONPATH)

set -euo pipefail

MARKER_DIR="${MARKER_DIR:-.planfile/.koru/autoloop-diag}"
CHECK="${CHECK:-all}"
CLOSE_TICKETS="${CLOSE_TICKETS:-false}"
CLOSE_STATUS="${CLOSE_STATUS:-done}"
KORU_PLANFILE_CMD="${KORU_PLANFILE_CMD:-planfile}"
export KORU_PLANFILE_CMD
if [ -n "${KORU_PYTHONPATH:-}" ]; then
  export PYTHONPATH="${KORU_PYTHONPATH}:${PYTHONPATH:-}"
fi

read -ra PLANFILE_INVOKE <<< "$KORU_PLANFILE_CMD"

is_true() {
  case "${1,,}" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

check_lc="${CHECK,,}"
close_status_raw="$CLOSE_STATUS"
close_status_lc="${close_status_raw,,}"
case "$close_status_lc" in
  cancelled) close_status_lc="canceled" ;;
  done|canceled|blocked|review|open|in_progress) ;;
  *)
    echo "! unsupported CLOSE_STATUS=${close_status_raw} (valid: done|canceled|blocked|review|open|in_progress), using 'done'" >&2
    close_status_lc="done"
    ;;
esac

# ---- 1. remove marker files ------------------------------------------------
if [ ! -d "$MARKER_DIR" ]; then
  echo "koru-autoloop-reset-diag-markers: no marker dir $MARKER_DIR, nothing to clear"
else
  if [ "$check_lc" = "all" ]; then
    echo "+ rm -f $MARKER_DIR/*.failed"
    rm -f "$MARKER_DIR"/*.failed 2>/dev/null || true
  else
    echo "+ rm -f $MARKER_DIR/${check_lc}.failed"
    rm -f "$MARKER_DIR/${check_lc}.failed" 2>/dev/null || true
  fi
  remaining=$(find "$MARKER_DIR" -maxdepth 1 -name '*.failed' 2>/dev/null | wc -l | tr -d ' ')
  echo "koru-autoloop-reset-diag-markers: markers remaining=${remaining}"
fi

# ---- 2. optionally close matching open tickets -----------------------------
if ! is_true "$CLOSE_TICKETS"; then
  exit 0
fi

filter_py="$(dirname "$0")/_koru_autodiag_filter_tickets.py"
if [ ! -f "$filter_py" ]; then
  echo "! helper missing: $filter_py" >&2
  exit 1
fi

echo "+ closing open [AUTO-DIAG] tickets (check=${check_lc}, status=${close_status_lc})"
if ! ids=$("${PLANFILE_INVOKE[@]}" ticket list --status open --format json 2>/dev/null \
  | python3 "$filter_py" --check "$check_lc"); then
  echo "! failed to list planfile tickets" >&2
  exit 1
fi

if [ -z "$ids" ]; then
  echo "- no open [AUTO-DIAG] tickets found"
  exit 0
fi

printf '%s\n' "$ids" | while IFS= read -r tid; do
  [ -z "$tid" ] && continue
  echo "+ planfile ticket update $tid --status ${close_status_lc}"
  "${PLANFILE_INVOKE[@]}" ticket update "$tid" --status "${close_status_lc}" >/dev/null \
    || echo "! failed to close $tid" >&2
done
