"""Application services for the local manager bounded context."""

from __future__ import annotations

from typing import Any

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
    ActionClaimed,
    ActionCompleted,
    ActionEnqueued,
    WorkerHeartbeated,
    WorkerRegistered,
)
from koru.bounded_contexts.local_manager.queries import (
    HealthSnapshotQuery,
    QueueSnapshotQuery,
    StateSnapshotQuery,
    WorkersSnapshotQuery,
)
from koru.cqrs import EventSourcingRuntime
from koru.local_manager_state import ServiceState


class LocalManagerCommandService:
    """Handles state-changing local-manager operations."""

    def __init__(
        self,
        state: ServiceState,
        runtime: EventSourcingRuntime | None = None,
    ) -> None:
        self._state = state
        self.runtime = runtime or EventSourcingRuntime()

    def enqueue(self, command: EnqueueActionCommand) -> dict[str, Any]:
        item = self._state.queue.enqueue(command.action_id, command.payload, command.received_at)
        event = ActionEnqueued(
            action_id=item["id"],
            action_type=str(item.get("type") or "generic"),
            status=str(item.get("status") or "queued"),
        )
        self.runtime.append_event(
            context=LOCAL_MANAGER_CONTEXT,
            event_type=ACTION_ENQUEUED,
            payload=event.to_payload(),
            aggregate_id=item["id"],
        )
        return item

    def claim(self, command: ClaimActionCommand) -> dict[str, Any] | None:
        item = self._state.queue.claim(
            worker_id=command.worker_id,
            capabilities=command.capabilities,
            action_types=command.action_types,
            lease_seconds=command.lease_seconds,
        )
        if item is None:
            return None
        event = ActionClaimed(action_id=item["id"], worker_id=command.worker_id)
        self.runtime.append_event(
            context=LOCAL_MANAGER_CONTEXT,
            event_type=ACTION_CLAIMED,
            payload=event.to_payload(),
            aggregate_id=item["id"],
        )
        return item

    def complete(self, command: CompleteActionCommand) -> dict[str, Any] | None:
        item = self._state.queue.complete(
            action_id=command.action_id,
            worker_id=command.worker_id,
            status=command.status,
            result=command.result,
        )
        if item is None:
            return None
        event = ActionCompleted(
            action_id=command.action_id,
            status=command.status,
            worker_id=command.worker_id,
        )
        self.runtime.append_event(
            context=LOCAL_MANAGER_CONTEXT,
            event_type=ACTION_COMPLETED,
            payload=event.to_payload(),
            aggregate_id=command.action_id,
        )
        return item

    def register_worker(self, command: RegisterWorkerCommand) -> dict[str, Any]:
        reply = self._state.workers.register(command.payload)
        event = WorkerRegistered(
            worker_id=str(reply["worker"]["worker_id"]),
            version=str(reply["worker"].get("version") or ""),
            decision=dict(reply.get("decision") or {}),
        )
        self.runtime.append_event(
            context=LOCAL_MANAGER_CONTEXT,
            event_type=WORKER_REGISTERED,
            payload=event.to_payload(),
            aggregate_id=event.worker_id,
        )
        return reply

    def heartbeat_worker(self, command: HeartbeatWorkerCommand) -> dict[str, Any]:
        reply = self._state.workers.heartbeat(command.payload)
        event = WorkerHeartbeated(
            worker_id=str(reply["worker"]["worker_id"]),
            version=str(reply["worker"].get("version") or ""),
            decision=dict(reply.get("decision") or {}),
        )
        self.runtime.append_event(
            context=LOCAL_MANAGER_CONTEXT,
            event_type=WORKER_HEARTBEATED,
            payload=event.to_payload(),
            aggregate_id=event.worker_id,
        )
        return reply


class LocalManagerQueryService:
    """Handles read-only local-manager queries."""

    def __init__(self, state: ServiceState) -> None:
        self._state = state

    def health(self, query: HealthSnapshotQuery) -> dict[str, Any]:
        queue_snapshot = self._state.queue.snapshot()
        workers_snapshot = self._state.workers.snapshot()
        return {
            "ok": True,
            "version": query.koru_version,
            "service": "koru-local-manager",
            "active_worker_id": workers_snapshot["active_worker_id"],
            "queue_counts": queue_snapshot["counts"],
        }

    def queue_snapshot(self, _query: QueueSnapshotQuery) -> dict[str, Any]:
        return self._state.queue.snapshot()

    def workers_snapshot(self, _query: WorkersSnapshotQuery) -> dict[str, Any]:
        return self._state.workers.snapshot()

    def state_snapshot(self, _query: StateSnapshotQuery) -> dict[str, Any]:
        return {
            "queue": self._state.queue.snapshot(),
            "workers": self._state.workers.snapshot(),
        }


__all__ = ["LocalManagerCommandService", "LocalManagerQueryService"]
