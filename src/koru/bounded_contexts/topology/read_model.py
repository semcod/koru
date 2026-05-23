"""Read models for the topology bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import TOPOLOGY_CONTEXT


class TopologyEventLogProjection(EventLogProjection):
    """In-memory read model for topology change history."""

    def __init__(self) -> None:
        super().__init__(context=TOPOLOGY_CONTEXT)


__all__ = ["EventLogEntry", "TopologyEventLogProjection"]