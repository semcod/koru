"""Deprecated compatibility alias for legacy :mod:`koru.autopilot.os_injector` imports.

Use :mod:`gillm.injection.os_injector` instead.
"""

from __future__ import annotations

import sys
import warnings

warnings.warn(
    "koru.autopilot.os_injector is deprecated; import from gillm.injection.os_injector instead",
    DeprecationWarning,
    stacklevel=2,
)

import gillm.injection.os_injector as _gillm_os_injector

sys.modules[__name__] = _gillm_os_injector
