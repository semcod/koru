"""Monitor capture (``mss``) with optional Wayland portal fallback.

By default the agent captures every detected monitor at ~20% native
resolution (``KORU_VISION_SCALE``) so the grid is fast to render even with
multi-display setups.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from typing import Any

from koruvision.capture_mss import (
    BlackFrameError,
    capture_backend,
    grab_all_mss,
    grab_single_mss,
    is_wayland,
    portal_capture_dict,
)
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

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


def _frame(descriptor: dict[str, Any]) -> VisionFrame:
    return VisionFrame(**descriptor)


def _wayland_portal_fallback(mss_exc: Exception) -> VisionFrame:
    try:
        descriptor = portal_capture_dict()
    except RuntimeError as portal_exc:
        msg = (
            f"{mss_exc}; portal fallback failed: {portal_exc}. "
            "Try: export KORU_VISION_BACKEND=portal and grant Screenshot "
            "in Settings → Privacy."
        )
        raise RuntimeError(msg) from portal_exc
    print(
        "koru vision: mss returned black frames on Wayland — used portal capture",
        file=sys.stderr,
    )
    return _frame(descriptor)


def list_monitors() -> list[dict[str, Any]]:
    """Return all attached monitors (excluding the union "virtual screen")."""
    import mss

    with mss.MSS() as grabber:
        return [dict(monitor) for monitor in grabber.monitors[1:]]


def capture_monitor_png(monitor_id: int | None = None, scale: float | None = None) -> VisionFrame:
    """Capture a single monitor; falls back to portal on Wayland when ``mss`` fails."""
    scale_value = resolve_scale(scale)
    backend = capture_backend()
    if backend == "portal":
        return _frame(portal_capture_dict())
    if backend == "mss":
        return _frame(grab_single_mss(monitor_id, scale_value))
    try:
        return _frame(grab_single_mss(monitor_id, scale_value))
    except RuntimeError as mss_exc:
        if not is_wayland():
            raise
        return _wayland_portal_fallback(mss_exc)


def capture_all_monitors(scale: float | None = None) -> list[VisionFrame]:
    """Capture every detected monitor; black/failed monitors are skipped."""
    scale_value = resolve_scale(scale)
    backend = capture_backend()
    if backend == "portal":
        return [_frame(portal_capture_dict())]
    descriptors = grab_all_mss(scale_value)
    if descriptors:
        return [_frame(item) for item in descriptors]
    if is_wayland():
        try:
            return [_frame(portal_capture_dict())]
        except RuntimeError as exc:
            raise RuntimeError(
                f"all monitors returned black frames; portal fallback failed: {exc}"
            ) from exc
    raise RuntimeError("all monitors returned black frames")


__all__ = [
    "BlackFrameError",
    "VisionFrame",
    "capture_all_monitors",
    "capture_monitor_png",
    "list_monitors",
]
