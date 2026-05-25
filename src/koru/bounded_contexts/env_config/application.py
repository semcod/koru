"""Application services for the environment-config bounded context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.cqrs import CqrsService, EventLogEntry, EventLogQueryService
from koru.domain.env import _build_env_payload, _write_env_file

from .commands import ApplyEnvUpdatesCommand, WriteEnvConfigCommand
from .events import (
    ENV_CONFIG_CONTEXT,
    ENV_CONFIG_WRITTEN,
    ENV_UPDATES_APPLIED,
    EnvConfigWritten,
    EnvUpdatesApplied,
)
from .queries import LoadEnvConfigHistoryQuery, LoadEnvConfigQuery


class EnvConfigCommandService(CqrsService):
    """Handles state-changing environment configuration operations."""

    def write(self, command: WriteEnvConfigCommand) -> Path:
        path = _write_env_file(command.project, command.updates)
        event = EnvConfigWritten(
            project=str(command.project.resolve()),
            path=str(path),
            updated_keys=sorted(command.updates),
        )
        self.runtime.append_event(
            context=ENV_CONFIG_CONTEXT,
            event_type=ENV_CONFIG_WRITTEN,
            payload=event.to_payload(),
            aggregate_id=str(command.project.resolve()),
        )
        return path

    def apply_updates(self, command: ApplyEnvUpdatesCommand) -> dict[str, str]:
        for key, value in command.updates.items():
            if value:
                command.environ[key] = value
            else:
                command.environ.pop(key, None)
        event = EnvUpdatesApplied(
            project=str(command.project.resolve()),
            updated_keys=sorted(command.updates),
        )
        self.runtime.append_event(
            context=ENV_CONFIG_CONTEXT,
            event_type=ENV_UPDATES_APPLIED,
            payload=event.to_payload(),
            aggregate_id=str(command.project.resolve()),
        )
        return dict(command.updates)


class EnvConfigQueryService(CqrsService):
    """Handles read-only environment configuration queries."""

    def load(self, query: LoadEnvConfigQuery) -> dict[str, Any]:
        return _build_env_payload(query.project, query.environ)

    def history(self, query: LoadEnvConfigHistoryQuery) -> list[EventLogEntry]:
        aggregate_id = str(query.project.resolve()) if query.project is not None else None
        return EventLogQueryService(self.runtime.store).recent(
            context=ENV_CONFIG_CONTEXT,
            aggregate_id=aggregate_id,
            limit=query.limit,
        )


__all__ = ["EnvConfigCommandService", "EnvConfigQueryService"]