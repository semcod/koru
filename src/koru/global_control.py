"""Machine-wide koru kill-switch.

One marker file controls every koru runtime on this host: the autonomous
loop, autopilot, fleet, queue drains, MCP server and the git co-author hook
all check it before doing agent work. ``koru off`` creates the marker,
``koru on`` removes it, ``koru status`` reports the current state.

The marker lives outside any project so a single command silences koru
across all repositories:

    $KORU_GLOBAL_CONTROL_DIR/killswitch          (explicit override, tests)
    $XDG_CONFIG_HOME/koru/killswitch             (when XDG_CONFIG_HOME set)
    ~/.config/koru/killswitch                    (default)

``KORU_GLOBAL_DISABLE=1`` in the environment behaves like the marker file
(useful for CI or one-off shells). Shell hooks and systemd units check the
same path, so keep the location stable.
"""

from __future__ import annotations

import getpass
import json
import os
import socket
from datetime import UTC, datetime
from pathlib import Path

from koru.env_flags import env_truthy

KILLSWITCH_ENV = "KORU_GLOBAL_DISABLE"
KILLSWITCH_DIR_ENV = "KORU_GLOBAL_CONTROL_DIR"
KILLSWITCH_FILENAME = "killswitch"

#: systemd user units that ``koru off`` stops (best effort).
MANAGED_USER_UNITS = (
    "koru-autonomous.service",
    "koru-autopilot.service",
    "coru-supervisor.service",
)


def global_control_dir() -> Path:
    """Directory holding the machine-wide koru control state."""
    override = os.environ.get(KILLSWITCH_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "koru"


def killswitch_path() -> Path:
    return global_control_dir() / KILLSWITCH_FILENAME


def is_globally_disabled() -> bool:
    """True when agent work must not run on this machine."""
    if env_truthy(KILLSWITCH_ENV):
        return True
    try:
        return killswitch_path().exists()
    except OSError:
        return False


def read_killswitch_state() -> dict[str, object]:
    """Return the recorded state (empty dict when enabled or unreadable)."""
    path = killswitch_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"raw": raw.strip()}
    return data if isinstance(data, dict) else {"raw": raw.strip()}


def global_disable(reason: str = "") -> Path:
    """Create the kill-switch marker; returns its path (idempotent)."""
    path = killswitch_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "disabled_at": datetime.now(UTC).isoformat(),
        "reason": reason or "disabled via `koru off`",
        "host": socket.gethostname(),
        "user": _current_user(),
    }
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def global_enable() -> bool:
    """Remove the kill-switch marker. Returns True when a marker was removed."""
    path = killswitch_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def disabled_message(component: str) -> str:
    """Human-readable refusal line for a blocked component."""
    state = read_killswitch_state()
    reason = str(state.get("reason") or "").strip()
    since = str(state.get("disabled_at") or "").strip()
    detail = f" (reason: {reason})" if reason else ""
    when = f" since {since}" if since else ""
    if env_truthy(KILLSWITCH_ENV):
        return (
            f"koru {component}: koru is disabled via {KILLSWITCH_ENV}=1; "
            f"unset it to run."
        )
    return (
        f"koru {component}: koru is globally disabled{when}{detail}. "
        f"Run `koru on` to re-enable (marker: {killswitch_path()})."
    )


def _current_user() -> str:
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return os.environ.get("USER", "unknown")


__all__ = [
    "KILLSWITCH_DIR_ENV",
    "KILLSWITCH_ENV",
    "KILLSWITCH_FILENAME",
    "MANAGED_USER_UNITS",
    "disabled_message",
    "global_control_dir",
    "global_disable",
    "global_enable",
    "is_globally_disabled",
    "killswitch_path",
    "read_killswitch_state",
]
