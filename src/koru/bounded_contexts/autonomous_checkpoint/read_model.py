"""Read models for the autonomous-checkpoint bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import AUTONOMOUS_CHECKPOINT_CONTEXT


class AutonomousCheckpointEventLogProjection(EventLogProjection):
    """In-memory read model for checkpoint history."""

    def __init__(self) -> None:
        super().__init__(context=AUTONOMOUS_CHECKPOINT_CONTEXT)


__all__ = ["AutonomousCheckpointEventLogProjection", "EventLogEntry"]