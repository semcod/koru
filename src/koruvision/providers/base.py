"""Compatibility exports for the VDisplay-owned observation contract."""

from __future__ import annotations

from typing import Any

from vdisplay.capture import (
    BlackFrameError,
    MonitorSpec,
    ObservationProvider as CaptureProvider,
    ProviderAvailability,
    screen_observation_from_png,
)


def frame_from_png(
    payload: bytes,
    *,
    monitor_id: int,
    scale: float,
    output: str,
    provider: str,
    capture_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-release descriptor shim around VDisplay's typed factory."""
    return screen_observation_from_png(
        payload,
        monitor_id=monitor_id,
        scale=scale,
        output=output or provider,
        provider=provider,
        capture_meta=capture_meta or {},
    ).to_descriptor()
