"""Compatibility alias for legacy :mod:`koru.autopilot.os_injector` imports."""

from __future__ import annotations

import sys

from koruide import os_injector as _koruide_os_injector

sys.modules[__name__] = _koruide_os_injector
