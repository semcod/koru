"""Compatibility alias for ``koru.serve`` → :mod:`koruapi.dashboard_serve`."""

from __future__ import annotations

import sys

import koruapi.dashboard_serve as _canonical

sys.modules[__name__] = _canonical
