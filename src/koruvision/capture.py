"""Minimal monitor capture (``mss``) for koruvision."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class VisionFrame:
    frame_id: str
    monitor_id: int
    captured_at: str
    mime: str
    width: int
    height: int
    payload: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


def list_monitors() -> list[dict[str, Any]]:
    import mss

    with mss.MSS() as grabber:
        return [dict(monitor) for monitor in grabber.monitors[1:]]


def capture_monitor_png(monitor_id: int = 0) -> VisionFrame:
    import mss

    with mss.MSS() as grabber:
        targets = grabber.monitors[1:]
        if not targets:
            msg = "no monitors detected"
            raise RuntimeError(msg)
        index = max(0, min(monitor_id, len(targets) - 1))
        shot = grabber.grab(targets[index])
        payload = mss.tools.to_png(shot.rgb, shot.size)
        width, height = shot.size
    captured_at = datetime.now(UTC).isoformat()
    frame_id = hashlib.sha256(payload).hexdigest()[:16]
    return VisionFrame(
        frame_id=frame_id,
        monitor_id=index,
        captured_at=captured_at,
        mime="image/png",
        width=width,
        height=height,
        payload=payload,
    )
