"""Application services for the tasks bounded context."""

from __future__ import annotations

from typing import Any

from koru.cqrs import EventSourcingRuntime
from koru.tasks import CreatedTask, _create_nl_task_impl, _read_config, _read_sprint

from .commands import CreateNlTaskCommand
from .events import TASK_CONTEXT, TASK_CREATED, TASK_REUSED, TaskCreated, TaskReused
from .queries import LoadTaskConfigQuery, LoadTaskSprintQuery


class TaskCommandService:
    """Handles state-changing task intake operations."""

    def __init__(self, runtime: EventSourcingRuntime | None = None) -> None:
        self.runtime = runtime or EventSourcingRuntime()

    def create_nl_task(self, command: CreateNlTaskCommand) -> CreatedTask:
        created = _create_nl_task_impl(
            command.project,
            command.text,
            sprint=command.sprint,
            queue_name=command.queue_name,
            priority=command.priority,
            scaffold=command.scaffold,
        )
        if created.reused:
            event = TaskReused(
                ticket_id=created.ticket_id,
                sprint=created.sprint,
                path=str(created.path),
                name=created.name,
            )
            self.runtime.append_event(
                context=TASK_CONTEXT,
                event_type=TASK_REUSED,
                payload=event.to_payload(),
                aggregate_id=created.ticket_id,
            )
            return created

        event = TaskCreated(
            ticket_id=created.ticket_id,
            sprint=created.sprint,
            path=str(created.path),
            name=created.name,
            queue_name=command.queue_name or "default",
            priority=command.priority,
        )
        self.runtime.append_event(
            context=TASK_CONTEXT,
            event_type=TASK_CREATED,
            payload=event.to_payload(),
            aggregate_id=created.ticket_id,
        )
        return created


class TaskQueryService:
    """Handles read-only task queries."""

    def load_config(self, query: LoadTaskConfigQuery) -> dict[str, Any]:
        return _read_config(query.path, project_name=query.project_name)

    def load_sprint(self, query: LoadTaskSprintQuery) -> dict[str, Any]:
        return _read_sprint(query.path, sprint=query.sprint)


__all__ = ["TaskCommandService", "TaskQueryService"]