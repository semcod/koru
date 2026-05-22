from __future__ import annotations

import struct
from types import SimpleNamespace
from unittest import mock

import pytest

from koruvision.capture import VisionFrame, capture_all_monitors, capture_monitor_png, list_monitors


def _require_mss() -> None:
    pytest.importorskip("mss")


def _fake_grabber(*, primary: bool = False) -> mock.MagicMock:
    shot = SimpleNamespace(
        rgb=bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]),
        size=(2, 2),
    )
    grabber = mock.MagicMock()
    grabber.monitors = [
        {"left": 0, "top": 0, "width": 4, "height": 2},
        {"left": 0, "top": 0, "width": 2, "height": 2, "is_primary": primary},
        {"left": 2, "top": 0, "width": 2, "height": 2},
    ]
    grabber.grab.return_value = shot
    grabber.__enter__.return_value = grabber
    return grabber


def _png(width: int = 3, height: int = 2) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def test_list_monitors_returns_at_least_one() -> None:
    _require_mss()
    with mock.patch("mss.mss", return_value=_fake_grabber(primary=True)):
        monitors = list_monitors()
    assert len(monitors) == 2
    assert any(monitor.get("is_primary") for monitor in monitors)


def test_capture_monitor_png_returns_frame(monkeypatch) -> None:
    _require_mss()
    monkeypatch.setenv("KORU_VISION_PROVIDER", "mss")
    with mock.patch("mss.mss", return_value=_fake_grabber(primary=True)):
        frame = capture_monitor_png(0, scale=1.0)
    assert isinstance(frame, VisionFrame)
    assert frame.mime == "image/png"
    assert frame.width == 2
    assert frame.height == 2
    assert frame.native_width == 2
    assert frame.native_height == 2
    assert frame.payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(frame.sha256) == 64
    assert frame.frame_id == frame.sha256[:16]


def test_capture_monitor_png_records_native_resolution_after_downscale(monkeypatch) -> None:
    _require_mss()
    monkeypatch.setenv("KORU_VISION_PROVIDER", "mss")
    pixels = []
    for _ in range(10 * 10):
        pixels.extend([10, 20, 30])
    shot = SimpleNamespace(rgb=bytes(pixels), size=(10, 10))
    grabber = mock.MagicMock()
    grabber.monitors = [
        {"left": 0, "top": 0, "width": 10, "height": 10},
        {"left": 0, "top": 0, "width": 10, "height": 10, "is_primary": True},
    ]
    grabber.grab.return_value = shot
    grabber.__enter__.return_value = grabber
    with mock.patch("mss.mss", return_value=grabber):
        frame = capture_monitor_png(0, scale=0.2)
    assert frame.native_width == 10
    assert frame.native_height == 10
    assert frame.width == 2
    assert frame.height == 2


def test_capture_monitor_png_skips_black_monitor(monkeypatch) -> None:
    _require_mss()
    monkeypatch.setenv("KORU_VISION_PROVIDER", "mss")
    black = SimpleNamespace(rgb=b"\x00\x00\x00" * 12, size=(2, 2))
    good = SimpleNamespace(
        rgb=bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]),
        size=(2, 2),
    )
    grabber = mock.MagicMock()
    grabber.monitors = [
        {"left": 0, "top": 0, "width": 4, "height": 2},
        {"left": 0, "top": 0, "width": 2, "height": 2, "is_primary": True},
        {"left": 2, "top": 0, "width": 2, "height": 2},
    ]
    grabber.grab.side_effect = [black, good]
    grabber.__enter__.return_value = grabber
    with mock.patch("mss.mss", return_value=grabber):
        frame = capture_monitor_png(None, scale=1.0)
    assert frame.monitor_id == 1


def test_capture_all_monitors_returns_frame_per_display(monkeypatch) -> None:
    _require_mss()
    monkeypatch.setenv("KORU_VISION_PROVIDER", "mss")
    pixels = bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])
    shot = SimpleNamespace(rgb=pixels, size=(2, 2))
    grabber = mock.MagicMock()
    grabber.monitors = [
        {"left": 0, "top": 0, "width": 4, "height": 2},
        {"left": 0, "top": 0, "width": 2, "height": 2, "is_primary": True, "output": "DP-1"},
        {"left": 2, "top": 0, "width": 2, "height": 2, "output": "DP-2"},
    ]
    grabber.grab.return_value = shot
    grabber.__enter__.return_value = grabber
    with mock.patch("mss.mss", return_value=grabber):
        frames = capture_all_monitors(scale=1.0)
    assert [frame.monitor_id for frame in frames] == [0, 1]
    assert [frame.output for frame in frames] == ["DP-1", "DP-2"]


def test_capture_monitor_png_auto_falls_back_to_portal_on_wayland(monkeypatch, capsys) -> None:
    from koruvision.providers.base import ProviderAvailability

    monkeypatch.delenv("KORU_VISION_BACKEND", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/koru-bus")
    unavailable = ProviderAvailability(available=False, reason="mocked in test")
    with mock.patch(
        "koruvision.providers.portal_screencast.PortalScreenCastProvider.availability",
        return_value=unavailable,
    ):
        with mock.patch(
            "koruvision.capture_mss._grab_single_mss_raw",
            side_effect=RuntimeError("black frames"),
        ):
            with mock.patch(
                "koruvision.portal_capture.capture_portal_png",
                return_value=_png(9, 4),
            ):
                frame = capture_monitor_png(None)
    assert frame.output == "portal"
    assert frame.width == 9
    assert frame.height == 4
    assert "used portal capture" in capsys.readouterr().err


def test_capture_monitor_png_auto_uses_native_command_when_mss_fails(monkeypatch) -> None:
    monkeypatch.delenv("KORU_VISION_BACKEND", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    monkeypatch.setattr(
        "koruvision.capture_mss.command_candidates",
        lambda: [("grim", ["grim", "-"], True)],
    )
    monkeypatch.setattr("koruvision.capture_mss.shutil.which", lambda binary: f"/usr/bin/{binary}")
    monkeypatch.setattr(
        "koruvision.capture_mss.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=_png(11, 6), stderr=b""),
    )
    with mock.patch(
        "koruvision.capture_mss._grab_single_mss_raw",
        side_effect=RuntimeError("display unavailable"),
    ):
        frame = capture_monitor_png(None)
    assert frame.output == "grim"
    assert frame.width == 11
    assert frame.height == 6


def test_capture_all_monitors_auto_falls_back_to_portal(monkeypatch) -> None:
    from koruvision.providers.base import ProviderAvailability

    monkeypatch.delenv("KORU_VISION_BACKEND", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/koru-bus")
    unavailable = ProviderAvailability(available=False, reason="mocked in test")
    with mock.patch(
        "koruvision.providers.portal_screencast.PortalScreenCastProvider.availability",
        return_value=unavailable,
    ):
        with mock.patch(
            "koruvision.capture_mss._grab_all_mss_raw",
            side_effect=RuntimeError("all monitors returned black frames"),
        ):
            with mock.patch(
                "koruvision.portal_capture.capture_portal_png",
                return_value=_png(5, 3),
            ):
                frames = capture_all_monitors()
    assert len(frames) == 1
    assert frames[0].output == "portal"
    assert frames[0].width == 5


def test_capture_monitor_png_reports_headless_environment(monkeypatch) -> None:
    monkeypatch.delenv("KORU_VISION_BACKEND", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setattr("koruvision.capture_mss.command_candidates", lambda: [])
    with mock.patch(
        "koruvision.capture_mss._grab_single_mss_raw",
        side_effect=RuntimeError("display unavailable"),
    ):
        with pytest.raises(RuntimeError, match="looks headless"):
            capture_monitor_png(None)
