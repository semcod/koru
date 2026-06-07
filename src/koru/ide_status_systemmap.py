"""Export live autopilot status as nlp2uri SystemMap-compatible URI index."""

from __future__ import annotations

from typing import Any


def format_autopilot_status_systemmap(
    status: dict[str, Any],
    *,
    socket_path: str = "",
) -> dict[str, Any]:
    """Convert ``koru autopilot status`` payload to URI index entries."""
    try:
        from nlp2uri.systemmap.koru_ide import build_koru_ide_uri_index
    except ImportError as exc:
        return {
            "ok": False,
            "error": (
                "nlp2uri is not installed; install koru[desktop] or sibling nlp2uri editable"
            ),
            "detail": str(exc),
        }

    index = build_koru_ide_uri_index(status, socket_path=socket_path)
    payload = index.to_dict()
    payload["ok"] = True
    payload["source"] = "koru.autopilot.status"
    if socket_path:
        payload["socket"] = socket_path
    return payload
