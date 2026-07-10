"""CLI for the machine-wide koru kill-switch: ``koru on|off|status``."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from koru.global_control import (
    KILLSWITCH_ENV,
    MANAGED_USER_UNITS,
    global_disable,
    global_enable,
    is_globally_disabled,
    killswitch_path,
    read_killswitch_state,
)


def _systemctl_user(*args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["systemctl", "--user", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _stop_managed_units() -> list[str]:
    """Stop koru user services (best effort). Returns units that were running."""
    stopped: list[str] = []
    for unit in MANAGED_USER_UNITS:
        check = _systemctl_user("is-active", unit)
        if check is None or check.stdout.strip() != "active":
            continue
        result = _systemctl_user("stop", unit)
        if result is not None and result.returncode == 0:
            stopped.append(unit)
    return stopped


def _unit_states() -> dict[str, str]:
    states: dict[str, str] = {}
    for unit in MANAGED_USER_UNITS:
        result = _systemctl_user("is-active", unit)
        states[unit] = result.stdout.strip() if result is not None else "unknown"
    return states


def off_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru off",
        description="Disable koru globally: agent loops, queue drains, MCP server "
        "and the git co-author hook stop doing agent work on this machine.",
    )
    parser.add_argument("--reason", default="", help="Why koru is being disabled.")
    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="Only set the kill-switch; do not stop running koru user services.",
    )
    args = parser.parse_args(argv)

    path = global_disable(args.reason)
    print(f"koru off: kill-switch set at {path}")
    if not args.no_stop:
        stopped = _stop_managed_units()
        for unit in stopped:
            print(f"koru off: stopped {unit}")
        if not stopped:
            print("koru off: no running koru user services found")
    print("koru off: re-enable with `koru on`")
    return 0


def on_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru on",
        description="Re-enable koru globally (removes the kill-switch marker).",
    )
    parser.parse_args(argv)

    removed = global_enable()
    if removed:
        print("koru on: kill-switch removed; koru is enabled again")
    else:
        print("koru on: koru was not disabled (no kill-switch marker)")
    if is_globally_disabled():
        print(
            f"koru on: warning: {KILLSWITCH_ENV} is set in this environment; "
            "koru stays disabled until you unset it",
            file=sys.stderr,
        )
        return 1
    print(
        "koru on: note: stopped services are not restarted automatically "
        "(start them with `systemctl --user start <unit>` if needed)"
    )
    return 0


def status_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru status",
        description="Show the global koru enable/disable state.",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    disabled = is_globally_disabled()
    state = read_killswitch_state()
    units = _unit_states()

    if args.json:
        print(
            json.dumps(
                {
                    "disabled": disabled,
                    "killswitch_path": str(killswitch_path()),
                    "killswitch": state,
                    "env_override": bool(state) is not disabled and disabled,
                    "user_units": units,
                },
                indent=2,
            )
        )
        return 0

    print(f"koru: {'DISABLED' if disabled else 'enabled'}")
    print(f"  kill-switch: {killswitch_path()}" + ("" if disabled else " (absent)"))
    if disabled and state:
        if state.get("reason"):
            print(f"  reason: {state['reason']}")
        if state.get("disabled_at"):
            print(f"  since:  {state['disabled_at']}")
    for unit, active in units.items():
        print(f"  {unit}: {active}")
    if not disabled:
        print("  disable with: koru off [--reason '...']")
    else:
        print("  enable with:  koru on")
    return 0


__all__ = ["off_main", "on_main", "status_main"]
