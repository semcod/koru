"""Compatibility alias for legacy :mod:`koru.autopilot.plugin_installer` imports."""

from __future__ import annotations

import sys

from koruide import plugin_installer as _koruide_plugin_installer

sys.modules[__name__] = _koruide_plugin_installer
