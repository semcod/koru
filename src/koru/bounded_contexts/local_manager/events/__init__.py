"""Domain events for the local manager bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LOCAL_MANAGER_CONTEXT = "local_manager"

ACTION_ENQUEUED = "local_manager.action_enqueued"
ACTION_CLAIMED = "local_manager.action_claimed"
ACTION_COMPLETED = "local_manager.action_completed"
WORKER_REGISTERED = "local_manager.worker_registered"
WORKER_HEARTBEATED = "local_manager.worker_heartbeated"


@dataclass(frozen=True)
class ActionEnqueued:
    action_id: str
    action_type: str
    status: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "status": self.status,
        }


@dataclass(frozen=True)
class ActionClaimed:
    action_id: str
    worker_id: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "worker_id": self.worker_id,
        }


@dataclass(frozen=True)
class ActionCompleted:
    action_id: str
    status: str
    worker_id: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "status": self.status,
            "worker_id": self.worker_id,
        }


@dataclass(frozen=True)
class WorkerRegistered:
    worker_id: str
    version: str
    decision: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "version": self.version,
            "decision": self.decision,
        }


@dataclass(frozen=True)
class WorkerHeartbeated:
    worker_id: str
    version: str
    decision: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "version": self.version,
            "decision": self.decision,
        }


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
