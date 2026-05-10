#!/usr/bin/env bash
set -euo pipefail
DEMO="/tmp/koru-e2e-init-$$"
trap 'rm -rf "$DEMO"' EXIT
mkdir -p "$DEMO" && cd "$DEMO" && git init -q

step() { echo "==> $1"; }

step "1. bare koru shows setup-required"
OUTPUT=$(koru --project "$DEMO" 2>&1)
echo "$OUTPUT" | grep -q "Setup required"

step "2. koru --init succeeds"
koru --init --project "$DEMO"

step "3. koru --doctor passes"
koru --doctor --project "$DEMO"
[ $? -eq 0 ]

step "4. bare koru shows STARTER-001"
OUTPUT=$(koru --project "$DEMO" 2>&1)
echo "$OUTPUT" | grep -q "STARTER-001"

step "5. koru --queue drains STARTER-001"
koru --queue --project "$DEMO" | grep -q "completed"

echo ""
echo "==> ✅ All 5 init e2e steps passed"
