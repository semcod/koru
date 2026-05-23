from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from koru.cqrs import DomainEvent, EventLogProjection, EventLogQueryService
from koru.cqrs.event_store import JsonlEventStore, StoredEvent


@dataclass(frozen=True)
class SampleEvent(DomainEvent):
    event_id: str
    count: int
    details: dict[str, object]


def _stored_event(*, sequence: int, context: str, event_type: str, payload: dict[str, object]) -> StoredEvent:
    return StoredEvent(
        sequence=sequence,
        event_id=f"e-{sequence}",
        context=context,
        event_type=event_type,
        occurred_at="2026-01-01T00:00:00Z",
        payload=payload,
        metadata={},
        aggregate_id="agg-1",
    )


def test_domain_event_to_payload_serializes_dataclass_fields() -> None:
    event = SampleEvent(
        event_id="evt-1",
        count=3,
        details={"status": "ok", "tags": ["cqrs", "contract"]},
    )

    payload = event.to_payload()

    assert payload == {
        "event_id": "evt-1",
        "count": 3,
        "details": {"status": "ok", "tags": ["cqrs", "contract"]},
    }


def test_event_log_projection_filters_context_and_applies_recent_limit() -> None:
    projection = EventLogProjection(context="topology")

    projection.handle(
        _stored_event(
            sequence=1,
            context="topology",
            event_type="topology.component_toggled",
            payload={"component_id": "redsl", "current": True},
        ),
    )
    projection.handle(
        _stored_event(
            sequence=2,
            context="local_manager",
            event_type="local_manager.action_enqueued",
            payload={"action_id": "a-1"},
        ),
    )
    projection.handle(
        _stored_event(
            sequence=3,
            context="topology",
            event_type="topology.saved",
            payload={"path": "/tmp/.koru/topology.yaml"},
        ),
    )

    all_entries = projection.recent()
    assert [entry.sequence for entry in all_entries] == [1, 3]
    assert [entry.event_type for entry in all_entries] == [
        "topology.component_toggled",
        "topology.saved",
    ]

    last_entry = projection.recent(limit=1)
    assert [entry.sequence for entry in last_entry] == [3]
    assert projection.recent(limit=0) == []


def test_event_log_projection_can_replay_store_and_filter_aggregate(tmp_path: Path) -> None:
    path = tmp_path / ".koru" / "event-store.jsonl"
    store = JsonlEventStore(path)
    store.append(
        context="topology",
        event_type="topology.component_toggled",
        payload={"component_id": "redsl"},
        aggregate_id="redsl",
    )
    store.append(
        context="topology",
        event_type="topology.pipeline_toggled",
        payload={"pipeline_id": "gate:wup"},
        aggregate_id="gate:wup",
    )
    store.append(
        context="local_manager",
        event_type="local_manager.action_enqueued",
        payload={"action_id": "a-1"},
        aggregate_id="a-1",
    )

    projection = EventLogProjection(context="topology")
    projection.replay(store)

    assert [entry.event_type for entry in projection.recent()] == [
        "topology.component_toggled",
        "topology.pipeline_toggled",
    ]
    assert [entry.aggregate_id for entry in projection.recent(aggregate_id="redsl")] == ["redsl"]


def test_event_log_query_service_reads_recent_history(tmp_path: Path) -> None:
    path = tmp_path / ".koru" / "event-store.jsonl"
    store = JsonlEventStore(path)
    store.append(
        context="tasks",
        event_type="tasks.created",
        payload={"ticket_id": "PLF-001"},
        aggregate_id="PLF-001",
    )
    store.append(
        context="tasks",
        event_type="tasks.reused",
        payload={"ticket_id": "PLF-001"},
        aggregate_id="PLF-001",
    )

    history = EventLogQueryService(store).recent(
        context="tasks",
        aggregate_id="PLF-001",
        limit=1,
    )

    assert [entry.event_type for entry in history] == ["tasks.reused"]


def test_jsonl_event_store_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / ".koru" / "event-store.jsonl"
    store = JsonlEventStore(path)

    first = store.append(
        context="tasks",
        event_type="tasks.created",
        payload={"ticket_id": "PLF-001"},
        aggregate_id="PLF-001",
    )
    second = store.append(
        context="tasks",
        event_type="tasks.reused",
        payload={"ticket_id": "PLF-001"},
        aggregate_id="PLF-001",
    )

    reloaded = JsonlEventStore(path)

    assert first.sequence == 1
    assert second.sequence == 2
    assert [event.sequence for event in reloaded.all_events(context="tasks")] == [1, 2]
    assert [event.event_type for event in reloaded.events_for_aggregate(context="tasks", aggregate_id="PLF-001")] == [
        "tasks.created",
        "tasks.reused",
    ]