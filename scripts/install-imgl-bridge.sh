#!/usr/bin/env bash
# Install imgl ↔ koru bridge into koru's project venv.
# Run from koru repo root. Uses .venv if present, else current python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMGL_ROOT="${IMGL_ROOT:-$HOME/github/semcod/imgl}"
IMG2NL_ROOT="${IMG2NL_ROOT:-$HOME/github/wronai/img2nl}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
  PIP="$ROOT/.venv/bin/pip"
  echo "Using koru venv: $ROOT/.venv"
else
  PY="$(command -v python3)"
  PIP="$(command -v pip)"
  echo "Using system/current python: $PY"
fi

if [[ ! -d "$IMGL_ROOT" ]]; then
  echo "imgl repo not found at $IMGL_ROOT — set IMGL_ROOT=/path/to/imgl" >&2
  exit 1
fi

"$PIP" install -e "$ROOT"
"$PIP" install -e "$ROOT/packages/koruenv" -e "$ROOT/packages/coru"
"$PIP" install -e "$ROOT/packages/dsl2koru" -e "$ROOT/packages/uri2koru" -e "$ROOT/packages/dsl2coru"
"$PIP" install -e "$IMGL_ROOT"
"$PIP" install "jsonschema>=4.0" "protobuf>=5.0"
"$PIP" install -e "$IMGL_ROOT/packages/dsl2imgl"
"$PIP" install -e "$IMGL_ROOT/packages/nlp2imgl"

if [[ -d "$IMG2NL_ROOT" ]]; then
  "$PIP" install -e "$IMG2NL_ROOT[analyze]" || "$PIP" install -e "$IMG2NL_ROOT"
  echo "img2nl: $IMG2NL_ROOT"
else
  echo "WARN: img2nl not found at $IMG2NL_ROOT — set IMG2NL_ROOT for capture autodiagnostics" >&2
fi

echo ""
echo "OK. Test:"
echo "  $ROOT/.venv/bin/dsl2imgl exec 'KEY ctrl+Return EXECUTE 0'"
echo "  $ROOT/.venv/bin/dsl2coru exec 'UI_KEY ctrl+Return'"
echo "  $ROOT/.venv/bin/koru imgl doctor --format yaml"
echo "  $ROOT/.venv/bin/koru imgl execute 'wpisz test w Chat input' --window region-bottom --dry-run"
