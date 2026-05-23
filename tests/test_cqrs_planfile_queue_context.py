from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from koru.bounded_contexts.planfile_queue.application import (
    PlanfileQueueCommandService,
    PlanfileQueueQueryService,
)
from koru.bounded_contexts.planfile_queue.commands import RunNextPlanfileTaskCommand
from koru.bounded_contexts.planfile_queue.events import (
    PLANFILE_QUEUE_CONTEXT,
    PLANFILE_QUEUE_IDLE,
    PLANFILE_QUEUE_TASK_COMPLETED,
)
from koru.bounded_contexts.planfile_queue.queries import (
    LoadNextRunnableTicketQuery,
    LoadPlanfileQueueHistoryQuery,
)
from koru.bounded_contexts.planfile_queue.read_model import PlanfileQueueEventLogProjection
from koru.cqrs import EventSourcingRuntime, runtime_for_project


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


def _ok(stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)


def test_planfile_queue_command_emits_completed_event_and_query_reads_ticket(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = PlanfileQueueEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = PlanfileQueueCommandService(runtime)
    query_service = PlanfileQueueQueryService()
    ticket = {
        "id": "PLF-001",
        "name": "Run bootstrap",
        "executor": {"kind": "shell", "handler": "echo ok"},
        "execution": {"state": "ready"},
    }

    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def shell_runner(command: str, _project: Path) -> SimpleNamespace:
        assert command == "echo ok"
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    next_ticket = query_service.load_next_runnable_ticket(
        LoadNextRunnableTicketQuery(project=tmp_path, planfile_runner=planfile_runner)
    )
    result = command_service.run_next_task(
        RunNextPlanfileTaskCommand(
            project=tmp_path,
            actor="koru-test",
            planfile_runner=planfile_runner,
            shell_runner=shell_runner,
        )
    )

    assert next_ticket is not None
    assert next_ticket["id"] == "PLF-001"
    assert result.status == "completed"
    assert result.ticket_id == "PLF-001"

    events = runtime.store.all_events(context=PLANFILE_QUEUE_CONTEXT)
    assert [event.event_type for event in events] == [PLANFILE_QUEUE_TASK_COMPLETED]
    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [PLANFILE_QUEUE_TASK_COMPLETED]
    assert projected[0].aggregate_id == "PLF-001"


def test_planfile_queue_command_emits_idle_event_when_no_ticket(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = PlanfileQueueEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = PlanfileQueueCommandService(runtime)

    def planfile_runner(_command: list[str], _project: Path) -> SimpleNamespace:
        return _ok("No runnable ticket found")

    result = command_service.run_next_task(
        RunNextPlanfileTaskCommand(project=tmp_path, planfile_runner=planfile_runner)
    )

    assert result.status == "idle"

    events = runtime.store.all_events(context=PLANFILE_QUEUE_CONTEXT)
    assert [event.event_type for event in events] == [PLANFILE_QUEUE_IDLE]
    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [PLANFILE_QUEUE_IDLE]


def test_planfile_queue_history_query_reads_persisted_events(tmp_path: Path) -> None:
    runtime = runtime_for_project(tmp_path)
    command_service = PlanfileQueueCommandService(runtime)
    query_service = PlanfileQueueQueryService(runtime)
    ticket = {
        "id": "PLF-777",
        "name": "Persist queue history",
        "executor": {"kind": "shell", "handler": "echo ok"},
        "execution": {"state": "ready"},
    }

    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def shell_runner(_command: str, _project: Path) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    result = command_service.run_next_task(
        RunNextPlanfileTaskCommand(
            project=tmp_path,
            planfile_runner=planfile_runner,
            shell_runner=shell_runner,
        )
    )

    history = query_service.history(LoadPlanfileQueueHistoryQuery(ticket_id="PLF-777", limit=10))

    assert result.status == "completed"
    assert [entry.event_type for entry in history] == [PLANFILE_QUEUE_TASK_COMPLETED]
    assert history[0].aggregate_id == "PLF-777"