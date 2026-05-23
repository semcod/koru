"""Reusable in-memory event-log projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from koru.cqrs.event_store import StoredEvent


@dataclass(frozen=True)
class EventLogEntry:
    sequence: int
    event_type: str
    aggregate_id: str | None
    occurred_at: str
    payload: dict[str, Any]


class EventLogProjection:
    """Collect StoredEvent objects for a single bounded context."""

    def __init__(self, *, context: str) -> None:
        self._context = context
        self._entries: list[EventLogEntry] = []

    def handle(self, event: StoredEvent) -> None:
        if event.context != self._context:
            return
        self._entries.append(
            EventLogEntry(
                sequence=event.sequence,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                occurred_at=event.occurred_at,
                payload=dict(event.payload),
            ),
        )

    def recent(self, limit: int | None = None) -> list[EventLogEntry]:
        entries = list(self._entries)
        if limit is None:
            return entries
        if limit <= 0:
            return []
        return entries[-limit:]


__all__ = ["EventLogEntry", "EventLogProjection"]