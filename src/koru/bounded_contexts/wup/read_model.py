"""Read models for the WUP bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import WUP_CONTEXT


class WupEventLogProjection(EventLogProjection):
    """In-memory read model for WUP health evaluation history."""

    def __init__(self) -> None:
        super().__init__(context=WUP_CONTEXT)


__all__ = ["EventLogEntry", "WupEventLogProjection"]