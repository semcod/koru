"""Compatibility alias for legacy :mod:`koru.autopilot.injector` imports."""

from __future__ import annotations

import sys

from koruide import injector as _koruide_injector

sys.modules[__name__] = _koruide_injector
