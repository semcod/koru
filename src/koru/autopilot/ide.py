"""Compatibility alias for legacy :mod:`koru.autopilot.ide` imports."""

from __future__ import annotations

import sys

from koruide import ide as _koruide_ide

sys.modules[__name__] = _koruide_ide
