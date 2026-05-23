"""Backwards-compatibility shim for the old ``koruide.daemon_storage`` path.

The console-log + session storage was moved to :mod:`koruide.daemon.storage`
when the monolithic ``daemon.py`` was split into a package. This module
keeps the legacy import path alive for any caller (in-tree shims, vendored
forks, external plugins) that still references ``koruide.daemon_storage``
directly. Prefer :mod:`koruide.daemon.storage` in new code.
"""

from __future__ import annotations

from koruide.daemon.storage import (
    add_console_log,
    clear_console_logs,
    get_console_logs,
    start_new_log_session,
)

__all__ = [
    "start_new_log_session",
    "add_console_log",
    "get_console_logs",
    "clear_console_logs",
]
