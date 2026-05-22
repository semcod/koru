"""On-disk persistence helpers for the vision frame store (rotation + replay)."""

from __future__ import annotations

import os
from pathlib import Path

from korumesh.codec import envelope_from_wire, envelope_to_wire
from korumesh.envelope import Envelope

_MAX_STORE_BYTES = 50_000_000
_ROTATE_KEEP_LINES = 2048


def frame_store_path() -> Path | None:
    """Return ``$KORU_MESH_FRAME_STORE`` as a Path or ``None`` if unset."""
    raw = os.environ.get("KORU_MESH_FRAME_STORE", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def append_envelope(path: Path, envelope: Envelope) -> None:
    """Append *envelope* to the JSONL store and rotate when it grows past 50 MB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(envelope_to_wire(envelope) + "\n")
    try:
        if path.stat().st_size > _MAX_STORE_BYTES:
            rotate_store(path)
    except OSError:
        return


def rotate_store(path: Path) -> None:
    """Keep only the last ``_ROTATE_KEEP_LINES`` entries of *path*."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    tail = lines[-_ROTATE_KEEP_LINES:]
    body = "\n".join(tail) + ("\n" if tail else "")
    path.write_text(body, encoding="utf-8")


def load_recent_envelopes(path: Path, *, limit: int) -> list[Envelope]:
    """Return the most recent ``limit`` vision envelopes (latest per envelope_id)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[Envelope] = []
    seen: set[str] = set()
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            envelope = envelope_from_wire(stripped)
        except (TypeError, ValueError, KeyError):
            continue
        if envelope.topic != "vision/frame" or envelope.envelope_id in seen:
            continue
        seen.add(envelope.envelope_id)
        rows.append(envelope)
        if len(rows) >= limit:
            break
    return list(reversed(rows))
