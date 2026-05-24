"""Browser ``getDisplayMedia`` capture — frames uploaded via dashboard HTTP."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png
from koruvision.providers.env import capture_provider_pref, env_truthy

_PROVIDER_NAME = "browser_getdisplay"
_MAX_STORED = 16


def browser_capture_requested() -> bool:
    pref = capture_provider_pref()
    return pref in {_PROVIDER_NAME, "browser"} or env_truthy("KORU_VISION_BROWSER")


def browser_capture_interval_seconds() -> int:
    raw = os.environ.get("KORU_VISION_BROWSER_INTERVAL", "").strip()
    if not raw:
        raw = os.environ.get("KORU_VISION_INTERVAL", "30").strip()
    try:
        return max(5, int(raw))
    except ValueError:
        return 30


def _vision_mime_with_provider(frame: dict[str, Any]) -> str:
    native_w = int(frame.get("native_width") or frame.get("width") or 0)
    native_h = int(frame.get("native_height") or frame.get("height") or 0)
    parts = [
        "image/png",
        f"monitor={frame['monitor_id']}",
        f"w={frame['width']}",
        f"h={frame['height']}",
        f"nw={native_w}",
        f"nh={native_h}",
        f"provider={_PROVIDER_NAME}",
    ]
    output = str(frame.get("output") or "").strip()
    if output:
        parts.append(f"output={output}")
    return "; ".join(parts)


def _frames_from_store() -> list[dict[str, Any]]:
    from korumesh.dashboard_parse import parse_mime_params
    from korumesh.store import list_vision_frames

    rows: list[dict[str, Any]] = []
    for envelope in list_vision_frames():
        _base, params = parse_mime_params(envelope.mime)
        if params.get("provider") != _PROVIDER_NAME:
            continue
        monitor_id = int(params.get("monitor", "0") or 0)
        rows.append(
            frame_from_png(
                envelope.payload,
                monitor_id=monitor_id,
                scale=1.0,
                output=params.get("output", "browser"),
                provider=_PROVIDER_NAME,
            )
        )
    return rows[-_MAX_STORED:]


def _decode_browser_png_upload(body: dict[str, Any]) -> bytes:
    image_b64 = body.get("image_b64") or body.get("payload_b64") or ""
    if not isinstance(image_b64, str) or not image_b64.strip():
        raise ValueError("image_b64 is required")
    try:
        payload = base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ValueError("image_b64 is not valid base64") from exc
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("upload must be a PNG image")
    return payload


def _browser_upload_monitor_id(body: dict[str, Any]) -> int:
    monitor_raw = body.get("monitor_id", body.get("monitor", 0))
    try:
        return int(monitor_raw)
    except (TypeError, ValueError):
        return 0


def _mesh_key_for_browser_upload(project: Path) -> bytes:
    from korumesh.keys import load_mesh_key

    key_path = project / ".koru" / "keys" / "mesh.hmac"
    if not key_path.is_file():
        from koruobserve.bootstrap import ensure_mesh_key

        ensure_mesh_key(project)
    return load_mesh_key(key_path)


def _remember_browser_upload_envelope(
    *,
    project: Path,
    peer: str,
    frame_dict: dict[str, Any],
) -> None:
    from korumesh.envelope import sign_envelope
    from korumesh.store import remember_envelope

    envelope = sign_envelope(
        peer_from=peer,
        peer_to="*",
        topic="vision/frame",
        mime=_vision_mime_with_provider(frame_dict),
        payload=frame_dict["payload"],
        key=_mesh_key_for_browser_upload(project),
        envelope_id=f"{peer}:vision:{frame_dict['monitor_id']}",
    )
    remember_envelope(envelope)


def _publish_browser_upload_if_requested(
    *,
    project: Path,
    peer: str,
    frame_dict: dict[str, Any],
    publish_mesh: bool,
) -> bool:
    if not publish_mesh:
        return False
    try:
        from koruvision.capture import VisionFrame
        from koruvision.mesh import publish_vision_frame, resolve_mesh_publish

        mesh_url, mesh_peer, mesh_key = resolve_mesh_publish(project)
        publish_vision_frame(
            VisionFrame(**frame_dict),
            mesh_url=mesh_url,
            peer_from=peer or mesh_peer,
            key=mesh_key,
        )
        return True
    except Exception:
        return False


def ingest_browser_upload(
    project: Path,
    body: dict[str, Any],
    *,
    publish_mesh: bool = True,
) -> dict[str, Any]:
    """Validate a browser PNG upload, persist to the mesh store, optionally publish."""
    payload = _decode_browser_png_upload(body)
    monitor_id = _browser_upload_monitor_id(body)
    output = str(body.get("output") or "browser").strip() or "browser"
    peer = str(body.get("peer") or body.get("peer_from") or "").strip()
    scale = float(body.get("scale", 1.0) or 1.0)

    frame_dict = frame_from_png(
        payload,
        monitor_id=monitor_id,
        scale=scale,
        output=output,
        provider=_PROVIDER_NAME,
    )

    from koruvision.mesh import default_peer_id

    if not peer:
        peer = default_peer_id()

    _remember_browser_upload_envelope(
        project=project,
        peer=peer,
        frame_dict=frame_dict,
    )
    published = _publish_browser_upload_if_requested(
        project=project,
        peer=peer,
        frame_dict=frame_dict,
        publish_mesh=publish_mesh,
    )

    return {
        "ok": True,
        "peer_from": peer,
        "monitor_id": frame_dict["monitor_id"],
        "frame_id": frame_dict["frame_id"],
        "published": published,
        "provider": _PROVIDER_NAME,
    }


class BrowserGetDisplayProvider:
    name = _PROVIDER_NAME
    streams = True

    def availability(self) -> ProviderAvailability:
        stored = _frames_from_store()
        if stored:
            return ProviderAvailability(
                available=True,
                reason=f"{len(stored)} browser frame(s) in mesh store",
                install_hint="Open /capture/host to share your screen from a browser",
            )
        return ProviderAvailability(
            available=True,
            reason="waiting for browser upload",
            install_hint="Open /capture/host in Chrome or Firefox and click Share screen",
            needs_consent=True,
        )

    def list_monitors(self) -> list[MonitorSpec]:
        frames = _frames_from_store()
        if not frames:
            return [
                MonitorSpec(
                    id=0,
                    output="browser",
                    width=1920,
                    height=1080,
                    is_primary=True,
                )
            ]
        return [
            MonitorSpec(
                id=int(item["monitor_id"]),
                output=str(item.get("output") or "browser"),
                width=int(item.get("native_width") or item.get("width") or 0),
                height=int(item.get("native_height") or item.get("height") or 0),
                is_primary=idx == 0,
            )
            for idx, item in enumerate(frames)
        ]

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        frames = _frames_from_store()
        if not frames:
            raise RuntimeError(
                f"{self.name}: no browser frames yet — open /capture/host and share your screen"
            )
        if scale == 1.0:
            return frames
        return [
            frame_from_png(
                item["payload"],
                monitor_id=int(item["monitor_id"]),
                scale=scale,
                output=str(item.get("output") or "browser"),
                provider=self.name,
            )
            for item in frames
        ]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        frames = self.capture_all(scale)
        if monitor_id is None:
            return frames[0]
        for frame in frames:
            if frame["monitor_id"] == monitor_id:
                return frame
        return frames[min(max(monitor_id, 0), len(frames) - 1)]
