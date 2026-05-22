from __future__ import annotations

from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock

from koruvision.capture import VisionFrame
from koruvision.mesh import publish_vision_frame, resolve_mesh_publish, vision_frame_envelope


def test_vision_frame_envelope_uses_vision_topic() -> None:
    key = b"vision-mesh-key-32-bytes-long!!"
    frame = VisionFrame(
        frame_id="abc",
        monitor_id=1,
        captured_at="2026-01-01T00:00:00+00:00",
        mime="image/png",
        width=2,
        height=2,
        payload=b"\x89PNG",
        native_width=10,
        native_height=10,
        output="DP-1",
        provider="portal_screencast",
    )
    envelope = vision_frame_envelope(frame, peer_from="host-a", key=key)
    assert envelope.topic == "vision/frame"
    assert envelope.mime.startswith("image/png")
    assert "monitor=1" in envelope.mime
    assert "nw=10" in envelope.mime
    assert "output=DP-1" in envelope.mime
    assert "provider=portal_screencast" in envelope.mime
    assert envelope.envelope_id == "host-a:vision:1"


def test_publish_vision_frame_calls_mesh_transport(tmp_path: Path) -> None:
    key_file = tmp_path / ".koru" / "keys" / "mesh.hmac"
    key_file.parent.mkdir(parents=True)
    key_file.write_bytes(b"publish-vision-key-32-bytes!!!")
    frame = VisionFrame(
        frame_id="abc",
        monitor_id=0,
        captured_at="t",
        mime="image/png",
        width=2,
        height=2,
        payload=b"\x89PNG",
    )
    with mock.patch("koruvision.mesh.publish_envelope", new_callable=AsyncMock) as publish:
        publish_vision_frame(
            frame,
            mesh_url="ws://127.0.0.1:9876",
            peer_from="host-a",
            key=b"publish-vision-key-32-bytes!!!",
        )
    publish.assert_called_once()


def test_resolve_mesh_publish_reads_project_defaults(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    key_file = project / ".koru" / "keys" / "mesh.hmac"
    key_file.parent.mkdir(parents=True)
    key_file.write_bytes(b"resolve-mesh-key-32-bytes-long!")
    (project / ".koru").mkdir(exist_ok=True)
    (project / ".koru" / "config.json").write_text(
        '{"mesh":{"relay_url":"ws://127.0.0.1:9999","psk_path":".koru/keys/mesh.hmac","peer_id":"worker-1"}}',
        encoding="utf-8",
    )
    url, peer, key = resolve_mesh_publish(project, mesh_url=None, peer_id=None, key_file=None)
    assert url == "ws://127.0.0.1:9999"
    assert peer == "worker-1"
    assert key == b"resolve-mesh-key-32-bytes-long!"
