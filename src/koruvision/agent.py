"""Periodic monitor capture for koruvision."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable

from koruvision.capture import (
    VisionFrame,
    capture_all_monitors,
    capture_monitor_png,
)

MIN_CAPTURE_INTERVAL_SECONDS = 30.0


def capture_once(monitor_id: int | None = 0, scale: float | None = None) -> VisionFrame:
    """Capture a single monitor (default: primary)."""
    return capture_monitor_png(monitor_id, scale=scale)


def capture_all_once(scale: float | None = None) -> list[VisionFrame]:
    """Capture every detected monitor in this cycle."""
    return capture_all_monitors(scale=scale)


def _capture_cycle(monitor_id: int | None, scale: float | None) -> list[VisionFrame]:
    """Branch between single-monitor and multi-monitor capture per cycle."""
    if monitor_id is None:
        return capture_all_once(scale=scale)
    return [capture_once(monitor_id, scale=scale)]


def normalize_capture_interval(interval_seconds: float) -> float:
    """Return an interval that never captures screenshots more often than every 30s."""
    if interval_seconds <= 0:
        msg = "interval_seconds must be positive"
        raise ValueError(msg)
    return max(MIN_CAPTURE_INTERVAL_SECONDS, interval_seconds)


def run_capture_loop(
    *,
    interval_seconds: float,
    monitor_id: int | None = 0,
    on_frame: Callable[[VisionFrame], None] | None = None,
    max_frames: int | None = None,
    scale: float | None = None,
) -> int:
    """Capture monitor(s) every *interval_seconds* until interrupted or *max_frames*.

    When ``monitor_id`` is ``None`` every detected monitor is captured per cycle.
    ``max_frames`` bounds the total number of frames published, not cycles.
    """
    interval_seconds = normalize_capture_interval(interval_seconds)
    count = 0
    while max_frames is None or count < max_frames:
        try:
            frames = _capture_cycle(monitor_id, scale)
        except Exception as exc:  # noqa: BLE001 — mss/X11/portal backends vary.
            print(f"koru vision agent: capture failed: {exc}", file=sys.stderr)
            frames = []
        for frame in frames:
            if on_frame is not None:
                try:
                    on_frame(frame)
                except Exception as exc:  # noqa: BLE001 — mesh publish may fail independently.
                    print(f"koru vision agent: publish failed: {exc}", file=sys.stderr)
            count += 1
            if max_frames is not None and count >= max_frames:
                break
        if max_frames is not None and count >= max_frames:
            break
        time.sleep(interval_seconds)
    return count
