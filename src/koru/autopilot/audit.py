"""Compatibility alias for legacy :mod:`koru.autopilot.audit` imports."""

from __future__ import annotations

import sys

from koruide import audit as _koruide_audit

sys.modules[__name__] = _koruide_audit
