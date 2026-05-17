"""Compatibility alias for legacy :mod:`koru.autopilot.config` imports."""

from __future__ import annotations

import sys

from koruide import config as _koruide_config

sys.modules[__name__] = _koruide_config
