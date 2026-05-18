"""Compatibility alias for ``koru.dsl`` → :mod:`korudsl`."""

from __future__ import annotations

import sys

from korudsl import *  # noqa: F403

sys.modules[__name__] = sys.modules["korudsl"]
