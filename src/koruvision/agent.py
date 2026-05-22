"""Periodic monitor capture for koruvision."""

from __future__ import annotations

import time
from collections.abc import Callable

from koruvision.capture import VisionFrame, capture_monitor_png


def capture_once(monitor_id: int = 0) -> VisionFrame:
    return capture_monitor_png(monitor_id)


def run_capture_loop(
    *,
    interval_seconds: float,
    monitor_id: int = 0,
    on_frame: Callable[[VisionFrame], None] | None = None,
    max_frames: int | None = None,
) -> int:
    """Capture monitors every *interval_seconds* until interrupted or *max_frames*."""
    if interval_seconds <= 0:
        msg = "interval_seconds must be positive"
        raise ValueError(msg)
    count = 0
    while max_frames is None or count < max_frames:
        frame = capture_once(monitor_id)
        if on_frame is not None:
            on_frame(frame)
        count += 1
        if max_frames is not None and count >= max_frames:
            break
        time.sleep(interval_seconds)
    return count
