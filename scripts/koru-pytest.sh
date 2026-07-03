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
critical_tests=(
  tests/test_cli.py::test_cli_shim_reloads_partial_legacy_module
  tests/test_cli.py::TestSubcommandDispatch::test_table_contains_all_documented_subcommands
  tests/test_cli.py::TestSubcommandDispatch::test_table_values_are_callables
  tests/test_agent_backend_runtime.py
  tests/test_autonomous_startup.py
  tests/test_autonomous_plugin_runtime.py
  tests/test_autonomous_readiness.py
  tests/test_autopilot_cli_direct_drive.py
  tests/test_autopilot_plugin_installer.py::test_resolve_target_ide_uses_integrated_terminal_hint
  tests/test_autopilot_plugin_installer.py::test_install_plugin_targets_vscodium_from_integrated_terminal
  tests/test_autopilot_plugin_installer.py::test_install_plugin_explicit_vscode_does_not_use_codium_hint
  tests/test_command_picker.py
  tests/test_doctor_facade.py
  tests/test_gillm_ide_client.py
  tests/test_gillm_recovery.py
  tests/test_autonomous_gillm_fallback.py
  tests/test_facade_late_binding_contract.py
  tests/test_ide_client.py
  tests/test_ide_reload.py
  tests/test_package_deduplication.py::test_autopilot_config_is_gillm_canonical
  tests/test_package_deduplication.py::test_koru_injection_shims_point_at_gillm
  tests/test_package_deduplication.py::test_no_duplicate_injector_implementation_in_koru_src
  tests/ides/test_all_ide_strategies.py
)
use_xdist=true
changed_only=false
explicit_selection=false
critical_only=false
critical_selection=false
include_all=false

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

_select_critical_tests() {
  local selected=()
  local test_file
  local test_path

  for test_file in "${critical_tests[@]}"; do
    test_path="${test_file%%::*}"
    if [ -f "$test_path" ]; then
      selected+=("$test_file")
    fi
  done

  if [ "${#selected[@]}" -eq 0 ]; then
    echo "No critical pytest files found; falling back to the default test selection." >&2
    return 1
  fi

  pytest_args=("${selected[@]}" "${pytest_args[@]:1}")
  critical_selection=true
  echo "koru-pytest: critical selection (${#selected[@]} targets); use --all for the full suite." >&2
}

_selection_includes_daemon() {
  local arg
  for arg in "${pytest_args[@]}"; do
    case "$arg" in
      tests|tests/|tests/test_autopilot_daemon.py|tests/test_autopilot_daemon.py::*)
        return 0
        ;;
    esac
  done
  return 1
}

_has_pytest_selection() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      tests|tests/|tests/*|*.py|*::*)
        return 0
        ;;
    esac
  done
  return 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all)
      include_all=true
      pytest_args+=(-m "")
      ;;
    --changed)
      changed_only=true
      ;;
    --critical)
      critical_only=true
      ;;
    --fast)
      pytest_args+=(-q)
      critical_only=true
      ;;
    --profile)
      pytest_args+=("--durations=${KORU_PYTEST_DURATIONS:-25}" "--durations-min=${KORU_PYTEST_DURATIONS_MIN:-0.25}")
      ;;
    --quick)
      pytest_args+=(-q --maxfail=1 --no-header --ff)
      critical_only=true
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

if [ "$critical_only" = true ] \
  && [ "$include_all" = false ] \
  && [ "$explicit_selection" = false ] \
  && [ "${pytest_args[0]}" = "tests/" ]; then
  _select_critical_tests || true
fi

workers="${KORU_PYTEST_WORKERS:-${PYTEST_WORKERS:-${TEST_JOBS:-auto}}}"
dist="${KORU_PYTEST_DIST:-${PYTEST_DIST:-loadfile}}"
if [ "$critical_selection" = true ] && [ "$workers" = "auto" ]; then
  if _is_truthy "${KORU_PYTEST_CRITICAL_XDIST:-0}"; then
    workers="${KORU_PYTEST_CRITICAL_WORKERS:-4}"
  else
    use_xdist=false
  fi
fi
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

  # Run daemon tests serially when they are part of the selected suite. This
  # avoids fork/spawn issues with background threads and unix sockets.
  run_daemon_serial=false
  if _selection_includes_daemon; then
    run_daemon_serial=true
  fi

  daemon_excluded_args=()
  for arg in "${pytest_args[@]}"; do
    if [ "$arg" = "tests/test_autopilot_daemon.py" ]; then
      continue
    fi
    daemon_excluded_args+=("$arg")
  done

  for i in "${!daemon_excluded_args[@]}"; do
    if [ "${daemon_excluded_args[$i]}" = "tests/" ] || [ "${daemon_excluded_args[$i]}" = "tests" ]; then
      daemon_excluded_args=("${daemon_excluded_args[@]:0:$((i+1))}" "--ignore=tests/test_autopilot_daemon.py" "${daemon_excluded_args[@]:$((i+1))}")
      break
    fi
  done

  if _has_pytest_selection "${daemon_excluded_args[@]}"; then
    "$PYTHON" -m pytest -n "$workers" --dist "$dist" "${daemon_excluded_args[@]}"
  fi
  if [ "$run_daemon_serial" = true ]; then
    "$PYTHON" -m pytest -q tests/test_autopilot_daemon.py
  fi
  exit 0
elif [ "$use_xdist" = true ]; then
  echo "pytest-xdist is not installed; running tests serially. Install dev extras with: pip install -e '.[dev]' (or set KORU_PYTEST_AUTO_INSTALL_XDIST=1)." >&2
fi

exec "$PYTHON" -m pytest "${pytest_args[@]}"
