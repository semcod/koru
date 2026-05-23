"""Read models for the local manager bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import LOCAL_MANAGER_CONTEXT


class LocalManagerEventLogProjection(EventLogProjection):
    """In-memory read model for local-manager change history."""

    def __init__(self) -> None:
        super().__init__(context=LOCAL_MANAGER_CONTEXT)


__all__ = ["EventLogEntry", "LocalManagerEventLogProjection"]