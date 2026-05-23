"""CQRS support primitives for bounded contexts."""

from __future__ import annotations

from typing import Any

from koru.cqrs.domain_event import DomainEvent
from koru.cqrs.event_bus import InProcessEventBus
from koru.cqrs.event_log_projection import EventLogEntry, EventLogProjection
from koru.cqrs.event_store import InMemoryEventStore, StoredEvent


class EventSourcingRuntime:
    """Convenience wrapper around an event store and an event bus."""

    def __init__(
        self,
        *,
        store: InMemoryEventStore | None = None,
        bus: InProcessEventBus | None = None,
    ) -> None:
        self.store = store or InMemoryEventStore()
        self.bus = bus or InProcessEventBus()

    def append_event(
        self,
        *,
        context: str,
        event_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        aggregate_id: str | None = None,
    ) -> StoredEvent:
        event = self.store.append(
            context=context,
            event_type=event_type,
            payload=payload,
            metadata=metadata,
            aggregate_id=aggregate_id,
        )
        self.bus.publish(event)
        return event


__all__ = [
    "DomainEvent",
    "EventSourcingRuntime",
    "EventLogEntry",
    "EventLogProjection",
    "InMemoryEventStore",
    "InProcessEventBus",
    "StoredEvent",
]
