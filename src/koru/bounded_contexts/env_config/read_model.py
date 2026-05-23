"""Read models for the environment-config bounded context."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import ENV_CONFIG_CONTEXT


class EnvConfigEventLogProjection(EventLogProjection):
    """In-memory read model for environment configuration history."""

    def __init__(self) -> None:
        super().__init__(context=ENV_CONFIG_CONTEXT)


__all__ = ["EventLogEntry", "EnvConfigEventLogProjection"]