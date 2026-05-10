#!/usr/bin/env bash
# install.sh — idempotent installer for c2004 git hooks (sumr-refresh).
#
# Usage:
#   bash scripts/git-hooks/install.sh                # install post-merge (default)
#   bash scripts/git-hooks/install.sh post-commit    # install post-commit alt
#   bash scripts/git-hooks/install.sh both           # install both
#   bash scripts/git-hooks/install.sh --uninstall    # remove c2004-owned hooks
#
# Safety:
#   * If a hook already exists and lacks the "c2004 sumr-refresh" marker,
#     it's backed up to <name>.backup.<timestamp> before overwrite.
#   * Re-running is a no-op (idempotent) when already installed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve repo root: prefer `git rev-parse`, fall back to ../.. relative to
# this script. `(cd && pwd)` must be a subshell so a successful
# `rev-parse` short-circuits cleanly (without the parens `cd && pwd` would
# always execute due to `||/&&` left-associativity).
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null \
  || (cd "${SCRIPT_DIR}/../.." && pwd))"

# Honour core.hooksPath when set (e.g. custom dotfiles), default to
# .git/hooks otherwise. `git rev-parse --git-path hooks` does both.
HOOKS_DIR="$(git -C "${REPO_ROOT}" rev-parse --git-path hooks 2>/dev/null || echo "${REPO_ROOT}/.git/hooks")"
case "${HOOKS_DIR}" in
  /*) : ;;
  *)  HOOKS_DIR="${REPO_ROOT}/${HOOKS_DIR}" ;;
esac

MARKER="c2004 sumr-refresh"

mkdir -p "${HOOKS_DIR}"
[ -d "${HOOKS_DIR}" ] || { echo "[install-hook] cannot resolve hooks dir (${HOOKS_DIR})" >&2; exit 3; }

log() { echo "[install-hook] $*"; }

install_one() {
  local name="$1"
  local src="${SCRIPT_DIR}/${name}"
  local dest="${HOOKS_DIR}/${name}"

  [ -f "${src}" ] || { log "missing ${src}"; return 2; }

  if [ -e "${dest}" ]; then
    if grep -q "${MARKER}" "${dest}" 2>/dev/null; then
      log "${name}: already installed (idempotent skip)"
      cp "${src}" "${dest}"  # refresh to latest template
      chmod +x "${dest}"
      return 0
    fi
    local backup="${dest}.backup.$(date +%s)"
    log "${name}: existing foreign hook found — backing up to $(basename "${backup}")"
    mv "${dest}" "${backup}"
  fi

  cp "${src}" "${dest}"
  chmod +x "${dest}"
  log "${name}: installed → .git/hooks/${name}"
}

uninstall_one() {
  local name="$1"
  local dest="${HOOKS_DIR}/${name}"
  [ -e "${dest}" ] || return 0
  if grep -q "${MARKER}" "${dest}" 2>/dev/null; then
    rm -f "${dest}"
    log "${name}: removed"
  else
    log "${name}: NOT our hook (no marker) — leaving alone"
  fi
}

mode="${1:-post-merge}"

case "${mode}" in
  --uninstall)
    uninstall_one post-merge
    uninstall_one post-commit
    ;;
  post-merge|post-commit)
    install_one "${mode}"
    ;;
  both)
    install_one post-merge
    install_one post-commit
    ;;
  -h|--help)
    sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "[install-hook] unknown mode: ${mode}" >&2
    echo "try: post-merge | post-commit | both | --uninstall" >&2
    exit 2
    ;;
esac
