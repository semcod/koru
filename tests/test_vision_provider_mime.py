from __future__ import annotations

import struct

from korumesh.dashboard_parse import envelope_to_frame_entry
from korumesh.envelope import sign_envelope
from koruvision.capture import VisionFrame
from koruvision.mesh import vision_frame_envelope
from koruvision.providers.base import frame_from_png
from koruvision.providers.detector import capture_one_with_providers


def _png(width: int = 4, height: int = 3) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def test_frame_from_png_includes_provider() -> None:
    descriptor = frame_from_png(
        _png(8, 6),
        monitor_id=1,
        scale=1.0,
        output="DP-2",
        provider="grim",
    )
    assert descriptor["provider"] == "grim"


def test_capture_one_stamps_provider_from_winning_backend(monkeypatch) -> None:
    class _FakeProvider:
        name = "fake_provider"
        streams = False

        def availability(self):
            from koruvision.providers.base import ProviderAvailability

            return ProviderAvailability(available=True)

        def list_monitors(self):
            return []

        def capture_all(self, scale):
            del scale
            return []

        def capture_one(self, monitor_id, scale):
            del monitor_id, scale
            return frame_from_png(
                _png(2, 2),
                monitor_id=0,
                scale=1.0,
                output="",
                provider="ignored",
            )

    monkeypatch.setattr(
        "koruvision.providers.detector.rank_providers",
        lambda: [_FakeProvider()],
    )
    frame = capture_one_with_providers(0, 1.0)
    assert frame["provider"] == "fake_provider"  # winning backend overrides frame dict


def test_envelope_roundtrip_preserves_provider() -> None:
    key = b"vision-mesh-key-32-bytes-long!!"
    frame = VisionFrame(
        frame_id="abc",
        monitor_id=2,
        captured_at="2026-01-01T00:00:00+00:00",
        mime="image/png",
        width=2,
        height=2,
        payload=_png(2, 2),
        provider="portal_screencast",
    )
    envelope = vision_frame_envelope(frame, peer_from="host-a", key=key)
    entry = envelope_to_frame_entry(envelope)
    assert entry["provider"] == "portal_screencast"
    assert entry["monitor"] == 2
