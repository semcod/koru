"""In-memory store of recent mesh frames (vision relay hub)."""

from __future__ import annotations

from collections import deque

from korumesh.envelope import Envelope

_MAX_FRAMES = 64
_order: deque[str] = deque(maxlen=_MAX_FRAMES)
_frames: dict[str, Envelope] = {}


def remember_envelope(envelope: Envelope) -> None:
    if envelope.topic != "vision/frame":
        return
    _frames[envelope.envelope_id] = envelope
    if envelope.envelope_id in _order:
        _order.remove(envelope.envelope_id)
    _order.append(envelope.envelope_id)
    while len(_order) > _MAX_FRAMES:
        stale = _order.popleft()
        _frames.pop(stale, None)


def list_vision_frames() -> list[Envelope]:
    return [_frames[frame_id] for frame_id in _order if frame_id in _frames]


def clear_vision_frames() -> None:
    _order.clear()
    _frames.clear()
