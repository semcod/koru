"""Deprecated compatibility alias — use :mod:`gillm.injection.injector` instead."""

from __future__ import annotations

import sys
import warnings

warnings.warn(
    "koruide.injector is deprecated; import from gillm.injection.injector instead",
    DeprecationWarning,
    stacklevel=2,
)

import gillm.injection.injector as _gillm_injector

sys.modules[__name__] = _gillm_injector
