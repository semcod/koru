"""Compatibility alias for ``koru.mcp_server`` → :mod:`koruapi.mcp_server`."""

from __future__ import annotations

import sys

import koruapi.mcp_server as _canonical

sys.modules[__name__] = _canonical
