#!/usr/bin/env bash
# Source this file to get ergonomic lane helpers for common IDE workflows.
#
# Example:
#   source scripts/koru-autopilot-lanes.sh
#   lane:windsurf
#   lane:status

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This script is intended to be sourced, not executed directly." >&2
  echo "Use: source scripts/koru-autopilot-lanes.sh" >&2
  exit 2
fi

_koru_lane_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${here}/.." && pwd
}

_koru_lane_script() {
  local root
  root="$(_koru_lane_root)"
  printf '%s/scripts/koru-autopilot-lane.sh\n' "$root"
}

_koru_lane_exec() {
  koruenv "$@"
}

_koru_lane_require_helper() {
  if ! command -v koruenv >/dev/null 2>&1; then
    echo "missing command: koruenv" >&2
    echo "install standalone package first: pip install -e ./packages/koruenv" >&2
    return 1
  fi
}

_koru_lane_is_ide() {
  case "$1" in
    auto|vscode|vscodium|cursor|windsurf|jetbrains|zed|antigravity)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

lane:use() {
  local ide="${1:-}"
  local instance="${2:-}"
  [[ -n "$ide" ]] || {
    echo "usage: lane:use <ide> [instance]" >&2
    return 2
  }
  if [[ -z "$instance" ]]; then
    instance="${ide}-main"
  fi
  _koru_lane_require_helper || return $?
  eval "$(_koru_lane_exec env "$ide" "$instance")"
  echo "lane active: ide=${KORU_AUTOPILOT_IDE} instance=${KORU_AUTOPILOT_INSTANCE} socket=${KORU_AUTOPILOT_SOCKET}"
}

lane:status() {
  local ide instance
  case "$#" in
    0)
      ide="${KORU_AUTOPILOT_IDE:-auto}"
      instance="${KORU_AUTOPILOT_INSTANCE:-${ide}-main}"
      ;;
    1)
      if _koru_lane_is_ide "$1"; then
        ide="$1"
        instance="${KORU_AUTOPILOT_INSTANCE:-${ide}-main}"
      else
        ide="${KORU_AUTOPILOT_IDE:-auto}"
        instance="$1"
      fi
      ;;
    *)
      ide="$1"
      instance="$2"
      ;;
  esac
  _koru_lane_require_helper || return $?
  _koru_lane_exec status "$ide" "$instance"
}

lane:run() {
  local ide instance
  if [[ "${1:-}" == "--" ]]; then
    ide="${KORU_AUTOPILOT_IDE:-}"
    instance="${KORU_AUTOPILOT_INSTANCE:-}"
    shift
  else
    ide="${1:-}"
    instance="${2:-}"
    [[ -n "$ide" && -n "$instance" && "${3:-}" == "--" ]] || {
      echo "usage: lane:run <ide> <instance> -- <command> [args...]" >&2
      echo "or after lane:use: lane:run -- <command> [args...]" >&2
      return 2
    }
    shift 3
  fi

  [[ -n "$ide" && -n "$instance" ]] || {
    echo "missing active lane; run lane:use first or pass <ide> <instance>" >&2
    return 2
  }
  [[ $# -ge 1 ]] || {
    echo "missing command for lane:run" >&2
    return 2
  }

  _koru_lane_require_helper || return $?
  _koru_lane_exec run "$ide" "$instance" -- "$@"
}

lane:windsurf() { lane:use windsurf "${1:-windsurf-main}"; }
lane:vscode() { lane:use vscode "${1:-vscode-main}"; }
lane:vscodium() { lane:use vscodium "${1:-vscodium-main}"; }
lane:cursor() { lane:use cursor "${1:-cursor-main}"; }
lane:jetbrains() { lane:use jetbrains "${1:-jetbrains-main}"; }
lane:zed() { lane:use zed "${1:-zed-main}"; }
