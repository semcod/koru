#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -n "${KORU_PYTHON:-}" ]; then
  PYTHON="$KORU_PYTHON"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi

pytest_args=(tests/)
use_xdist=true
changed_only=false
explicit_selection=false

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

pytest_help=""
if [ "$use_xdist" = true ]; then
  pytest_help="$("$PYTHON" -m pytest --help 2>/dev/null || true)"
fi

if [ "$use_xdist" = true ] && grep -q -- "--numprocesses" <<<"$pytest_help"; then
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

  "$PYTHON" -m pytest -n "$workers" --dist loadgroup "${daemon_excluded_args[@]}"
  rc1=$?

  "$PYTHON" -m pytest -q tests/test_autopilot_daemon.py
  rc2=$?

  if [ $rc1 -ne 0 ] || [ $rc2 -ne 0 ]; then
    exit 1
  fi
  exit 0
elif [ "$use_xdist" = true ]; then
  echo "pytest-xdist is not installed; running tests serially. Install dev extras with: pip install -e '.[dev]'" >&2
fi

exec "$PYTHON" -m pytest "${pytest_args[@]}"
