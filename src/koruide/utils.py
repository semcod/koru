"""Small koruide-internal helpers that have no external dependency."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_xdg_path(relative_path: str) -> Path:
    """Resolve an XDG-style config path.

    Args:
        relative_path: Relative path from the XDG config base
            (e.g. ``"koru/autopilot.toml"``).

    Returns:
        Absolute path to the XDG config location.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / relative_path
