"""Domain events for the local manager bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

LOCAL_MANAGER_CONTEXT = "local_manager"

ACTION_ENQUEUED = "local_manager.action_enqueued"
ACTION_CLAIMED = "local_manager.action_claimed"
ACTION_COMPLETED = "local_manager.action_completed"
WORKER_REGISTERED = "local_manager.worker_registered"
WORKER_HEARTBEATED = "local_manager.worker_heartbeated"


@dataclass(frozen=True)
class ActionEnqueued(DomainEvent):
    action_id: str
    action_type: str
    status: str


@dataclass(frozen=True)
class ActionClaimed(DomainEvent):
    action_id: str
    worker_id: str


@dataclass(frozen=True)
class ActionCompleted(DomainEvent):
    action_id: str
    status: str
    worker_id: str | None


@dataclass(frozen=True)
class WorkerRegistered(DomainEvent):
    worker_id: str
    version: str
    decision: dict[str, object]


@dataclass(frozen=True)
class WorkerHeartbeated(DomainEvent):
    worker_id: str
    version: str
    decision: dict[str, object]


__all__ = [
    "ACTION_CLAIMED",
    "ACTION_COMPLETED",
    "ACTION_ENQUEUED",
    "ActionClaimed",
    "ActionCompleted",
    "ActionEnqueued",
    "LOCAL_MANAGER_CONTEXT",
    "WORKER_HEARTBEATED",
    "WORKER_REGISTERED",
    "WorkerHeartbeated",
    "WorkerRegistered",
]
