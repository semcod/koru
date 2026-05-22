"""In-memory store of recent mesh frames (vision relay hub).

When ``KORU_MESH_FRAME_STORE`` points at a JSONL file, frames are also
appended there so separate processes (relay vs ``koru serve`` dashboard)
share the same grid data.
"""

from __future__ import annotations

from collections import deque

from korumesh.envelope import Envelope
from korumesh.store_persistence import (
    append_envelope,
    frame_store_path,
    load_recent_envelopes,
)

_MAX_FRAMES = 64
_order: deque[str] = deque(maxlen=_MAX_FRAMES)
_frames: dict[str, Envelope] = {}


def _remember_in_memory(envelope: Envelope) -> None:
    _frames[envelope.envelope_id] = envelope
    if envelope.envelope_id in _order:
        _order.remove(envelope.envelope_id)
    _order.append(envelope.envelope_id)
    while len(_order) > _MAX_FRAMES:
        stale = _order.popleft()
        _frames.pop(stale, None)


def remember_envelope(envelope: Envelope) -> None:
    """Persist a ``vision/frame`` envelope in memory and (optionally) on disk."""
    if envelope.topic != "vision/frame":
        return
    _remember_in_memory(envelope)
    path = frame_store_path()
    if path is not None:
        append_envelope(path, envelope)


def list_vision_frames() -> list[Envelope]:
    """Return recent vision frames (disk store takes precedence over memory)."""
    path = frame_store_path()
    if path is not None and path.is_file():
        on_disk = load_recent_envelopes(path, limit=_MAX_FRAMES)
        if on_disk:
            return on_disk
    return [_frames[frame_id] for frame_id in _order if frame_id in _frames]


def clear_vision_frames() -> None:
    """Drop all in-memory frames and remove the on-disk JSONL store, if any."""
    _order.clear()
    _frames.clear()
    path = frame_store_path()
    if path is not None:
        path.unlink(missing_ok=True)
