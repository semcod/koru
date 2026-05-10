#!/usr/bin/env bash
# End-to-end smoke test for koru queue runner.
#
# Verifies the full lifecycle:
#   planfile ticket next --format json
#   → koru dispatches by executor.kind
#   → planfile ticket claim/start/complete (or input for human)
#
# Requirements:
#   - planfile >= 0.1.87 (with TicketExecutor/TicketExecution schema and
#     ticket next/claim/start/complete/fail/input commands)
#   - koru installed or PYTHONPATH=src/
#
# Usage:
#   bash tests/e2e/smoke.sh
#   PLANFILE_BIN=/path/to/planfile bash tests/e2e/smoke.sh

set -euo pipefail

KORU_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLANFILE_BIN="${PLANFILE_BIN:-planfile}"
DEMO_DIR="${DEMO_DIR:-/tmp/koru-e2e-smoke-$$}"
ACTOR="${ACTOR:-koru-e2e}"

cleanup() { rm -rf "$DEMO_DIR"; }
trap cleanup EXIT

echo "==> Setting up demo project at $DEMO_DIR"
mkdir -p "$DEMO_DIR/.planfile/sprints"
cd "$DEMO_DIR"
git init -q

cat > .planfile/config.yaml <<'EOF'
project: koru-e2e-smoke
prefix: SMOKE
next_id: 3
EOF

cat > .planfile/sprints/current.yaml <<'EOF'
sprint:
  id: sprint-001
  name: Smoke test sprint
  status: active
  tickets:
    SMOKE-001:
      id: SMOKE-001
      name: Shell ticket — echo OK
      status: open
      priority: high
      sprint: current
      labels: [koru-task, smoke]
      executor:
        kind: shell
        mode: automatic
        handler: "echo SMOKE_PASS"
      execution:
        queue: default
        state: ready
        attempt: 0
        max_attempts: 1
    SMOKE-002:
      id: SMOKE-002
      name: Human ticket — secret value
      status: open
      priority: normal
      sprint: current
      labels: [koru-task, smoke]
      blocked_by: [SMOKE-001]
      executor:
        kind: human
        mode: interactive
        handler: password
      execution:
        queue: default
        state: pending
      inputs:
        prompt: "Provide test API key"
        env_keys: [TEST_API_KEY]
EOF

echo "==> 1. Verify planfile reads tickets"
"$PLANFILE_BIN" ticket list >/dev/null

echo "==> 2. planfile ticket next returns SMOKE-001"
NEXT_ID=$("$PLANFILE_BIN" ticket next --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
[ "$NEXT_ID" = "SMOKE-001" ] || { echo "FAIL: expected SMOKE-001, got $NEXT_ID"; exit 1; }

echo "==> 3. koru --queue --dry-run previews shell command"
DRY_OUT=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --dry-run 2>&1)
echo "$DRY_OUT" | grep -q "status=dry_run" || { echo "FAIL dry-run: $DRY_OUT"; exit 1; }
echo "$DRY_OUT" | grep -q "ticket=SMOKE-001" || { echo "FAIL dry-run ticket: $DRY_OUT"; exit 1; }

echo "==> 4. koru --queue executes SMOKE-001"
RUN_OUT=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --actor "$ACTOR" 2>&1)
echo "$RUN_OUT" | grep -q "status=completed" || { echo "FAIL run: $RUN_OUT"; exit 1; }

echo "==> 5. SMOKE-001 is now done with assigned_to=$ACTOR"
STATUS=$("$PLANFILE_BIN" ticket show SMOKE-001 --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["status"])')
[ "$STATUS" = "done" ] || { echo "FAIL: SMOKE-001 status=$STATUS, expected done"; exit 1; }

ASSIGNEE=$("$PLANFILE_BIN" ticket show SMOKE-001 --format json | python3 -c 'import json,sys;t=json.load(sys.stdin);print((t.get("execution") or {}).get("assigned_to") or "")')
[ "$ASSIGNEE" = "$ACTOR" ] || { echo "FAIL: assigned_to=$ASSIGNEE, expected $ACTOR"; exit 1; }

echo "==> 6. Next run picks SMOKE-002 (human → waiting_input)"
NEXT2_OUT=$(PYTHONPATH="$KORU_REPO/src" python3 -m koru.cli --queue --project "$DEMO_DIR" --actor "$ACTOR" 2>&1)
echo "$NEXT2_OUT" | grep -q "status=waiting_input" || { echo "FAIL next2: $NEXT2_OUT"; exit 1; }
echo "$NEXT2_OUT" | grep -q "ticket=SMOKE-002" || { echo "FAIL next2 ticket: $NEXT2_OUT"; exit 1; }
echo "$NEXT2_OUT" | grep -q "Provide test API key" || { echo "FAIL next2 prompt: $NEXT2_OUT"; exit 1; }

echo ""
echo "==> ✅ All 6 e2e steps passed"
