"""Watch planfile queue events over WebSocket."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def format_queue_event(event: dict[str, Any]) -> str:
    """Return a compact human-readable line for a planfile WebSocket event."""
    if event.get("ok") is True and "message" in event:
        return f"connected: {event['message']}"

    event_type = str(event.get("type") or "event")
    action = str(event.get("action") or "-")
    ticket_id = str(event.get("ticket_id") or "-")
    ticket = event.get("ticket") if isinstance(event.get("ticket"), dict) else {}
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}

    parts = [event_type, action, ticket_id]
    if ticket.get("name"):
        parts.append(str(ticket["name"]))
    if execution.get("state"):
        parts.append(f"state={execution['state']}")
    if execution.get("assigned_to"):
        parts.append(f"assigned_to={execution['assigned_to']}")
    if execution.get("last_error"):
        parts.append(f"error={execution['last_error']}")

    return " | ".join(parts)


async def _default_connect(ws_url: str):
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("Install watch support with: pip install 'koru[watch]'") from exc

    return websockets.connect(ws_url)


async def watch_planfile_events(
    ws_url: str,
    *,
    max_events: int | None = None,
    printer: Callable[[str], None] = print,
    connector: Callable[[str], Any] | None = None,
) -> int:
    """Watch planfile WebSocket events and print compact status lines."""
    connect = connector or _default_connect
    seen = 0

    try:
        async with await connect(ws_url) as websocket:
            while max_events is None or seen < max_events:
                raw = await websocket.recv()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    printer(raw)
                else:
                    printer(format_queue_event(payload))
                seen += 1
    except Exception as exc:
        raise RuntimeError(
            f"Could not connect to planfile WebSocket at {ws_url}: {exc}"
        ) from exc

    return seen
