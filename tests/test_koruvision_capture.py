from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

from koruvision.capture import VisionFrame, capture_monitor_png, list_monitors

pytest.importorskip("mss")


def _fake_grabber() -> mock.MagicMock:
    shot = SimpleNamespace(rgb=bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]), size=(2, 2))
    grabber = mock.MagicMock()
    grabber.monitors = [{}, {"left": 0, "top": 0, "width": 2, "height": 2}]
    grabber.grab.return_value = shot
    grabber.__enter__.return_value = grabber
    return grabber


def test_list_monitors_returns_at_least_one() -> None:
    with mock.patch("mss.MSS", return_value=_fake_grabber()):
        monitors = list_monitors()
    assert monitors == [{"left": 0, "top": 0, "width": 2, "height": 2}]


def test_capture_monitor_png_returns_frame() -> None:
    with mock.patch("mss.MSS", return_value=_fake_grabber()):
        frame = capture_monitor_png(0)
    assert isinstance(frame, VisionFrame)
    assert frame.mime == "image/png"
    assert frame.width == 2
    assert frame.height == 2
    assert frame.payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(frame.sha256) == 64
    assert frame.frame_id == frame.sha256[:16]
