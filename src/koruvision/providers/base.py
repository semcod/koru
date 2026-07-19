"""Shared types and frame helpers for capture providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from vdisplay.capture import ScreenObservation, png_dimensions, resolve_capture_scale


class BlackFrameError(RuntimeError):
    """Captured buffer is empty/black (common with XWayland + ``mss``)."""


@dataclass(frozen=True)
class ProviderAvailability:
    available: bool
    reason: str = ""
    install_hint: str = ""
    needs_consent: bool = False


@dataclass(frozen=True)
class MonitorSpec:
    id: int
    output: str
    width: int
    height: int
    left: int = 0
    top: int = 0
    is_primary: bool = False


@runtime_checkable
class CaptureProvider(Protocol):
    name: str
    streams: bool

    def availability(self) -> ProviderAvailability: ...

    def list_monitors(self) -> list[MonitorSpec]: ...

    def capture_all(self, scale: float) -> list[dict[str, Any]]: ...

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]: ...


def frame_from_png(
    payload: bytes,
    *,
    monitor_id: int,
    scale: float,
    output: str,
    provider: str,
    capture_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a VisionFrame descriptor dict from raw PNG bytes."""
    if not payload:
        raise RuntimeError(f"{provider}: empty image")
    native_w, native_h = png_dimensions(payload)
    if native_w <= 0 or native_h <= 0:
        raise RuntimeError(f"{provider}: invalid PNG dimensions")
    scale_value = resolve_capture_scale(scale, env_var="KORU_VISION_SCALE")
    thumb_w = max(1, int(native_w * scale_value))
    thumb_h = max(1, int(native_h * scale_value))
    return ScreenObservation.from_png(
        payload,
        monitor_id=monitor_id,
        captured_at=datetime.now(UTC).isoformat(),
        width=thumb_w,
        height=thumb_h,
        output=output or provider,
        provider=provider,
        capture_meta=capture_meta or {},
    ).to_descriptor()
