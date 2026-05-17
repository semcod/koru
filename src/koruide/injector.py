"""Keyboard/clipboard injector bridge for `koruide` extraction.

Current implementation re-exports legacy injector types from
`koru.autopilot.injector`.
"""

from __future__ import annotations

from koru.autopilot.injector import BackendStatus, InjectionResult, Injector, InjectorError

__all__ = [
    "BackendStatus",
    "InjectionResult",
    "InjectorError",
    "Injector",
]
