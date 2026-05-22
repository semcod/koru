"""Ensure capture intervals never go below the 30s safety floor."""

from __future__ import annotations

import pytest

from koruvision.agent import MIN_CAPTURE_INTERVAL_SECONDS, normalize_capture_interval


def test_normalize_clamps_short_intervals_up() -> None:
    assert normalize_capture_interval(1.0) == MIN_CAPTURE_INTERVAL_SECONDS
    assert normalize_capture_interval(5.0) == MIN_CAPTURE_INTERVAL_SECONDS
    assert normalize_capture_interval(29.999) == MIN_CAPTURE_INTERVAL_SECONDS


def test_normalize_passes_long_intervals_through() -> None:
    assert normalize_capture_interval(30.0) == 30.0
    assert normalize_capture_interval(120.0) == 120.0


def test_normalize_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        normalize_capture_interval(0.0)
    with pytest.raises(ValueError):
        normalize_capture_interval(-5.0)
