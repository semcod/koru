#!/usr/bin/env bash
# Run the koru CLI from this repository's .venv (avoids pyenv/global stale builds).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KORU_BIN="${ROOT}/.venv/bin/koru"
if [[ ! -x "${KORU_BIN}" ]]; then
  echo "koru-from-repo: missing ${KORU_BIN} — run: cd ${ROOT} && python -m venv .venv && pip install -e '.[dev]'" >&2
  exit 1
fi
exec "${KORU_BIN}" "$@"
