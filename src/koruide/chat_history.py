"""Read plugin-emitted chat events from the shared NDJSON file.

The autopilot daemon writes every ``message.sent`` / ``message.received`` /
``session.*`` event from the IDE plugin into a single append-only NDJSON file
(see :meth:`koruide.daemon.AutopilotDaemon._append_event`). The autonomous
loop reads that file to decide whether the LLM in the IDE is *still working
on the current ticket* (so we should NOT redrive the same prompt) or whether
the conversation has gone quiet (so we may redrive).

The format is a stable contract between the daemon and the loop:

.. code-block:: json

    {"ts": 1716406400.12, "type": "message.sent", "ide": "vscode",
     "chat": "default", "text": "<full prompt>", "length": 236}
    {"ts": 1716406470.55, "type": "message.received", "ide": "vscode",
     "chat": "default", "text": "<LLM reply>", "summary": "<short>"}
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ChatEvent:
    """Single plugin event as read from the NDJSON file."""

    ts: float
    type: str
    ide: str
    chat: str
    text: str = ""
    summary: str = ""
    length: int = 0
    reason: str = ""

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.ts)


def default_events_path() -> Path:
    """Path daemon writes to (matches ``AutopilotDaemon._event_path``)."""
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_dir) / "koru-autopilot-events.ndjson"


def _parse_line(line: str) -> ChatEvent | None:
    line = line.strip()
    if not line:
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return ChatEvent(
            ts=float(payload.get("ts") or 0.0),
            type=str(payload.get("type") or ""),
            ide=str(payload.get("ide") or ""),
            chat=str(payload.get("chat") or "default"),
            text=str(payload.get("text") or ""),
            summary=str(payload.get("summary") or ""),
            length=int(payload.get("length") or 0),
            reason=str(payload.get("reason") or ""),
        )
    except (TypeError, ValueError):
        return None


def _event_matches_filters(
    ev: ChatEvent,
    *,
    ide: str | None,
    chat: str | None,
    type_filter: set[str] | None,
    max_age_seconds: float | None,
) -> bool:
    if ide is not None and ev.ide != ide:
        return False
    if chat is not None and ev.chat != chat:
        return False
    if type_filter is not None and ev.type not in type_filter:
        return False
    if max_age_seconds is not None and ev.age_seconds > max_age_seconds:
        return False
    return True


def read_events(
    path: Path | None = None,
    *,
    ide: str | None = None,
    chat: str | None = None,
    max_age_seconds: float | None = None,
    types: Iterable[str] | None = None,
    limit: int = 200,
) -> list[ChatEvent]:
    """Read recent chat events, newest last (chronological)."""
    target = path or default_events_path()
    if not target.exists():
        return []
    try:
        raw_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    events: list[ChatEvent] = []
    type_filter = set(types) if types is not None else None
    for line in raw_lines[-(limit * 4) :]:
        ev = _parse_line(line)
        if ev is None:
            continue
        if not _event_matches_filters(
            ev, ide=ide, chat=chat, type_filter=type_filter, max_age_seconds=max_age_seconds
        ):
            continue
        events.append(ev)
    return events[-limit:]


def last_event(
    path: Path | None = None,
    *,
    ide: str | None = None,
    chat: str | None = None,
    types: Iterable[str] | None = None,
) -> ChatEvent | None:
    events = read_events(path, ide=ide, chat=chat, types=types, limit=10)
    return events[-1] if events else None


def has_recent_activity(
    *,
    path: Path | None = None,
    ide: str | None = None,
    chat: str | None = None,
    within_seconds: float,
    types: Iterable[str] = ("message.sent", "message.received"),
) -> bool:
    """True iff any event of ``types`` was emitted within ``within_seconds``."""
    events = read_events(
        path,
        ide=ide,
        chat=chat,
        max_age_seconds=within_seconds,
        types=types,
        limit=20,
    )
    return bool(events)


__all__ = [
    "ChatEvent",
    "default_events_path",
    "has_recent_activity",
    "last_event",
    "read_events",
]
