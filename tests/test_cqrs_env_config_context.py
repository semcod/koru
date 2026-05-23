from __future__ import annotations

import os
from pathlib import Path

from koru.bounded_contexts.env_config.application import (
    EnvConfigCommandService,
    EnvConfigQueryService,
)
from koru.bounded_contexts.env_config.commands import (
    ApplyEnvUpdatesCommand,
    WriteEnvConfigCommand,
)
from koru.bounded_contexts.env_config.events import (
    ENV_CONFIG_CONTEXT,
    ENV_CONFIG_WRITTEN,
    ENV_UPDATES_APPLIED,
)
from koru.bounded_contexts.env_config.queries import LoadEnvConfigHistoryQuery, LoadEnvConfigQuery
from koru.bounded_contexts.env_config.read_model import EnvConfigEventLogProjection
from koru.cqrs import EventSourcingRuntime, runtime_for_project


def test_env_config_commands_emit_domain_events(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = EnvConfigEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = EnvConfigCommandService(runtime)
    query_service = EnvConfigQueryService()
    environ = {"KORU_VISION_SCALE": "0.3"}

    path = command_service.write(
        WriteEnvConfigCommand(
            project=tmp_path,
            updates={"KORU_VISION_INTERVAL": "45", "KORU_VISION_PROVIDER": "mss"},
        ),
    )
    applied = command_service.apply_updates(
        ApplyEnvUpdatesCommand(
            project=tmp_path,
            updates={"KORU_VISION_SCALE": "0.5", "KORU_VISION_PROVIDER": ""},
            environ=environ,
        ),
    )

    payload = query_service.load(LoadEnvConfigQuery(project=tmp_path, environ=environ))

    assert path == tmp_path / ".env"
    assert applied == {"KORU_VISION_SCALE": "0.5", "KORU_VISION_PROVIDER": ""}
    assert environ == {"KORU_VISION_SCALE": "0.5"}
    by_name = {row["name"]: row for row in payload["keys"]}
    assert by_name["KORU_VISION_INTERVAL"]["file_value"] == "45"
    assert by_name["KORU_VISION_SCALE"]["env_value"] == "0.5"

    events = runtime.store.all_events(context=ENV_CONFIG_CONTEXT)
    assert [event.event_type for event in events] == [
        ENV_CONFIG_WRITTEN,
        ENV_UPDATES_APPLIED,
    ]

    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [
        ENV_CONFIG_WRITTEN,
        ENV_UPDATES_APPLIED,
    ]
    assert projected[0].aggregate_id == str(tmp_path.resolve())


def test_env_config_history_query_reads_persisted_events(tmp_path: Path) -> None:
    runtime = runtime_for_project(tmp_path)
    command_service = EnvConfigCommandService(runtime)
    query_service = EnvConfigQueryService(runtime)

    command_service.write(
        WriteEnvConfigCommand(
            project=tmp_path,
            updates={"KORU_VISION_INTERVAL": "45"},
        )
    )
    command_service.apply_updates(
        ApplyEnvUpdatesCommand(
            project=tmp_path,
            updates={"KORU_VISION_SCALE": "0.4"},
            environ={},
        )
    )

    history = query_service.history(LoadEnvConfigHistoryQuery(project=tmp_path, limit=10))

    assert [entry.event_type for entry in history] == [
        ENV_CONFIG_WRITTEN,
        ENV_UPDATES_APPLIED,
    ]
    assert all(entry.aggregate_id == str(tmp_path.resolve()) for entry in history)