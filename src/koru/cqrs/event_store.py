"""Thread-safe in-memory event store for lightweight event sourcing."""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class StoredEvent:
    """Persisted domain event envelope."""

    sequence: int
    event_id: str
    context: str
    event_type: str
    occurred_at: str
    payload: dict[str, Any]
    metadata: dict[str, Any]
    aggregate_id: str | None = None


class InMemoryEventStore:
    """Append-only event stream kept in memory for the current process."""

    def __init__(self, max_events: int = 10_000) -> None:
        self._lock = threading.Lock()
        self._events: deque[StoredEvent] = deque(maxlen=max(1, int(max_events)))
        self._sequence = 0

    def append(
        self,
        *,
        context: str,
        event_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        aggregate_id: str | None = None,
    ) -> StoredEvent:
        with self._lock:
            self._sequence += 1
            event = StoredEvent(
                sequence=self._sequence,
                event_id=uuid.uuid4().hex,
                context=context,
                event_type=event_type,
                occurred_at=_utc_now(),
                payload=dict(payload),
                metadata=dict(metadata or {}),
                aggregate_id=aggregate_id,
            )
            self._events.append(event)
            return event

    def all_events(self, *, context: str | None = None) -> list[StoredEvent]:
        with self._lock:
            events = list(self._events)
        if context is None:
            return events
        return [event for event in events if event.context == context]

    def events_for_aggregate(self, *, context: str, aggregate_id: str) -> list[StoredEvent]:
        return [
            event
            for event in self.all_events(context=context)
            if event.aggregate_id == aggregate_id
        ]


__all__ = ["InMemoryEventStore", "StoredEvent"]
