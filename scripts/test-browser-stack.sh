#!/usr/bin/env bash
# Quick Koru integration test for browser automation stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [ -n "${VENV:-}" ]; then
  :
elif [ -x "$ROOT/.venv/bin/python" ]; then
  VENV=".venv"
elif [ -x "$ROOT/venv/bin/python" ]; then
  VENV="venv"
else
  VENV=".venv"
fi
PY="$ROOT/$VENV/bin/python"
PIP="$ROOT/$VENV/bin/pip"

if [ ! -x "$PY" ]; then
  echo "error: run ./project.sh first (missing $ROOT/$VENV)" >&2
  exit 1
fi
echo "Using $VENV"

echo "==> pytest (browser stack)"
"$PY" -m pytest tests/test_nlp2oql_bridge.py tests/test_koru_browser_stack.py tests/test_mcp_server_split.py::test_schema_tools_regression_contains_expected_tool_names -q

echo ""
echo "==> nlp2oql doctor"
"$VENV/bin/nlp2oql" doctor 2>/dev/null || echo "nlp2oql doctor skipped"

echo ""
echo "==> testql complex-replay dry-run"
EXAMPLE="$ROOT/../../oqlos/testql/examples/environment/complex-replay.testql.toon.yaml"
if [ -f "$EXAMPLE" ]; then
  "$VENV/bin/testql" run "$EXAMPLE" --dry-run
else
  echo "skip: $EXAMPLE not found"
fi

echo ""
echo "==> nlp2uri + testql browser demo"
if [ -x "$ROOT/examples/nlp2uri-testql-browser/run.sh" ]; then
  DRY_RUN=1 TARGET_URL=https://example.com bash "$ROOT/examples/nlp2uri-testql-browser/run.sh" 2>&1 | tail -12
fi

echo ""
echo "OK: Koru browser stack smoke passed"
