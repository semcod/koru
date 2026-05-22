from __future__ import annotations

from korumesh.envelope import sign_envelope
from korumesh.store import clear_vision_frames, list_vision_frames, remember_envelope


def test_remember_envelope_keeps_vision_frames_only() -> None:
    clear_vision_frames()
    key = b"store-test-key-32-bytes-long!!!"
    vision = sign_envelope(
        peer_from="host-a",
        peer_to="*",
        topic="vision/frame",
        mime="image/png",
        payload=b"\x89PNG",
        key=key,
    )
    other = sign_envelope(
        peer_from="host-a",
        peer_to="*",
        topic="mesh/ping",
        mime="text/plain",
        payload=b"hi",
        key=key,
    )
    remember_envelope(vision)
    remember_envelope(other)
    frames = list_vision_frames()
    assert len(frames) == 1
    assert frames[0].topic == "vision/frame"
    clear_vision_frames()
