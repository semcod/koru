"""Koru Autopilot Daemon package.

UNIX-socket broker between IDE plugins and koru CLI clients. Split out of
the legacy single-file ``koruide/daemon.py`` (deleted) into:

* :mod:`koruide.daemon.server` — :class:`AutopilotDaemon`, selector loop, I/O
* :mod:`koruide.daemon.handlers` — per-message-type handlers (drive, hello, …)
* :mod:`koruide.daemon.protocol` — ``_Client``, ``_PluginEventHandoff``,
  ``_peer_uid``, ``_daemon_package_version``
* :mod:`koruide.daemon.storage` — thread-safe in-memory console-log + session
  ring, with 10 KB-per-session clamping

This ``__init__`` is also a **compatibility shim** for callers that still
reach into the old monolithic-module namespace (``from koruide import
daemon as koruide_daemon_mod`` followed by ``koruide_daemon_mod._verbose_io``,
``koruide_daemon_mod.time.monotonic``, …). Anything previously importable as
an attribute of ``koruide.daemon`` is re-exported here so the public surface
of the rename is unchanged.
"""

from __future__ import annotations

import os
import time

from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.daemon.protocol import _peer_uid
from koruide.daemon.handlers import _default_handoff
from koruide.daemon.server import AutopilotDaemon, _env_truthy, _verbose_io
from koruide.daemon.storage import (
    add_console_log,
    clear_console_logs,
    get_console_logs,
    start_new_log_session,
)

__all__ = [
    "AutopilotDaemon",
    "start_new_log_session",
    "add_console_log",
    "get_console_logs",
    "clear_console_logs",
    "_peer_uid",
    "_default_handoff",
    "_env_truthy",
    "_verbose_io",
    "detect_running_ides",
    "os",
    "time",
]
