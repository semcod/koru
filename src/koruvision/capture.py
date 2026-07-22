"""Monitor capture via ranked capture providers.

The agent captures every detected monitor at ~20% native resolution
(``KORU_VISION_SCALE``) so the grid stays fast even with multi-display
setups. Provider order is chosen by :mod:`koruvision.providers.detector`
(Wayland: ScreenCast → mss → CLI tools → portal screenshot, etc.).
"""

from __future__ import annotations

import shutil  # noqa: F401 — re-exported for monkeypatching from tests
import subprocess  # noqa: F401 — re-exported for monkeypatching from tests
from typing import Any

from vdisplay.capture import BlackFrameError, ScreenObservation, resolve_capture_scale

from koruvision.providers.detector import capture_all_with_providers, capture_one_with_providers

# Compatibility name retained for Koru callers.  The data contract and its
# canonical hashing now live at the capture boundary owned by VDisplay.
VisionFrame = ScreenObservation


def list_monitors() -> list[dict[str, Any]]:
    """Return all attached monitors (excluding the union "virtual screen")."""
    import mss

    with mss.mss() as grabber:
        return [dict(monitor) for monitor in grabber.monitors[1:]]


def capture_monitor_png(monitor_id: int | None = None, scale: float | None = None) -> VisionFrame:
    """Capture a single monitor using the best available provider."""
    resolved_scale = resolve_capture_scale(scale, env_var="KORU_VISION_SCALE")
    return capture_one_with_providers(monitor_id, resolved_scale)


def capture_all_monitors(scale: float | None = None) -> list[VisionFrame]:
    """Capture every detected monitor; black/failed monitors are skipped."""
    resolved_scale = resolve_capture_scale(scale, env_var="KORU_VISION_SCALE")
    return capture_all_with_providers(resolved_scale)


__all__ = [
    "BlackFrameError",
    "VisionFrame",
    "capture_all_monitors",
    "capture_monitor_png",
    "list_monitors",
]
