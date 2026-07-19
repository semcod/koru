"""Thin Koru adapter for VDisplay's persistent portal ScreenCast session."""

from __future__ import annotations

import shutil
from typing import Any

from vdisplay.capture import (
    get_active_screencast,
    portal_session_env_status,
    start_screencast_session,
)

from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png


def _stream_properties(session: Any, index: int) -> dict[str, Any]:
    streams = list(getattr(session, "streams", []) or [])
    if index >= len(streams) or not isinstance(streams[index], dict):
        return {}
    properties = streams[index].get("properties") or {}
    return dict(properties) if isinstance(properties, dict) else {}


def _stream_output(session: Any, index: int) -> str:
    targets = list(getattr(session, "stream_targets", []) or [])
    if index < len(targets) and str(targets[index]).strip():
        return str(targets[index]).strip()
    properties = _stream_properties(session, index)
    return str(properties.get("id") or f"monitor-{index}")


def _active_or_new_session() -> Any:
    session = get_active_screencast()
    if session is not None and bool(getattr(session, "is_ready", False)):
        return session
    return start_screencast_session(interactive=True, multiple=True)


def _screencast_frames(scale: float) -> list[dict[str, Any]]:
    """Capture every VDisplay portal stream with stable provenance."""
    del scale  # Koru's descriptor adapter applies the requested logical scale.
    session = _active_or_new_session()
    node_ids = list(getattr(session, "node_ids", []) or [])
    if not node_ids:
        raise RuntimeError("portal_screencast: VDisplay session has no PipeWire streams")

    frames: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, node_id in enumerate(node_ids):
        try:
            payload = session.capture_png(node_index=index)
        except Exception as exc:  # noqa: BLE001 - one failed monitor must not hide the others.
            errors.append(f"stream {index}: {exc}")
            continue
        frames.append(
            {
                "monitor_id": index,
                "output": _stream_output(session, index),
                "payload": payload,
                "capture_meta": {
                    "session": "vdisplay",
                    "stream_index": index,
                    "node_id": int(node_id),
                },
            }
        )
    if not frames:
        detail = "; ".join(errors) or "no frames"
        raise RuntimeError(f"portal_screencast: {detail}")
    return frames


class PortalScreenCastProvider:
    name = "portal_screencast"
    streams = True

    def availability(self) -> ProviderAvailability:
        ok, reason = portal_session_env_status()
        if not ok:
            return ProviderAvailability(available=False, reason=reason)
        if shutil.which("gst-launch-1.0") is None:
            return ProviderAvailability(
                available=False,
                reason="gst-launch-1.0 not found",
                install_hint="apt install gstreamer1.0-tools gstreamer1.0-pipewire",
            )
        session = get_active_screencast()
        ready = session is not None and bool(getattr(session, "is_ready", False))
        return ProviderAvailability(
            available=True,
            reason="active VDisplay ScreenCast session" if ready else "VDisplay portal ScreenCast",
            needs_consent=not ready,
            install_hint=(
                "persistent VDisplay session ready"
                if ready
                else "Accept screen sharing when Koru starts VDisplay ScreenCast"
            ),
        )

    def list_monitors(self) -> list[MonitorSpec]:
        from koruvision.providers.detector import monitors_via_xrandr

        return monitors_via_xrandr()

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in _screencast_frames(scale):
            descriptor = frame_from_png(
                item["payload"],
                monitor_id=int(item["monitor_id"]),
                scale=scale,
                output=str(item.get("output") or ""),
                provider=self.name,
                capture_meta=dict(item.get("capture_meta") or {}),
            )
            rows.append(descriptor)
        return rows

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        frames = self.capture_all(scale)
        if monitor_id is None:
            return frames[0]
        for frame in frames:
            if frame["monitor_id"] == monitor_id:
                return frame
        return frames[min(max(0, monitor_id), len(frames) - 1)]


__all__ = ["PortalScreenCastProvider"]
