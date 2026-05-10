#!/usr/bin/env bash
# scripts/redup-precommit.sh
#
# Advisory duplicate scan for pre-commit. By default it warns but does not
# block commits because c2004 still has historical duplication across modules.
# Set REDUP_STRICT=true to make it a blocking gate.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

echo "[redup] scanning for high-similarity duplicates…"
if REDUP_EXTENSIONS="${REDUP_PRECOMMIT_EXT:-.py,.js,.ts,.tsx,.jsx}" \
  REDUP_MIN_LINES="${REDUP_PRECOMMIT_MIN_LINES:-8}" \
  REDUP_MIN_SIMILARITY="${REDUP_PRECOMMIT_MIN_SIM:-0.92}" \
  REDUP_MAX_GROUPS="${REDUP_PRECOMMIT_MAX_GROUPS:-400}" \
  REDUP_MAX_LINES="${REDUP_PRECOMMIT_MAX_LINES:-6000}" \
  REDUP_REPORT_PATH="${REDUP_PRECOMMIT_REPORT_PATH:-.redup/precommit-check.json}" \
  scripts/redup-check.sh .; then
  echo "[redup] ✓ duplicate budget respected"
  exit 0
fi

if [ "${REDUP_STRICT:-false}" = "true" ]; then
  cat <<'EOF'

[redup] ❌ duplicate budget exceeded — commit blocked.
        Run `task quality:redup:report` for a machine-readable report.
        Override with:  git commit --no-verify   (NOT recommended)
EOF
  exit 1
fi

cat <<'EOF'

[redup] ⚠ duplicate budget exceeded — advisory only.
        Run `task quality:redup:report` to inspect duplicate groups.
        Set REDUP_STRICT=true to make this hook blocking.
EOF
exit 0
