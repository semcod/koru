"""Shared read-side queries for persisted event logs."""

from __future__ import annotations

from koru.cqrs.event_log_projection import EventLogEntry
from koru.cqrs.event_store import EventStore


class EventLogQueryService:
    """Provides simple history queries over an event store."""

    def __init__(self, store: EventStore) -> None:
        self._store = store

    def recent(
        self,
        *,
        context: str,
        aggregate_id: str | None = None,
        limit: int | None = None,
    ) -> list[EventLogEntry]:
        if aggregate_id is None:
            events = self._store.all_events(context=context)
        else:
            events = self._store.events_for_aggregate(context=context, aggregate_id=aggregate_id)
        entries = [
            EventLogEntry(
                sequence=event.sequence,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                occurred_at=event.occurred_at,
                payload=dict(event.payload),
            )
            for event in events
        ]
        if limit is None:
            return entries
        if limit <= 0:
            return []
        return entries[-limit:]


__all__ = ["EventLogQueryService"]