"""Shared types and frame helpers for capture providers."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from koruvision.scaling import resolve_scale


class BlackFrameError(RuntimeError):
    """Captured buffer is empty/black (common with XWayland + ``mss``)."""


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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


def png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) >= 24 and payload.startswith(_PNG_SIGNATURE) and payload[12:16] == b"IHDR":
        width, height = struct.unpack(">II", payload[16:24])
        return int(width), int(height)
    return 0, 0


def frame_from_png(
    payload: bytes,
    *,
    monitor_id: int,
    scale: float,
    output: str,
    provider: str,
) -> dict[str, Any]:
    """Build a VisionFrame descriptor dict from raw PNG bytes."""
    if not payload:
        raise RuntimeError(f"{provider}: empty image")
    native_w, native_h = png_dimensions(payload)
    if native_w <= 0 or native_h <= 0:
        raise RuntimeError(f"{provider}: invalid PNG dimensions")
    scale_value = resolve_scale(scale)
    thumb_w = max(1, int(native_w * scale_value))
    thumb_h = max(1, int(native_h * scale_value))
    return {
        "frame_id": hashlib.sha256(payload).hexdigest()[:16],
        "monitor_id": monitor_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "mime": "image/png",
        "width": thumb_w,
        "height": thumb_h,
        "payload": payload,
        "native_width": native_w,
        "native_height": native_h,
        "output": output or provider,
        "provider": provider,
    }
