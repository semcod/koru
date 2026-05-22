from __future__ import annotations

from pathlib import Path

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


def test_frame_store_file_shared_across_processes(tmp_path: Path, monkeypatch) -> None:
    store_path = tmp_path / "mesh-frames.jsonl"
    monkeypatch.setenv("KORU_MESH_FRAME_STORE", str(store_path))
    clear_vision_frames()
    key = b"store-file-key-32-bytes-long!!!!"
    vision = sign_envelope(
        peer_from="host-b",
        peer_to="*",
        topic="vision/frame",
        mime="image/png",
        payload=b"\x89PNG",
        key=key,
    )
    remember_envelope(vision)
    # Dashboard runs in another process: in-memory store is empty, JSONL has frames.
    import korumesh.store as store_mod

    store_mod._order.clear()
    store_mod._frames.clear()
    frames = list_vision_frames()
    assert len(frames) == 1
    assert frames[0].peer_from == "host-b"
    clear_vision_frames()
