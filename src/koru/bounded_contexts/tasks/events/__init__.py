"""Domain events for the tasks bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

TASK_CONTEXT = "tasks"

TASK_CREATED = "tasks.created"
TASK_REUSED = "tasks.reused"


@dataclass(frozen=True)
class TaskCreated(DomainEvent):
    ticket_id: str
    sprint: str
    path: str
    name: str
    queue_name: str
    priority: str


@dataclass(frozen=True)
class TaskReused(DomainEvent):
    ticket_id: str
    sprint: str
    path: str
    name: str


__all__ = [
    "TASK_CONTEXT",
    "TASK_CREATED",
    "TASK_REUSED",
    "TaskCreated",
    "TaskReused",
]