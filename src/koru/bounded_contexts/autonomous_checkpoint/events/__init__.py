"""Domain events for the autonomous-checkpoint bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

AUTONOMOUS_CHECKPOINT_CONTEXT = "autonomous_checkpoint"

LOOP_CHECKPOINT_SAVED = "autonomous_checkpoint.saved"
LOOP_CHECKPOINT_RESTORED = "autonomous_checkpoint.restored"


@dataclass(frozen=True)
class LoopCheckpointSaved(DomainEvent):
    path: str
    cycle: int
    queue_status: str
    waiting_ticket: str


@dataclass(frozen=True)
class LoopCheckpointRestored(DomainEvent):
    path: str
    cycle: int
    queue_status: str
    waiting_ticket: str


__all__ = [
    "AUTONOMOUS_CHECKPOINT_CONTEXT",
    "LOOP_CHECKPOINT_RESTORED",
    "LOOP_CHECKPOINT_SAVED",
    "LoopCheckpointRestored",
    "LoopCheckpointSaved",
]