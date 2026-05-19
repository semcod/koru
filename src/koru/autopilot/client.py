"""Compatibility shim: legacy import path for `AutopilotClient`.

Runtime code should gradually migrate to importing from :mod:`koruide.client`.
"""

from __future__ import annotations

from koruide.client import AutopilotClient

__all__ = ["AutopilotClient"]
