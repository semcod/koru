"""Compatibility redirect for legacy :mod:`koruos` imports."""

from __future__ import annotations

import sys
import gillm.focus as _gillm_focus

# Redirect the module itself
sys.modules[__name__] = _gillm_focus

# Also redirect the strategies subpackages to gillm.focus
import gillm.focus.wayland as _wayland
import gillm.focus.x11 as _x11
import gillm.focus.darwin as _darwin
import gillm.focus.windows as _windows
import gillm.focus.registry as _registry
import gillm.focus.strategy as _base

sys.modules["koruos.strategies.wayland_linux"] = _wayland
sys.modules["koruos.strategies.x11_linux"] = _x11
sys.modules["koruos.strategies.darwin"] = _darwin
sys.modules["koruos.strategies.windows"] = _windows
sys.modules["koruos.strategies.registry"] = _registry
sys.modules["koruos.strategies.base"] = _base
