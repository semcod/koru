"""Reusable in-memory event-log projections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from koru.cqrs.event_store import EventStore, StoredEvent


@dataclass(frozen=True)
class EventLogEntry:
    sequence: int
    event_type: str
    aggregate_id: str | None
    occurred_at: str
    payload: dict[str, Any]


class EventLogProjection:
    """Collect StoredEvent objects for a single bounded context."""

    context: str | None = None

    def __init__(self, *, context: str | None = None) -> None:
        self._context = context or self.context
        if not self._context:
            raise ValueError("context must be provided or set as a class attribute")
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

    def reset(self) -> None:
        self._entries.clear()

    def replay(self, events: Iterable[StoredEvent] | EventStore) -> None:
        self.reset()
        source = events.all_events(context=self._context) if hasattr(events, "all_events") else events
        for event in source:
            self.handle(event)

    def recent(
        self,
        limit: int | None = None,
        *,
        aggregate_id: str | None = None,
    ) -> list[EventLogEntry]:
        entries = list(self._entries)
        if aggregate_id is not None:
            entries = [entry for entry in entries if entry.aggregate_id == aggregate_id]
        if limit is None:
            return entries
        if limit <= 0:
            return []
        return entries[-limit:]


__all__ = ["EventLogEntry", "EventLogProjection"]