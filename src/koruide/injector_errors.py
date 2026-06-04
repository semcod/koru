"""Deprecated compatibility alias — use :mod:`gillm.injection.errors` instead."""

from __future__ import annotations

import sys
import warnings

warnings.warn(
    "koruide.injector_errors is deprecated; import from gillm.injection.errors instead",
    DeprecationWarning,
    stacklevel=2,
)

import gillm.injection.errors as _gillm_errors

sys.modules[__name__] = _gillm_errors
