"""Client helper functions for autopilot CLI."""

import json
import os
import sys
from pathlib import Path
from typing import Any


def call_daemon_method(
    client: Any,
    method_name: str,
    error_message_prefix: str,
    not_running_return_code: int = 1,
) -> int:
    """Call a daemon method with standard error handling and JSON output.

    Args:
        client: The autopilot client instance.
        method_name: Name of the method to call (e.g., "status", "shutdown").
        error_message_prefix: Prefix for error messages (e.g., "koru autopilot status").
        not_running_return_code: Return code when daemon is not running (default: 1).

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if not client.is_running():
        print(
            "koru autopilot: daemon is NOT running"
            if not_running_return_code == 1
            else "koru autopilot: daemon is not running",
        )
        return not_running_return_code

    try:
        method = getattr(client, method_name)
        info = method()
    except (OSError, RuntimeError) as exc:
        print(f"{error_message_prefix}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


def resolve_xdg_path(relative_path: str) -> Path:
    """Resolve an XDG-style config path.

    Args:
        relative_path: Relative path from the XDG config base (e.g., "systemd/user").

    Returns:
        Absolute path to the XDG config location.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / relative_path
