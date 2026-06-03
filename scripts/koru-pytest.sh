#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -n "${KORU_PYTHON:-}" ]; then
  PYTHON="$KORU_PYTHON"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [ -x "./.venv/bin/python" ]; then
  PYTHON="./.venv/bin/python"
else
  PYTHON="python3"
fi

pytest_args=(tests/)
use_xdist=true
changed_only=false
explicit_selection=false

_is_truthy() {
  case "${1:-}" in
    1|true|True|TRUE|yes|Yes|YES|on|On|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

_has_xdist() {
  "$PYTHON" -c "import xdist" >/dev/null 2>&1
}

_ensure_xdist() {
  if _has_xdist; then
    return 0
  fi
  if ! _is_truthy "${KORU_PYTEST_AUTO_INSTALL_XDIST:-1}"; then
    return 1
  fi
  echo "pytest-xdist is missing; installing pytest-xdist into current environment..." >&2
  if "$PYTHON" -m pip install --disable-pip-version-check -q pytest-xdist >/dev/null 2>&1; then
    _has_xdist
    return $?
  fi
  return 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all)
      pytest_args+=(-m "")
      ;;
    --changed)
      changed_only=true
      ;;
    --fast)
      pytest_args+=(-q)
      ;;
    --profile)
      pytest_args+=("--durations=${KORU_PYTEST_DURATIONS:-25}" "--durations-min=${KORU_PYTEST_DURATIONS_MIN:-0.25}")
      ;;
    --quick)
      pytest_args+=(-q --maxfail=1 --no-header --ff)
      ;;
    --serial)
      use_xdist=false
      ;;
    --verbose)
      pytest_args+=(-v)
      ;;
    --)
      shift
      pytest_args+=("$@")
      break
      ;;
    *)
      if [[ "$1" == tests/* || "$1" == *".py" || "$1" == *"::"* ]]; then
        explicit_selection=true
      fi
      pytest_args+=("$1")
      ;;
  esac
  shift
done

if [ "$explicit_selection" = true ] && [ "${pytest_args[0]}" = "tests/" ]; then
  pytest_args=("${pytest_args[@]:1}")
fi

if [ "$changed_only" = true ]; then
  mapfile -t changed_tests < <(
    git diff --name-only --diff-filter=ACMRTUXB "${KORU_PYTEST_CHANGED_BASE:-HEAD}" -- tests \
      | grep -E '^tests/(test_.*|.*_test)\.py$' || true
  )
  if [ "${#changed_tests[@]}" -gt 0 ]; then
    pytest_args=("${changed_tests[@]}" "${pytest_args[@]:1}")
  else
    echo "No changed pytest files found under tests/; falling back to the default test selection." >&2
  fi
fi

workers="${KORU_PYTEST_WORKERS:-${PYTEST_WORKERS:-${TEST_JOBS:-auto}}}"
dist="${KORU_PYTEST_DIST:-${PYTEST_DIST:-loadfile}}"
case "$workers" in
  0|1|false|False|FALSE|off|Off|OFF|no|No|NO)
    use_xdist=false
    ;;
esac

if [ "$use_xdist" = true ] && _ensure_xdist; then
  if [ "$explicit_selection" = true ]; then
    # Explicit file/test selection — run exactly what was asked (may include daemon tests).
    pytest_args=(-n "$workers" --dist "$dist" "${pytest_args[@]}")
    exec "$PYTHON" -m pytest "${pytest_args[@]}"
  fi

  # Run everything except daemon tests in parallel, then daemon tests serially.
  # This avoids fork/spawn issues with background threads and unix sockets.
  daemon_excluded_args=("${pytest_args[@]}")
  for i in "${!daemon_excluded_args[@]}"; do
    if [ "${daemon_excluded_args[$i]}" = "tests/" ]; then
      daemon_excluded_args[$i]="tests/"
      # Insert exclusion after the directory argument
      daemon_excluded_args=("${daemon_excluded_args[@]:0:$((i+1))}" "--ignore=tests/test_autopilot_daemon.py" "${daemon_excluded_args[@]:$((i+1))}")
      break
    fi
  done

  "$PYTHON" -m pytest -n "$workers" --dist "$dist" "${daemon_excluded_args[@]}"
  rc1=$?

  "$PYTHON" -m pytest -q tests/test_autopilot_daemon.py
  rc2=$?

  if [ $rc1 -ne 0 ] || [ $rc2 -ne 0 ]; then
    exit 1
  fi
  exit 0
elif [ "$use_xdist" = true ]; then
  echo "pytest-xdist is not installed; running tests serially. Install dev extras with: pip install -e '.[dev]' (or set KORU_PYTEST_AUTO_INSTALL_XDIST=1)." >&2
fi

exec "$PYTHON" -m pytest "${pytest_args[@]}"
