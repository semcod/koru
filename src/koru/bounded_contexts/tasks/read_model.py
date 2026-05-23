"""Read models for the tasks bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import TASK_CONTEXT


class TaskEventLogProjection(EventLogProjection):
    """In-memory read model for task intake history."""

    def __init__(self) -> None:
        super().__init__(context=TASK_CONTEXT)


__all__ = ["EventLogEntry", "TaskEventLogProjection"]