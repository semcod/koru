"""Regression guard: GUI injection unit tests live in the ``gillm`` package."""

from __future__ import annotations

from gillm.injection import Injector, InjectorError, OsInjectorProfile, try_drive_with_profile


def test_gillm_injection_surface_available_from_koru_dependency() -> None:
    """Koru depends on ``gillm`` for keyboard/OS GUI control; tests run in ``gillm/tests/``."""
    assert Injector is not None
    assert InjectorError is not None
    assert OsInjectorProfile is not None
    assert callable(try_drive_with_profile)
