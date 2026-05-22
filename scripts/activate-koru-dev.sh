#!/usr/bin/env bash
# Activate semcod/koru .venv and put its bin/ first on PATH (fixes pyenv/global shadowing).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "${ROOT}/.venv/bin/activate" ]]; then
  echo "activate-koru-dev: run first: cd ${ROOT} && python -m venv .venv && pip install -e '.[dev]'" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "${ROOT}/.venv/bin/activate"
export PATH="${ROOT}/.venv/bin:${PATH}"
hash -r 2>/dev/null || true
if command -v koru >/dev/null 2>&1; then
  echo "koru: $(command -v koru) ($(koru --version 2>/dev/null | head -1 || echo '?'))"
else
  echo "koru: not found on PATH after activate" >&2
  exit 1
fi
