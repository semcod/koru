"""Monitor capture with mss → portal → native-command fallbacks.

The agent captures every detected monitor at ~20% native resolution
(``KORU_VISION_SCALE``) so the grid stays fast even with multi-display
setups. When ``mss`` fails (e.g. Wayland returns black frames) the
``capture_mss`` helpers fall back to ``org.freedesktop.portal.Screenshot``
or to a native screenshot binary (``grim``/``gnome-screenshot``/...).
"""

from __future__ import annotations

import hashlib
import shutil  # noqa: F401 — re-exported for monkeypatching from tests
import subprocess  # noqa: F401 — re-exported for monkeypatching from tests
from dataclasses import dataclass
from typing import Any

from koruvision.capture_mss import (
    BlackFrameError,
    capture_backend,
    command_capture_dict as _command_capture_dict,
    grab_all_mss,
    grab_single_mss,
    portal_capture_dict,
)
from koruvision.scaling import resolve_scale

# Test-visible aliases — tests monkeypatch these directly.
_capture_via_mss_single = grab_single_mss
_capture_all_via_mss = grab_all_mss


@dataclass(frozen=True)
class VisionFrame:
    frame_id: str
    monitor_id: int
    captured_at: str
    mime: str
    width: int
    height: int
    payload: bytes
    native_width: int = 0
    native_height: int = 0
    output: str = ""

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


def _frame(descriptor: dict[str, Any]) -> VisionFrame:
    return VisionFrame(**descriptor)


def _command_candidates() -> list[tuple[str, list[str], bool]]:
    """Pass-through for the native screenshot commands (kept for monkeypatching)."""
    from koruvision.capture_mss import command_candidates

    return command_candidates()


def list_monitors() -> list[dict[str, Any]]:
    """Return all attached monitors (excluding the union "virtual screen")."""
    import mss

    with mss.mss() as grabber:
        return [dict(monitor) for monitor in grabber.monitors[1:]]


def capture_monitor_png(monitor_id: int | None = None, scale: float | None = None) -> VisionFrame:
    """Capture a single monitor; falls back to portal/native CLI when ``mss`` fails."""
    scale_value = resolve_scale(scale)
    backend = capture_backend()
    if backend == "portal":
        return _frame(portal_capture_dict())
    if backend in {"command", "native", "desktop"}:
        return _frame(_command_capture_dict())
    return _frame(_capture_via_mss_single(monitor_id, scale_value))


def capture_all_monitors(scale: float | None = None) -> list[VisionFrame]:
    """Capture every detected monitor; black/failed monitors are skipped."""
    scale_value = resolve_scale(scale)
    backend = capture_backend()
    if backend == "portal":
        return [_frame(portal_capture_dict())]
    if backend in {"command", "native", "desktop"}:
        return [_frame(_command_capture_dict())]
    return [_frame(item) for item in _capture_all_via_mss(scale_value)]


__all__ = [
    "BlackFrameError",
    "VisionFrame",
    "capture_all_monitors",
    "capture_monitor_png",
    "list_monitors",
]
