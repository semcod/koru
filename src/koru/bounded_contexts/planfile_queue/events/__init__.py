"""Domain events for the planfile queue bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

PLANFILE_QUEUE_CONTEXT = "planfile_queue"

PLANFILE_QUEUE_TASK_COMPLETED = "planfile_queue.task_completed"
PLANFILE_QUEUE_TASK_FAILED = "planfile_queue.task_failed"
PLANFILE_QUEUE_TASK_WAITING = "planfile_queue.task_waiting"
PLANFILE_QUEUE_IDLE = "planfile_queue.idle"
PLANFILE_QUEUE_TICK_ERROR = "planfile_queue.tick_error"


@dataclass(frozen=True)
class PlanfileQueueTaskCompleted(DomainEvent):
    ticket_id: str
    executor_kind: str
    message: str
    exit_code: int


@dataclass(frozen=True)
class PlanfileQueueTaskFailed(DomainEvent):
    ticket_id: str
    executor_kind: str
    message: str
    exit_code: int
    stderr: str


@dataclass(frozen=True)
class PlanfileQueueTaskWaiting(DomainEvent):
    ticket_id: str
    executor_kind: str
    status: str
    message: str


@dataclass(frozen=True)
class PlanfileQueueIdle(DomainEvent):
    message: str


@dataclass(frozen=True)
class PlanfileQueueTickError(DomainEvent):
    status: str
    ticket_id: str
    message: str
    exit_code: int
    stderr: str


__all__ = [
    "PLANFILE_QUEUE_CONTEXT",
    "PLANFILE_QUEUE_IDLE",
    "PLANFILE_QUEUE_TASK_COMPLETED",
    "PLANFILE_QUEUE_TASK_FAILED",
    "PLANFILE_QUEUE_TASK_WAITING",
    "PLANFILE_QUEUE_TICK_ERROR",
    "PlanfileQueueIdle",
    "PlanfileQueueTaskCompleted",
    "PlanfileQueueTaskFailed",
    "PlanfileQueueTaskWaiting",
    "PlanfileQueueTickError",
]