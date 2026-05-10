#!/usr/bin/env bash
# End-to-end smoke test for the koru bootstrap workflow.
#
# Verifies the hybrid flat→nested format bridge:
#   1. koru --bootstrap --from <flat.yaml> writes .planfile/ structure
#   2. planfile reads the resulting tickets
#   3. koru --queue executes the first runnable task (DAG-aware ordering)
#   4. Subsequent ticket becomes runnable after dependencies clear
#
# Requirements: planfile >= 0.1.87 with TicketExecutor/TicketExecution.

set -euo pipefail

KORU_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLANFILE_BIN="${PLANFILE_BIN:-planfile}"
DEMO_DIR="${DEMO_DIR:-/tmp/koru-bootstrap-smoke-$$}"
ACTOR="${ACTOR:-koru-bs}"

cleanup() { rm -rf "$DEMO_DIR"; }
trap cleanup EXIT

# Avoid Rich line-wrapping in planfile JSON output (matches koru's subprocess env).
export COLUMNS=10000
export TERM=dumb

echo "==> Setting up demo project at $DEMO_DIR"
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"
git init -q

echo "==> 1. koru --bootstrap imports flat pipeline into .planfile/"
PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli \
  --bootstrap \
  --from "$KORU_REPO/examples/bootstrap.planfile.yaml" \
  --project "$DEMO_DIR" \
  --sprint current >/tmp/koru-bs-out.txt 2>&1
grep -q "✓ imported" /tmp/koru-bs-out.txt || { cat /tmp/koru-bs-out.txt; echo "FAIL: bootstrap did not report success"; exit 1; }
grep -q "tickets: 15 imported" /tmp/koru-bs-out.txt || { cat /tmp/koru-bs-out.txt; echo "FAIL: expected 15 tickets"; exit 1; }

echo "==> 2. .planfile/ structure created"
[ -f "$DEMO_DIR/.planfile/config.yaml" ] || { echo "FAIL: config.yaml missing"; exit 1; }
[ -f "$DEMO_DIR/.planfile/sprints/current.yaml" ] || { echo "FAIL: current.yaml missing"; exit 1; }

echo "==> 3. planfile sees all 15 tickets"
TICKET_COUNT=$("$PLANFILE_BIN" ticket list --status all --format json | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')
[ "$TICKET_COUNT" = "15" ] || { echo "FAIL: planfile sees $TICKET_COUNT tickets, expected 15"; exit 1; }

echo "==> 4. planfile ticket next picks KORU-B-001 (highest priority, ready)"
NEXT_ID=$("$PLANFILE_BIN" ticket next --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
[ "$NEXT_ID" = "KORU-B-001" ] || { echo "FAIL: next=$NEXT_ID, expected KORU-B-001"; exit 1; }

echo "==> 5. koru --queue executes KORU-B-001 (git rev-parse)"
RUN1=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --actor "$ACTOR" 2>&1)
echo "$RUN1" | grep -q "status=completed" || { echo "FAIL run1: $RUN1"; exit 1; }
echo "$RUN1" | grep -q "ticket=KORU-B-001" || { echo "FAIL run1 ticket: $RUN1"; exit 1; }

echo "==> 6. koru --queue executes KORU-B-002 (python version, also ready)"
RUN2=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --actor "$ACTOR" 2>&1)
echo "$RUN2" | grep -q "status=completed" || { echo "FAIL run2: $RUN2"; exit 1; }
echo "$RUN2" | grep -q "ticket=KORU-B-002" || { echo "FAIL run2 ticket: $RUN2"; exit 1; }

echo "==> 7. KORU-B-010 (depends on B-001+B-002) is now next, in dry-run"
RUN3=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --actor "$ACTOR" --dry-run 2>&1)
echo "$RUN3" | grep -q "status=dry_run" || { echo "FAIL run3: $RUN3"; exit 1; }
echo "$RUN3" | grep -q "ticket=KORU-B-010" || { echo "FAIL run3 ticket: $RUN3"; exit 1; }

echo "==> 8. Re-bootstrap without --force is rejected"
if PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli \
    --bootstrap \
    --from "$KORU_REPO/examples/bootstrap.planfile.yaml" \
    --project "$DEMO_DIR" \
    --sprint current >/tmp/koru-bs-err.txt 2>&1
then
    cat /tmp/koru-bs-err.txt
    echo "FAIL: re-bootstrap should have errored"
    exit 1
fi
grep -q "already exists" /tmp/koru-bs-err.txt || { cat /tmp/koru-bs-err.txt; echo "FAIL: missing 'already exists' message"; exit 1; }

echo "==> 9. Re-bootstrap with --force succeeds"
PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli \
    --bootstrap \
    --from "$KORU_REPO/examples/bootstrap.planfile.yaml" \
    --project "$DEMO_DIR" \
    --sprint current \
    --force >/tmp/koru-bs-force.txt 2>&1
grep -q "imported" /tmp/koru-bs-force.txt || { cat /tmp/koru-bs-force.txt; echo "FAIL force"; exit 1; }

echo ""
echo "==> ✅ All 9 bootstrap e2e steps passed"
