"""Deprecated compatibility redirect for legacy :mod:`koruos` imports.

Use :mod:`gillm.focus` instead::

    from gillm.focus import OsStrategy, resolve_active_os_strategy
    from gillm.focus.wayland import WaylandLinuxStrategy

This module will be removed in a future koru release.
"""

from __future__ import annotations

import sys
import warnings

_DEPRECATION = (
    "koruos is deprecated; import from gillm.focus instead "
    "(e.g. from gillm.focus import resolve_active_os_strategy). "
    "See gillm.focus.wayland / gillm.focus.x11 for platform strategies."
)

warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)

import gillm.focus as _gillm_focus
import gillm.focus.darwin as _darwin
import gillm.focus.registry as _registry
import gillm.focus.strategy as _base
import gillm.focus.wayland as _wayland
import gillm.focus.windows as _windows
import gillm.focus.x11 as _x11

sys.modules[__name__] = _gillm_focus
sys.modules["koruos.strategies"] = _gillm_focus
sys.modules["koruos.strategies.wayland_linux"] = _wayland
sys.modules["koruos.strategies.x11_linux"] = _x11
sys.modules["koruos.strategies.darwin"] = _darwin
sys.modules["koruos.strategies.windows"] = _windows
sys.modules["koruos.strategies.registry"] = _registry
sys.modules["koruos.strategies.base"] = _base
