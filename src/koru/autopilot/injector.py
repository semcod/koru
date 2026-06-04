"""Deprecated compatibility alias for legacy :mod:`koru.autopilot.injector` imports.

Use :mod:`gillm.injection.injector` instead.
"""

from __future__ import annotations

import sys
import warnings

warnings.warn(
    "koru.autopilot.injector is deprecated; import from gillm.injection.injector instead",
    DeprecationWarning,
    stacklevel=2,
)

import gillm.injection.injector as _gillm_injector

sys.modules[__name__] = _gillm_injector
