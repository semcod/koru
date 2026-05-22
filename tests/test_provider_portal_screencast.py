from __future__ import annotations

import json
import struct
from pathlib import Path
from unittest import mock

from koruvision.providers.portal_screencast import PortalScreenCastProvider


def _png(width: int = 4, height: int = 3) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def test_portal_screencast_capture_all_mocked(monkeypatch) -> None:
    provider = PortalScreenCastProvider()
    payload = _png(8, 6)
    monkeypatch.setattr(
        "koruvision.providers.portal_screencast._screencast_frames",
        lambda scale: [
            {
                "monitor_id": 0,
                "output": "DP-1",
                "native_width": 8,
                "native_height": 6,
                "payload": payload,
            },
            {
                "monitor_id": 1,
                "output": "DP-2",
                "native_width": 8,
                "native_height": 6,
                "payload": payload,
            },
        ],
    )
    frames = provider.capture_all(0.5)
    assert len(frames) == 2
    assert frames[0]["monitor_id"] == 0
    assert frames[0]["output"] == "DP-1"
    assert frames[0]["width"] == 4
    assert frames[0]["height"] == 3
    assert frames[0]["provider"] == "portal_screencast"


def test_screencast_frames_retries_after_cache_clear(monkeypatch, tmp_path: Path) -> None:
    from koruvision.providers.screencast_session import session_file_for_project

    session = session_file_for_project(tmp_path)
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text('{"session_path": "/org/freedesktop/portal/desktop/session/stale"}\n')
    calls = {"n": 0}

    def fake_run(args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return type("P", (), {"returncode": 2, "stdout": "", "stderr": "reuse failed"})()
        import base64

        payload = [
            {
                "monitor_id": 0,
                "output": "DP-1",
                "native_width": 4,
                "native_height": 3,
                "payload_b64": base64.b64encode(_png(4, 3)).decode("ascii"),
            }
        ]
        return type("P", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})()

    monkeypatch.setenv("KORU_MESH_FRAME_STORE", str(tmp_path / ".koru" / "run" / "mesh.jsonl"))
    (tmp_path / ".koru" / "run").mkdir(parents=True, exist_ok=True)
    with mock.patch(
        "koruvision.providers.portal_screencast._run_screencast_subprocess",
        side_effect=fake_run,
    ):
        from koruvision.providers.portal_screencast import _screencast_frames

        frames = _screencast_frames(0.5)
    assert calls["n"] == 2
    assert len(frames) == 1


def test_rank_providers_forces_screencast(monkeypatch) -> None:
    monkeypatch.setenv("KORU_VISION_PROVIDER", "portal_screencast")
    from koruvision.providers.detector import rank_providers

    ranked = rank_providers()
    assert len(ranked) == 1
    assert ranked[0].name == "portal_screencast"
