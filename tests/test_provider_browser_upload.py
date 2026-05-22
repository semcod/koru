"""Tests for browser getDisplayMedia upload and provider."""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from unittest import mock

import pytest

from koruvision.providers.browser_getdisplay import (
    BrowserGetDisplayProvider,
    ingest_browser_upload,
)


def _png(width: int = 12, height: int = 8) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def test_ingest_browser_upload_stores_frame_with_provider(tmp_path: Path) -> None:
    from korumesh.store import clear_vision_frames, list_vision_frames

    clear_vision_frames()
    key_path = tmp_path / ".koru" / "keys" / "mesh.hmac"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"k" * 32)

    body = {
        "peer": "browser-peer",
        "monitor_id": 1,
        "output": "display-1",
        "image_b64": base64.b64encode(_png(12, 8)).decode("ascii"),
    }
    with mock.patch("koruvision.mesh.publish_vision_frame"):
        result = ingest_browser_upload(tmp_path, body, publish_mesh=False)

    assert result["ok"] is True
    assert result["provider"] == "browser_getdisplay"
    frames = list_vision_frames()
    assert len(frames) == 1
    assert "provider=browser_getdisplay" in frames[0].mime
    assert frames[0].peer_from == "browser-peer"
    clear_vision_frames()


def test_ingest_rejects_non_png(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PNG"):
        ingest_browser_upload(
            tmp_path,
            {"image_b64": base64.b64encode(b"not-png").decode("ascii")},
            publish_mesh=False,
        )


def test_browser_provider_reads_from_store(tmp_path: Path) -> None:
    from korumesh.envelope import sign_envelope
    from korumesh.store import clear_vision_frames, remember_envelope

    clear_vision_frames()
    key = b"browser-test-key-32-bytes!!!!"
    remember_envelope(
        sign_envelope(
            peer_from="host",
            peer_to="*",
            topic="vision/frame",
            mime=(
                "image/png; monitor=0; w=12; h=8; nw=12; nh=8; "
                "provider=browser_getdisplay; output=browser"
            ),
            payload=_png(12, 8),
            key=key,
        )
    )
    provider = BrowserGetDisplayProvider()
    frames = provider.capture_all(scale=1.0)
    assert len(frames) == 1
    assert frames[0]["output"] == "browser"
    clear_vision_frames()


def _serve_project(tmp_path: Path):
    from tests.test_serve import _free_port, _get, _post_json, _start

    (tmp_path / ".planfile" / "sprints").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".planfile" / "config.yaml").write_text("project: test\n", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  id: current\n  tickets: {}\n",
        encoding="utf-8",
    )
    port = _free_port()
    server = _start(tmp_path, port)
    return server, port, _get, _post_json


def test_capture_host_route_served(tmp_path: Path) -> None:
    server, port, get, _post = _serve_project(tmp_path)
    try:
        status, ctype, html = get(port, "/capture/host?peer=test-peer")
        assert status == 200
        assert "text/html" in ctype
        assert "getDisplayMedia" in html
        assert "test-peer" in html
        assert "/api/mesh/browser-upload" in html
    finally:
        server.shutdown()
        server.server_close()


def test_browser_upload_post(tmp_path: Path) -> None:
    from korumesh.store import clear_vision_frames, list_vision_frames

    clear_vision_frames()
    (tmp_path / ".koru" / "keys").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".koru" / "keys" / "mesh.hmac").write_bytes(b"z" * 32)

    server, port, _get, post_json = _serve_project(tmp_path)
    try:
        status, _ctype, text = post_json(
            port,
            "/api/mesh/browser-upload",
            {
                "peer": "post-peer",
                "monitor_id": 0,
                "image_b64": base64.b64encode(_png()).decode("ascii"),
            },
        )
        assert status == 200
        data = json.loads(text)
        assert data["ok"] is True
        assert data["peer_from"] == "post-peer"
        frames = list_vision_frames()
        assert len(frames) == 1
        assert "provider=browser_getdisplay" in frames[0].mime
    finally:
        server.shutdown()
        server.server_close()
        clear_vision_frames()
