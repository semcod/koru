"""Compatibility alias for legacy :mod:`koru.autopilot.injector` imports."""

from __future__ import annotations

import sys

import gillm.injection.injector as _gillm_injector

sys.modules[__name__] = _gillm_injector
