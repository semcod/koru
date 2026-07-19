from __future__ import annotations

import struct

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


def test_screencast_frames_use_vdisplay_session(monkeypatch) -> None:
    from koruvision.providers import portal_screencast as mod

    class FakeSession:
        node_ids = [41, 42]
        stream_targets = ["DP-1", "DP-2"]
        streams = []

        def capture_png(self, *, node_index: int = 0) -> bytes:
            return _png(4 + node_index, 3)

    monkeypatch.setattr(mod, "_active_or_new_session", lambda: FakeSession())

    frames = mod._screencast_frames(0.5)
    assert [item["output"] for item in frames] == ["DP-1", "DP-2"]
    assert frames[1]["capture_meta"] == {
        "session": "vdisplay",
        "stream_index": 1,
        "node_id": 42,
    }


def test_rank_providers_forces_screencast(monkeypatch) -> None:
    monkeypatch.setenv("KORU_VISION_PROVIDER", "portal_screencast")
    from koruvision.providers.detector import rank_providers

    ranked = rank_providers()
    assert len(ranked) == 1
    assert ranked[0].name == "portal_screencast"
