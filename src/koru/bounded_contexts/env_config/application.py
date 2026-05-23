"""Application services for the environment-config bounded context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.cqrs import EventSourcingRuntime

from .commands import ApplyEnvUpdatesCommand, WriteEnvConfigCommand
from .events import ENV_CONFIG_CONTEXT, ENV_CONFIG_WRITTEN, ENV_UPDATES_APPLIED, EnvConfigWritten, EnvUpdatesApplied
from .queries import LoadEnvConfigQuery


class EnvConfigCommandService:
    """Handles state-changing environment configuration operations."""

    def __init__(self, runtime: EventSourcingRuntime | None = None) -> None:
        self.runtime = runtime or EventSourcingRuntime()

    def write(self, command: WriteEnvConfigCommand) -> Path:
        from koru.env_config import _write_env_file
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


class EnvConfigQueryService:
    """Handles read-only environment configuration queries."""

    def load(self, query: LoadEnvConfigQuery) -> dict[str, Any]:
        from koru.env_config import _build_env_payload
        return _build_env_payload(query.project, query.environ)


__all__ = ["EnvConfigCommandService", "EnvConfigQueryService"]