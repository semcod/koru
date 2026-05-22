"""Publish vision frames to a Koru mesh relay."""

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


def vision_frame_envelope(frame: VisionFrame, *, peer_from: str, key: bytes):
    return sign_envelope(
        peer_from=peer_from,
        peer_to="*",
        topic="vision/frame",
        mime=frame.mime,
        payload=frame.payload,
        key=key,
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
