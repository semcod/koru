"""Read models for the planfile queue bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import PLANFILE_QUEUE_CONTEXT


class PlanfileQueueEventLogProjection(EventLogProjection):
    """In-memory read model for queue tick history."""

    context = PLANFILE_QUEUE_CONTEXT


__all__ = ["EventLogEntry", "PlanfileQueueEventLogProjection"]