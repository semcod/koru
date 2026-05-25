"""CQRS support primitives for bounded contexts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.cqrs.domain_event import DomainEvent
from koru.cqrs.event_bus import InProcessEventBus
from koru.cqrs.event_log_projection import EventLogEntry, EventLogProjection
from koru.cqrs.event_log_query import EventLogQueryService
from koru.cqrs.event_store import (
    EventStore,
    InMemoryEventStore,
    JsonlEventStore,
    StoredEvent,
    project_event_store_path,
    storage_dir_event_store_path,
)


class EventSourcingRuntime:
    """Convenience wrapper around an event store and an event bus."""

    def __init__(
        self,
        *,
        store: EventStore | None = None,
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


class CqrsService:
    """Base class for CQRS services using EventSourcingRuntime."""

    def __init__(self, runtime: EventSourcingRuntime | None = None) -> None:
        self.runtime = runtime or EventSourcingRuntime()


def runtime_for_project(project: Path, *, bus: InProcessEventBus | None = None) -> EventSourcingRuntime:
    return EventSourcingRuntime(
        store=JsonlEventStore(project_event_store_path(project)),
        bus=bus,
    )


def runtime_for_storage_dir(
    storage_dir: Path,
    *,
    bus: InProcessEventBus | None = None,
) -> EventSourcingRuntime:
    return EventSourcingRuntime(
        store=JsonlEventStore(storage_dir_event_store_path(storage_dir)),
        bus=bus,
    )


__all__ = [
    "CqrsService",
    "DomainEvent",
    "EventStore",
    "EventSourcingRuntime",
    "EventLogEntry",
    "EventLogProjection",
    "EventLogQueryService",
    "InMemoryEventStore",
    "InProcessEventBus",
    "JsonlEventStore",
    "StoredEvent",
    "project_event_store_path",
    "runtime_for_project",
    "runtime_for_storage_dir",
    "storage_dir_event_store_path",
]
