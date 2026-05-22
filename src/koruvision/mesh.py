"""Publish vision frames to a Koru mesh relay.

Per-monitor envelopes use a stable ``envelope_id`` (``{peer}:vision:{monitor}``)
so the relay store keeps the latest frame for every (peer, monitor) pair
instead of accumulating duplicates.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

from koru.configurator import load_project_config
from koruvision.capture import VisionFrame
from korumesh.keys import load_mesh_key
from korumesh.envelope import sign_envelope
from korumesh.transport import publish_envelope


def default_peer_id() -> str:
    return socket.gethostname()


def resolve_mesh_publish(
    project: Path,
    *,
    mesh_url: str | None,
    peer_id: str | None,
    key_file: Path | None,
) -> tuple[str, str, bytes]:
    saved = load_project_config(project)
    mesh = saved.get("mesh") if isinstance(saved.get("mesh"), dict) else {}
    url = mesh_url or str(mesh.get("relay_url") or "ws://127.0.0.1:9876")
    peer = peer_id or str(mesh.get("peer_id") or default_peer_id())
    key_path = key_file or (project / str(mesh.get("psk_path") or ".koru/keys/mesh.hmac"))
    return url, peer, load_mesh_key(key_path)


def _vision_mime(frame: VisionFrame) -> str:
    native_w = frame.native_width or frame.width
    native_h = frame.native_height or frame.height
    parts = [
        "image/png",
        f"monitor={frame.monitor_id}",
        f"w={frame.width}",
        f"h={frame.height}",
        f"nw={native_w}",
        f"nh={native_h}",
    ]
    if frame.output:
        parts.append(f"output={frame.output}")
    if frame.provider:
        parts.append(f"provider={frame.provider}")
    return "; ".join(parts)


def vision_frame_envelope(frame: VisionFrame, *, peer_from: str, key: bytes):
    envelope_id = f"{peer_from}:vision:{frame.monitor_id}"
    return sign_envelope(
        peer_from=peer_from,
        peer_to="*",
        topic="vision/frame",
        mime=_vision_mime(frame),
        payload=frame.payload,
        key=key,
        envelope_id=envelope_id,
    )


def publish_vision_frame(
    frame: VisionFrame,
    *,
    mesh_url: str,
    peer_from: str,
    key: bytes,
) -> None:
    envelope = vision_frame_envelope(frame, peer_from=peer_from, key=key)
    asyncio.run(publish_envelope(mesh_url, envelope, recv_timeout=0.2))
