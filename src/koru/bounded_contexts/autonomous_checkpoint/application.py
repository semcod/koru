"""Application services for the autonomous-checkpoint bounded context."""

from __future__ import annotations

from typing import Any

from koru.autonomous_checkpoint import (
    _apply_checkpoint_payload,
    _build_checkpoint_payload,
    _read_checkpoint_payload,
    _stdio_info,
    _write_checkpoint_payload,
)
from koru.cqrs import EventLogEntry, EventLogQueryService, EventSourcingRuntime

from .commands import RestoreLoopCheckpointCommand, SaveLoopCheckpointCommand
from .events import (
    AUTONOMOUS_CHECKPOINT_CONTEXT,
    LOOP_CHECKPOINT_RESTORED,
    LOOP_CHECKPOINT_SAVED,
    LoopCheckpointRestored,
    LoopCheckpointSaved,
)
from .queries import LoadCheckpointHistoryQuery, LoadLoopCheckpointSnapshotQuery


class AutonomousCheckpointCommandService:
    """Handles state-changing checkpoint operations."""

    def __init__(self, runtime: EventSourcingRuntime | None = None) -> None:
        self.runtime = runtime or EventSourcingRuntime()

    def save(self, command: SaveLoopCheckpointCommand) -> None:
        payload = _build_checkpoint_payload(
            cycle=command.cycle,
            state=command.state,
            queue_status=command.queue_status,
            waiting_ticket=command.waiting_ticket,
        )
        _write_checkpoint_payload(command.path, payload)
        event = LoopCheckpointSaved(
            path=str(command.path),
            cycle=command.cycle,
            queue_status=command.queue_status,
            waiting_ticket=command.waiting_ticket,
        )
        self.runtime.append_event(
            context=AUTONOMOUS_CHECKPOINT_CONTEXT,
            event_type=LOOP_CHECKPOINT_SAVED,
            payload=event.to_payload(),
            aggregate_id=str(command.path),
        )

    def restore(self, command: RestoreLoopCheckpointCommand) -> int | None:
        payload = _read_checkpoint_payload(command.path)
        if payload is None:
            return None
        cycle = _apply_checkpoint_payload(payload, command.state)
        if cycle is None:
            return None
        _stdio_info(
            f"koru autonomous: restored checkpoint cycle={cycle}",
            fmt=command.stdio_format,
        )
        event = LoopCheckpointRestored(
            path=str(command.path),
            cycle=cycle,
            queue_status=str(payload.get("queue_status") or ""),
            waiting_ticket=str(payload.get("waiting_ticket") or ""),
        )
        self.runtime.append_event(
            context=AUTONOMOUS_CHECKPOINT_CONTEXT,
            event_type=LOOP_CHECKPOINT_RESTORED,
            payload=event.to_payload(),
            aggregate_id=str(command.path),
        )
        return cycle


class AutonomousCheckpointQueryService:
    """Handles read-only checkpoint queries."""

    def __init__(self, runtime: EventSourcingRuntime | None = None) -> None:
        self.runtime = runtime or EventSourcingRuntime()

    def load_snapshot(self, query: LoadLoopCheckpointSnapshotQuery) -> dict[str, Any] | None:
        return _read_checkpoint_payload(query.path)

    def history(self, query: LoadCheckpointHistoryQuery) -> list[EventLogEntry]:
        aggregate_id = str(query.path) if query.path is not None else None
        return EventLogQueryService(self.runtime.store).recent(
            context=AUTONOMOUS_CHECKPOINT_CONTEXT,
            aggregate_id=aggregate_id,
            limit=query.limit,
        )


__all__ = ["AutonomousCheckpointCommandService", "AutonomousCheckpointQueryService"]