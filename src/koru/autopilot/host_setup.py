"""Compatibility alias for legacy :mod:`koru.autopilot.host_setup` imports."""

from __future__ import annotations

import sys

from koruide import host_setup as _koruide_host_setup

sys.modules[__name__] = _koruide_host_setup
