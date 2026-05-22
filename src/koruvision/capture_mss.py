"""Internal mss/portal capture primitives used by :mod:`koruvision.capture`."""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import UTC, datetime
from typing import Any

from koruvision.scaling import downscale_rgb_nearest, rgb_mostly_black


class BlackFrameError(RuntimeError):
    """Captured buffer is empty/black (common with XWayland + ``mss``)."""


def capture_backend() -> str:
    """Return the active capture backend (``auto``/``mss``/``portal``)."""
    return os.environ.get("KORU_VISION_BACKEND", "auto").strip().lower() or "auto"


def is_wayland() -> bool:
    """True when the active session is Wayland (controls portal fallback)."""
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def frame_from_shot(shot: Any, *, monitor_id: int, scale: float, output: str = "") -> dict[str, Any]:
    """Encode an mss shot as a PNG payload + descriptor dict for :class:`VisionFrame`."""
    import mss.tools

    if rgb_mostly_black(shot.rgb):
        raise BlackFrameError("monitor image is mostly black")
    src_w, src_h = shot.size
    dst_w = max(1, int(src_w * scale))
    dst_h = max(1, int(src_h * scale))
    rgb = downscale_rgb_nearest(shot.rgb, src_w, src_h, dst_w, dst_h)
    payload = mss.tools.to_png(rgb, (dst_w, dst_h))
    return {
        "frame_id": hashlib.sha256(payload).hexdigest()[:16],
        "monitor_id": monitor_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "mime": "image/png",
        "width": dst_w,
        "height": dst_h,
        "payload": payload,
        "native_width": src_w,
        "native_height": src_h,
        "output": output,
    }


def ordered_monitor_indices(targets: list[dict[str, Any]]) -> list[int]:
    """Return indices with the ``is_primary`` monitor(s) first."""
    primary = [index for index, monitor in enumerate(targets) if monitor.get("is_primary")]
    rest = [index for index in range(len(targets)) if index not in primary]
    return primary + rest


def portal_capture_dict() -> dict[str, Any]:
    """Capture via ``org.freedesktop.portal.Screenshot`` returning a VisionFrame descriptor."""
    from koruvision.portal_capture import PortalCaptureError, capture_portal_png

    try:
        payload = capture_portal_png()
    except PortalCaptureError as exc:
        raise RuntimeError(str(exc)) from exc
    return {
        "frame_id": hashlib.sha256(payload).hexdigest()[:16],
        "monitor_id": -1,
        "captured_at": datetime.now(UTC).isoformat(),
        "mime": "image/png",
        "width": 0,
        "height": 0,
        "payload": payload,
        "native_width": 0,
        "native_height": 0,
        "output": "portal",
    }


def grab_target(grabber: Any, target: dict[str, Any], index: int, scale: float) -> dict[str, Any]:
    """Grab a single monitor through *grabber* and turn it into a VisionFrame descriptor."""
    return frame_from_shot(
        grabber.grab(target),
        monitor_id=index,
        scale=scale,
        output=str(target.get("output") or ""),
    )


def grab_single_mss(monitor_id: int | None, scale: float) -> dict[str, Any]:
    """Pick one monitor (explicit index or first non-black) via mss."""
    import mss

    with mss.MSS() as grabber:
        targets = [dict(monitor) for monitor in grabber.monitors[1:]]
        if not targets:
            raise RuntimeError("no monitors detected")
        if monitor_id is not None:
            index = max(0, min(monitor_id, len(targets) - 1))
            return grab_target(grabber, targets[index], index, scale)
        last_error: Exception | None = None
        for index in ordered_monitor_indices(targets):
            try:
                return grab_target(grabber, targets[index], index, scale)
            except BlackFrameError as exc:
                last_error = exc
        msg = f"mss capture produced only black frames ({last_error})"
        raise RuntimeError(msg) from last_error


def grab_all_mss(scale: float) -> list[dict[str, Any]]:
    """Capture every monitor mss reports; log+skip blacks/errors."""
    import mss

    frames: list[dict[str, Any]] = []
    with mss.MSS() as grabber:
        targets = [dict(monitor) for monitor in grabber.monitors[1:]]
        for index, target in enumerate(targets):
            try:
                frames.append(grab_target(grabber, target, index, scale))
            except BlackFrameError:
                continue
            except Exception as exc:  # noqa: BLE001 — surface in stderr, keep going
                print(
                    f"koru vision: monitor {index} capture failed: {exc}",
                    file=sys.stderr,
                )
    return frames
