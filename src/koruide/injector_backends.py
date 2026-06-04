"""Deprecated compatibility alias — use :mod:`gillm.injection.backends` instead."""

from __future__ import annotations

import sys
import warnings

warnings.warn(
    "koruide.injector_backends is deprecated; import from gillm.injection.backends instead",
    DeprecationWarning,
    stacklevel=2,
)

import gillm.injection.backends as _gillm_backends

sys.modules[__name__] = _gillm_backends
