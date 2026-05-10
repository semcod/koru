#!/usr/bin/env bash
# scripts/redup-check.sh
#
# Real duplicate-budget gate for c2004. reDUP's built-in `check` command is
# currently summary-oriented, so this wrapper generates a JSON report and
# enforces the thresholds itself.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

SCAN_PATH="${1:-.}"
EXTENSIONS="${REDUP_EXTENSIONS:-.py,.js,.ts,.tsx,.jsx}"
MIN_LINES="${REDUP_MIN_LINES:-8}"
MIN_SIMILARITY="${REDUP_MIN_SIMILARITY:-0.92}"
MAX_GROUPS="${REDUP_MAX_GROUPS:-400}"
MAX_LINES="${REDUP_MAX_LINES:-6000}"
INCLUDE_TESTS="${REDUP_INCLUDE_TESTS:-false}"
REPORT_PATH="${REDUP_REPORT_PATH:-.redup/check.json}"

mkdir -p "$(dirname "$REPORT_PATH")"

SCAN_ARGS=(
  scan "$SCAN_PATH"
  --format json
  --output "$REPORT_PATH"
  --ext "$EXTENSIONS"
  --min-lines "$MIN_LINES"
  --min-sim "$MIN_SIMILARITY"
)

if [ "$INCLUDE_TESTS" = "true" ]; then
  SCAN_ARGS+=(--include-tests)
fi

scripts/redup-run.sh "${SCAN_ARGS[@]}"

python3 - "$REPORT_PATH" "$MAX_GROUPS" "$MAX_LINES" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
max_groups = int(sys.argv[2])
max_lines = int(sys.argv[3])

# Post-scan filter: redup nie obsługuje exclude_patterns w current TOML schema,
# więc filtrujemy tu. Synchronized with redup.toml [exclude] section docs.
EXCLUDE_PATTERNS = [
    ".swop/",                # generated swop services (gitignored)
    "archive/",
    "_archive/",
    "/_pb2",                 # generated protobuf
    "/__generated__/",
    "venv/",
    ".venv/",
    "node_modules/",
    "/alembic/",             # alembic migrations are intentional copies
]

# c2004-specific architecture: `shared/` is a compatibility shim layer that
# re-exports from `packages/backend-shared-py/src/shared/`. Its files are
# either ~200B stubs OR bootloader-style wrappers that runtime-import from
# canonical `packages/`. Both contain symbols matching canonical → redup
# flags them. We detect such files by docstring marker.
SHIM_DOCSTRING_MARKERS = (
    "Compatibility wrapper for",
    "Compatibility shim for",
    "Canonical implementation lives in",
)


def is_compat_shim(file_path: str) -> bool:
    """True if file declares itself as a compat shim in c2004 (NOT a duplicate)."""
    if not file_path.startswith("shared/"):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            head = fh.read(800)  # docstring is always at top
    except OSError:
        return False
    return any(marker in head for marker in SHIM_DOCSTRING_MARKERS)


def is_excluded(file_path: str) -> bool:
    return any(p in file_path for p in EXCLUDE_PATTERNS) or is_compat_shim(file_path)


with report_path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

raw_groups = payload.get("groups", []) or []
filtered_groups = []
for g in raw_groups:
    fragments = g.get("fragments", []) or []
    keep = [f for f in fragments if not is_excluded(f.get("file", ""))]
    if len(keep) >= 2:  # group needs ≥2 fragments to be a duplicate
        g_copy = dict(g)
        g_copy["fragments"] = keep
        filtered_groups.append(g_copy)

groups = len(filtered_groups)
saved_lines = sum(int(g.get("saved_lines", 0)) for g in filtered_groups)

# Persist filtered report for downstream consumers (CI logs, healing-webhook)
filtered_path = report_path.with_suffix(".filtered.json")
with filtered_path.open("w", encoding="utf-8") as handle:
    json.dump(
        {
            "summary": {
                "total_groups": groups,
                "total_saved_lines": saved_lines,
                "total_fragments": sum(len(g.get("fragments", [])) for g in filtered_groups),
                "raw_total_groups": len(raw_groups),
                "filtered_out": len(raw_groups) - groups,
            },
            "groups": filtered_groups,
        },
        handle,
        indent=2,
    )

print(f"[redup] raw_groups={len(raw_groups)} filtered_groups={groups} "
      f"(excluded {len(raw_groups) - groups} via {len(EXCLUDE_PATTERNS)} patterns)")
print(f"[redup] total_groups={groups} total_saved_lines={saved_lines} "
      f"(budget: groups<={max_groups}, lines<={max_lines})")
print(f"[redup] filtered report → {filtered_path}")

violations = []
if groups > max_groups:
    violations.append(f"groups {groups} > {max_groups}")
if saved_lines > max_lines:
    violations.append(f"saved_lines {saved_lines} > {max_lines}")

if violations:
    print(f"[redup] budget exceeded: {', '.join(violations)}", file=sys.stderr)
    raise SystemExit(1)

print("[redup] budget OK")
PY
