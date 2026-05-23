"""Thread-safe in-memory event store for lightweight event sourcing."""

from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
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


class EventStore(Protocol):
    """Minimal append/read contract for event stores."""

    def append(
        self,
        *,
        context: str,
        event_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        aggregate_id: str | None = None,
    ) -> StoredEvent: ...

    def all_events(self, *, context: str | None = None) -> list[StoredEvent]: ...

    def events_for_aggregate(self, *, context: str, aggregate_id: str) -> list[StoredEvent]: ...


def _event_to_record(event: StoredEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "event_id": event.event_id,
        "context": event.context,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "payload": event.payload,
        "metadata": event.metadata,
        "aggregate_id": event.aggregate_id,
    }


def _record_to_event(record: dict[str, Any]) -> StoredEvent:
    return StoredEvent(
        sequence=int(record["sequence"]),
        event_id=str(record["event_id"]),
        context=str(record["context"]),
        event_type=str(record["event_type"]),
        occurred_at=str(record["occurred_at"]),
        payload=dict(record.get("payload") or {}),
        metadata=dict(record.get("metadata") or {}),
        aggregate_id=(
            None if record.get("aggregate_id") is None else str(record.get("aggregate_id"))
        ),
    )


def project_event_store_path(project: Path, *, file_name: str = "event-store.jsonl") -> Path:
    return project.resolve() / ".koru" / file_name


def storage_dir_event_store_path(storage_dir: Path, *, file_name: str = "event-store.jsonl") -> Path:
    return storage_dir.resolve() / file_name


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


class JsonlEventStore:
    """Append-only JSONL event store persisted under a workspace state dir."""

    def __init__(self, path: Path, max_events: int = 10_000) -> None:
        self.path = path.resolve()
        self._lock = threading.Lock()
        self._events: deque[StoredEvent] = deque(maxlen=max(1, int(max_events)))
        self._sequence = 0
        self._load_existing_events()

    def _load_existing_events(self) -> None:
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        events: list[StoredEvent] = []
        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            try:
                events.append(_record_to_event(record))
            except (KeyError, TypeError, ValueError):
                continue
        if events:
            self._sequence = max(event.sequence for event in events)
            self._events.extend(events[-self._events.maxlen :])

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
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{json.dumps(_event_to_record(event), ensure_ascii=True)}\n")
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


__all__ = [
    "EventStore",
    "InMemoryEventStore",
    "JsonlEventStore",
    "StoredEvent",
    "project_event_store_path",
    "storage_dir_event_store_path",
]
