"""Command objects for the local manager bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EnqueueActionCommand:
    action_id: str
    payload: dict[str, Any]
    received_at: str


@dataclass(frozen=True)
class ClaimActionCommand:
    worker_id: str
    capabilities: list[str]
    action_types: list[str] | None = None
    lease_seconds: int = 300


@dataclass(frozen=True)
class CompleteActionCommand:
    action_id: str
    worker_id: str | None
    status: str
    result: dict[str, Any] | None = None


@dataclass(frozen=True)
class RegisterWorkerCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class HeartbeatWorkerCommand:
    payload: dict[str, Any]


__all__ = [
    "ClaimActionCommand",
    "CompleteActionCommand",
    "EnqueueActionCommand",
    "HeartbeatWorkerCommand",
    "RegisterWorkerCommand",
]
