#!/usr/bin/env bash
# nlp2uri (native browser URI) + TestQL (Playwright DOM) — combined demo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KORU_ROOT="$(cd "$ROOT/../.." && pwd)"
TESTQL_ROOT="${TESTQL_ROOT:-$KORU_ROOT/../../oqlos/testql}"

TARGET_URL="${TARGET_URL:-https://example.com}"
DRY_RUN="${DRY_RUN:-1}"
EXECUTE_NATIVE="${EXECUTE_NATIVE:-0}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  Phase 1 — nlp2uri: NL → URI → OS action (xdg-open / open)
  Phase 2 — testql:  Playwright DOM (click, assert, keyboard input)

Options (env):
  TARGET_URL=https://example.com   Page under test
  DRY_RUN=1                        testql --dry-run (default)
  EXECUTE_NATIVE=1                 run nlp2uri execute (not dry-run)
  NLP2URI=/path/to/nlp2uri         Override binary
  TESTQL=/path/to/testql           Override binary

Examples:
  ./run.sh
  TARGET_URL=https://tom.sapletta.com/ DRY_RUN=0 ./run.sh
  EXECUTE_NATIVE=1 DRY_RUN=0 ./run.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

resolve_bin() {
  local name="$1"
  local koru_venv="$KORU_ROOT/venv/bin/$name"
  local testql_venv="$TESTQL_ROOT/venv/bin/$name"
  if [[ -n "${!2:-}" ]]; then
    echo "${!2}"
  elif [[ -x "$koru_venv" ]]; then
    echo "$koru_venv"
  elif [[ -x "$testql_venv" ]]; then
    echo "$testql_venv"
  elif command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
  else
    echo ""
  fi
}

NLP2URI="$(resolve_bin nlp2uri NLP2URI)"
TESTQL="$(resolve_bin testql TESTQL)"

if [[ -z "$NLP2URI" ]]; then
  echo "error: nlp2uri not found. Run: cd $KORU_ROOT && ./project.sh" >&2
  exit 1
fi
if [[ -z "$TESTQL" ]]; then
  echo "error: testql not found. Install: cd $TESTQL_ROOT && pip install -e ." >&2
  exit 1
fi

render_scenario() {
  local src="$1"
  local dst="$2"
  sed "s|https://example.com|${TARGET_URL}|g" "$src" >"$dst"
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

OQL="$WORKDIR/browser-dom.oql"
TOON="$WORKDIR/browser-dom.testql.toon.yaml"
render_scenario "$ROOT/browser-dom.oql" "$OQL"
render_scenario "$ROOT/browser-dom.testql.toon.yaml" "$TOON"

TESTQL_ARGS=()
if [[ "$DRY_RUN" == "1" ]]; then
  TESTQL_ARGS+=(--dry-run)
fi

NLP2URI_EXEC_ARGS=(execute "${TARGET_URL}" --platform linux)
if [[ "$EXECUTE_NATIVE" != "1" ]]; then
  NLP2URI_EXEC_ARGS+=(--dry-run)
fi

echo "==> Target URL: $TARGET_URL"
echo "==> nlp2uri:    $NLP2URI"
echo "==> testql:     $TESTQL"
echo ""

echo "=== Phase 1a: nlp2uri plan (NL → URI + OSAction) ==="
"$NLP2URI" plan "open ${TARGET_URL}" --json | head -c 2000
echo ""
echo ""

echo "=== Phase 1b: nlp2uri execute (native browser — optional) ==="
"$NLP2URI" "${NLP2URI_EXEC_ARGS[@]}"
echo ""

echo "=== Phase 2a: testql OQL (GUI_START → ASSERT → CLICK) ==="
"$TESTQL" run "$OQL" --url "$TARGET_URL" "${TESTQL_ARGS[@]}"
echo ""

echo "=== Phase 2b: testql TestTOON (SHELL nlp2uri + NAVIGATE + FLOW) ==="
"$TESTQL" run "$TOON" --url "$TARGET_URL" "${TESTQL_ARGS[@]}"
echo ""

echo "=== Done ==="
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Note: testql ran in dry-run mode. Set DRY_RUN=0 and install playwright for live DOM."
  echo "      pip install playwright && playwright install chromium"
fi
if [[ "$EXECUTE_NATIVE" != "1" ]]; then
  echo "Note: nlp2uri execute was dry-run. Set EXECUTE_NATIVE=1 to open the system browser."
fi
