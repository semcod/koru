"""Koru OS strategies.

Each operating system / display-server combination owns a separate
strategy file under :mod:`koruos.strategies`. Higher layers ask the
registry for the current platform's strategy instead of probing
``shutil.which("xdotool")`` or ``os.environ.get("WAYLAND_DISPLAY")``
inline. This removes the scattered ad-hoc decision tree that caused
recurring Wayland focus failures.
"""

from koruos.strategies.base import (
    FocusOutcome,
    KeySequence,
    OsCapabilities,
    OsStrategy,
)
from koruos.strategies.registry import (
    get_os_strategy,
    list_os_strategy_ids,
    register_os_strategy,
    resolve_active_os_strategy,
)

__all__ = [
    "FocusOutcome",
    "KeySequence",
    "OsCapabilities",
    "OsStrategy",
    "get_os_strategy",
    "list_os_strategy_ids",
    "register_os_strategy",
    "resolve_active_os_strategy",
]
