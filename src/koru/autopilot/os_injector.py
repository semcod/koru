"""Compatibility alias for legacy :mod:`koru.autopilot.os_injector` imports."""

from __future__ import annotations

import sys

import gillm.injection.os_injector as _gillm_os_injector

sys.modules[__name__] = _gillm_os_injector
