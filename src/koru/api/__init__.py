"""Compatibility alias for ``koru.api`` → :mod:`koruapi`."""

from __future__ import annotations

import sys

from koruapi import *  # noqa: F403

sys.modules[__name__] = sys.modules["koruapi"]
