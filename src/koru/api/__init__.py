"""Compatibility alias for ``koru.api`` → :mod:`koruapi`."""

import sys

import koruapi as _canonical

sys.modules[__name__] = _canonical
