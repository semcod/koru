"""Daemon bridge for `koruide` extraction.

Current implementation re-exports the legacy daemon while runtime callers
migrate to `koruide.*` import paths.
"""

from __future__ import annotations

from koru.autopilot.daemon import AutopilotDaemon

__all__ = ["AutopilotDaemon"]
