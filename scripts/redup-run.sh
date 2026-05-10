#!/usr/bin/env bash
# scripts/redup-run.sh
#
# Thin wrapper for reDUP. Prefer the installed `redup` CLI when available,
# otherwise fall back to the local semcod checkout so c2004 can use the tool
# without an extra host install step.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

REDUP_SOURCE_DIR="${REDUP_SOURCE_DIR:-/home/tom/github/semcod/redup/src}"

if command -v redup >/dev/null 2>&1; then
  exec redup "$@"
fi

if [ -f "$REDUP_SOURCE_DIR/redup/__init__.py" ]; then
  exec env PYTHONPATH="$REDUP_SOURCE_DIR${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m redup.cli_app.main "$@"
fi

cat <<'EOF' >&2
[redup] CLI not available.
        Install with:  pip install --user "redup[ast,fuzzy]"
        Or provide a local checkout via:  REDUP_SOURCE_DIR=/path/to/redup/src
EOF
exit 127
