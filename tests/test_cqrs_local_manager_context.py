from __future__ import annotations

from koru.cqrs import EventSourcingRuntime
from koru.bounded_contexts.local_manager.application import (
    LocalManagerCommandService,
    LocalManagerQueryService,
)
from koru.bounded_contexts.local_manager.commands import (
    ClaimActionCommand,
    CompleteActionCommand,
    EnqueueActionCommand,
    HeartbeatWorkerCommand,
    RegisterWorkerCommand,
)
from koru.bounded_contexts.local_manager.events import (
    ACTION_CLAIMED,
    ACTION_COMPLETED,
    ACTION_ENQUEUED,
    LOCAL_MANAGER_CONTEXT,
    WORKER_HEARTBEATED,
    WORKER_REGISTERED,
)
from koru.bounded_contexts.local_manager.read_model import LocalManagerEventLogProjection
from koru.bounded_contexts.local_manager.queries import HealthSnapshotQuery
from koru.local_manager_state import ServiceState


def test_local_manager_commands_emit_domain_events() -> None:
    state = ServiceState(max_events=16)
    runtime = EventSourcingRuntime()
    projection = LocalManagerEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = LocalManagerCommandService(state, runtime)
    query_service = LocalManagerQueryService(state)

    enqueued = command_service.enqueue(
        EnqueueActionCommand(
            action_id="a-1",
            payload={"type": "demo"},
            received_at="2026-01-01T00:00:00Z",
        ),
    )
    claimed = command_service.claim(
        ClaimActionCommand(worker_id="w-1", capabilities=[]),
    )
    completed = command_service.complete(
        CompleteActionCommand(
            action_id="a-1",
            worker_id="w-1",
            status="completed",
            result={"ok": True},
        ),
    )
    command_service.register_worker(
        RegisterWorkerCommand(payload={"worker_id": "w-1", "version": "1.0.0", "health": "ok"}),
    )
    command_service.heartbeat_worker(
        HeartbeatWorkerCommand(payload={"worker_id": "w-1", "health": "ok"}),
    )

    assert enqueued["id"] == "a-1"
    assert claimed is not None
    assert completed is not None

    health = query_service.health(HealthSnapshotQuery(koru_version="1.0.0"))
    assert health["ok"] is True
    assert health["queue_counts"] == {"completed": 1}

    events = command_service.runtime.store.all_events(context=LOCAL_MANAGER_CONTEXT)
    assert [event.event_type for event in events] == [
        ACTION_ENQUEUED,
        ACTION_CLAIMED,
        ACTION_COMPLETED,
        WORKER_REGISTERED,
        WORKER_HEARTBEATED,
    ]

    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [
        ACTION_ENQUEUED,
        ACTION_CLAIMED,
        ACTION_COMPLETED,
        WORKER_REGISTERED,
        WORKER_HEARTBEATED,
    ]
    assert projected[0].aggregate_id == "a-1"
