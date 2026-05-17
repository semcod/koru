"""Compatibility shim: legacy import path for autopilot daemon.

Runtime code should gradually migrate to importing from :mod:`koruide.daemon`.
"""

from __future__ import annotations

from koruide.daemon import AutopilotDaemon, _default_handoff, _peer_uid, detect_running_ides, os

__all__ = [
    "AutopilotDaemon",
    "_default_handoff",
    "_peer_uid",
    "detect_running_ides",
    "os",
]
