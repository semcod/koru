"""Monitor capture via ranked capture providers.

The agent captures every detected monitor at ~20% native resolution
(``KORU_VISION_SCALE``) so the grid stays fast even with multi-display
setups. Provider order is chosen by :mod:`koruvision.providers.detector`
(Wayland: ScreenCast → mss → CLI tools → portal screenshot, etc.).
"""

from __future__ import annotations

import hashlib
import shutil  # noqa: F401 — re-exported for monkeypatching from tests
import subprocess  # noqa: F401 — re-exported for monkeypatching from tests
from dataclasses import dataclass
from typing import Any

from koruvision.capture_mss import BlackFrameError
from koruvision.providers.detector import capture_all_with_providers, capture_one_with_providers
from koruvision.scaling import resolve_scale


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
    provider: str = ""

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


def _frame(descriptor: dict[str, Any]) -> VisionFrame:
    return VisionFrame(**descriptor)


def list_monitors() -> list[dict[str, Any]]:
    """Return all attached monitors (excluding the union "virtual screen")."""
    import mss

    with mss.mss() as grabber:
        return [dict(monitor) for monitor in grabber.monitors[1:]]


def capture_monitor_png(monitor_id: int | None = None, scale: float | None = None) -> VisionFrame:
    """Capture a single monitor using the best available provider."""
    return _frame(capture_one_with_providers(monitor_id, resolve_scale(scale)))


def capture_all_monitors(scale: float | None = None) -> list[VisionFrame]:
    """Capture every detected monitor; black/failed monitors are skipped."""
    return [_frame(item) for item in capture_all_with_providers(resolve_scale(scale))]


__all__ = [
    "BlackFrameError",
    "VisionFrame",
    "capture_all_monitors",
    "capture_monitor_png",
    "list_monitors",
]
