from __future__ import annotations

from pathlib import Path

from koru.bounded_contexts.tasks.application import TaskCommandService, TaskQueryService
from koru.bounded_contexts.tasks.commands import CreateNlTaskCommand
from koru.bounded_contexts.tasks.events import TASK_CONTEXT, TASK_CREATED, TASK_REUSED
from koru.bounded_contexts.tasks.queries import (
    LoadTaskConfigQuery,
    LoadTaskHistoryQuery,
    LoadTaskSprintQuery,
)
from koru.bounded_contexts.tasks.read_model import TaskEventLogProjection
from koru.cqrs import EventSourcingRuntime, runtime_for_project


def test_task_commands_emit_domain_events_and_queries_read_snapshots(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = TaskEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = TaskCommandService(runtime)
    query_service = TaskQueryService()

    created = command_service.create_nl_task(
        CreateNlTaskCommand(
            project=tmp_path,
            text="Add CQRS task intake",
            queue_name="refactor",
            priority="high",
        )
    )

    config = query_service.load_config(
        LoadTaskConfigQuery(
            path=tmp_path / ".planfile" / "config.yaml",
            project_name=tmp_path.name,
        )
    )
    sprint = query_service.load_sprint(
        LoadTaskSprintQuery(path=tmp_path / ".planfile" / "sprints" / "current.yaml")
    )

    assert created.ticket_id == "PLF-001"
    assert config["next_id"] == 2
    assert sprint["sprint"]["tickets"][created.ticket_id]["execution"]["queue"] == "refactor"

    events = runtime.store.all_events(context=TASK_CONTEXT)
    assert [event.event_type for event in events] == [TASK_CREATED]
    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [TASK_CREATED]
    assert projected[0].aggregate_id == created.ticket_id


def test_task_command_emits_reused_event_for_deduped_ticket(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = TaskEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = TaskCommandService(runtime)
    scaffold = {
        "source_tool": "prefact",
        "source_context": {"dedupe_key": "tasks:src/koru/tasks.py"},
        "title": "Split task intake",
    }

    first = command_service.create_nl_task(
        CreateNlTaskCommand(project=tmp_path, text="First", scaffold=scaffold)
    )
    second = command_service.create_nl_task(
        CreateNlTaskCommand(project=tmp_path, text="Second", scaffold=scaffold)
    )

    assert first.ticket_id == second.ticket_id
    assert second.reused is True

    events = runtime.store.all_events(context=TASK_CONTEXT)
    assert [event.event_type for event in events] == [TASK_CREATED, TASK_REUSED]
    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [TASK_CREATED, TASK_REUSED]


def test_task_history_query_reads_persisted_events(tmp_path: Path) -> None:
    runtime = runtime_for_project(tmp_path)
    command_service = TaskCommandService(runtime)
    query_service = TaskQueryService(runtime)

    created = command_service.create_nl_task(
        CreateNlTaskCommand(project=tmp_path, text="Persisted history", queue_name="refactor")
    )

    history = query_service.history(LoadTaskHistoryQuery(ticket_id=created.ticket_id, limit=10))

    assert [entry.event_type for entry in history] == [TASK_CREATED]
    assert history[0].aggregate_id == created.ticket_id