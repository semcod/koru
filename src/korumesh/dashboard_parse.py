"""Mime parameter helpers for vision/frame envelopes used by the grid view."""

from __future__ import annotations

import base64

from korumesh.envelope import Envelope


def parse_mime_params(mime: str) -> tuple[str, dict[str, str]]:
    """Return ``(base_mime, params)`` from a mime string with ``;`` separators."""
    parts = [piece.strip() for piece in mime.split(";") if piece.strip()]
    if not parts:
        return mime, {}
    base = parts[0]
    params: dict[str, str] = {}
    for piece in parts[1:]:
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        params[key.strip()] = value.strip()
    return base, params


def _int_param(params: dict[str, str], name: str) -> int | None:
    raw = params.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def envelope_to_frame_entry(envelope: Envelope) -> dict[str, object]:
    """Convert a stored vision envelope into the JSON shape used by ``/api/mesh/frames``."""
    base_mime, params = parse_mime_params(envelope.mime)
    return {
        "envelope_id": envelope.envelope_id,
        "peer_from": envelope.peer_from,
        "created_at": envelope.created_at,
        "mime": base_mime,
        "image_b64": base64.b64encode(envelope.payload).decode("ascii"),
        "bytes": len(envelope.payload),
        "monitor": _int_param(params, "monitor"),
        "width": _int_param(params, "w"),
        "height": _int_param(params, "h"),
        "native_width": _int_param(params, "nw"),
        "native_height": _int_param(params, "nh"),
        "output": params.get("output", ""),
        "provider": params.get("provider", ""),
    }
