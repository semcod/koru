#!/usr/bin/env bash
# scripts/regix-precommit.sh
#
# Pre-commit hook driver — runs `regix compare HEAD --local --errors-only`
# to detect code quality regressions in the working tree (uncommitted
# changes) before they land in the repo.
#
# Behaviour:
#   • If `regix` is on PATH → run the comparison; commit fails on any
#     `error` regression (delta ≥ delta_error in regix.yaml).
#   • Otherwise → print a friendly hint and exit 0 so fresh clones aren't
#     blocked. Install with: pip install --user "regix[full]"
#
# Configuration: regix.yaml at repo root.
# CI parity: GitHub Actions runs the same comparison on PRs.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

if ! command -v regix >/dev/null 2>&1; then
  cat <<'EOF'
[regix] not installed — skipping regression check.
        Install with:  pip install --user "regix[full]"
        Or run via:    task quality:regix
EOF
  exit 0
fi

# Skip when there's nothing to compare against (initial commit, shallow clone)
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "[regix] no HEAD ref — skipping (initial commit?)."
  exit 0
fi

# Compare working tree against HEAD; only fail on errors (delta ≥ delta_error)
# Suppress warnings to avoid noise on every commit.
echo "[regix] comparing working tree against HEAD…"
if ! regix compare HEAD --local --errors-only --fail-on error 2>&1; then
  cat <<'EOF'

[regix] ❌ regression detected — commit blocked.
        Run `task quality:regix:report` for the full diff.
        Override with:  git commit --no-verify   (NOT recommended)
EOF
  exit 1
fi

echo "[regix] ✓ no regressions"
exit 0
