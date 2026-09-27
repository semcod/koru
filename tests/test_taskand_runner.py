"""Tests for the Taskand process runner adapter in the Koru queue system."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from koru.bounded_contexts.planfile_queue.application import PlanfileQueueCommandService
from koru.bounded_contexts.planfile_queue.commands import RunNextPlanfileTaskCommand
from koru.cqrs import EventSourcingRuntime
from koru.queue.runner import _execute_action, _resolve_ticket_action, run_next_planfile_task
from koru.queue.types import TaskandRunResult
from tests._planfile_readiness import runnable_fixture_report


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


def _ok(stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)


def test_resolve_ticket_action_for_taskand_and_process() -> None:
    ticket_proc = {
        "id": "PLF-101",
        "executor": {"kind": "taskand", "handler": "proc://taskand.dev/shell/run/v1"},
        "inputs": {"params": {"cmd": "uptime"}},
    }
    action, missing = _resolve_ticket_action(ticket_proc, "taskand")
    assert missing is not None
    assert action is not None
    assert action["uri"] == "proc://taskand.dev/shell/run/v1"
    assert action["data"] == {"cmd": "uptime"}

    ticket_process = {
        "id": "PLF-102",
        "executor": {"kind": "process"},
        "inputs": {
            "process_uri": "proc://taskand.dev/docker/ps/v1",
            "data": {"all": True},
        },
    }
    action2, _ = _resolve_ticket_action(ticket_process, "process")
    assert action2 is not None
    assert action2["uri"] == "proc://taskand.dev/docker/ps/v1"
    assert action2["data"] == {"all": True}


def test_resolve_ticket_action_taskand_missing_prompt() -> None:
    ticket_empty = {
        "id": "PLF-103",
        "executor": {"kind": "taskand"},
        "inputs": {},
    }
    action, missing = _resolve_ticket_action(ticket_empty, "taskand")
    assert action is None
    assert "missing inputs.process_uri" in missing


def test_execute_action_dispatches_to_taskand_runner(tmp_path: Path) -> None:
    calls = []

    def fake_taskand_runner(action: dict, project: Path) -> TaskandRunResult:
        calls.append((action, project))
        return TaskandRunResult(
            returncode=0,
            stdout='{"ok": true}',
            stderr="",
            status_code=200,
            uri=action["uri"],
            run_id="run-42",
        )

    action = {
        "uri": "proc://taskand.dev/shell/run/v1",
        "data": {"command": "date"},
    }

    result, label = _execute_action(
        "taskand",
        action,
        tmp_path,
        "PLF-104",
        api_runner=lambda *_: _ok(),
        llm_runner=lambda *_: _ok(),
        shell_runner=lambda *_: _ok(),
        taskand_runner=fake_taskand_runner,
    )

    assert len(calls) == 1
    assert calls[0][0] == action
    assert calls[0][1] == tmp_path
    assert result.returncode == 0
    assert "proc://taskand.dev/shell/run/v1" in label


def test_run_next_planfile_task_executes_taskand_ticket_successfully(tmp_path: Path) -> None:
    ticket = {
        "id": "PLF-200",
        "name": "Execute Taskand Pipeline",
        "executor": {"kind": "taskand", "handler": "proc://taskand.dev/pipeline/v1"},
        "inputs": {"input": {"branch": "main"}},
        "execution": {"state": "ready"},
    }

    executed_taskand = []
    planfile_commands = []

    @runnable_fixture_report
    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        args = _ticket_args(command)
        planfile_commands.append(args)
        if args[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def fake_taskand_runner(action: dict, project: Path) -> TaskandRunResult:
        executed_taskand.append(action)
        return TaskandRunResult(
            returncode=0,
            stdout=json.dumps({"ok": True, "output": "success"}),
            stderr="",
            status_code=200,
            uri=action["uri"],
            run_id="taskand-req-99",
        )

    result = run_next_planfile_task(
        project=tmp_path,
        planfile_runner=planfile_runner,
        taskand_runner=fake_taskand_runner,
    )

    assert result.status == "completed"
    assert result.ticket_id == "PLF-200"
    assert result.executor_kind == "taskand"
    assert len(executed_taskand) == 1
    assert executed_taskand[0]["uri"] == "proc://taskand.dev/pipeline/v1"

    done_commands = [cmd for cmd in planfile_commands if cmd[:2] == ["ticket", "done"]]
    assert len(done_commands) == 1
    assert done_commands[0][2] == "PLF-200"


def test_run_next_planfile_task_handles_taskand_failure(tmp_path: Path) -> None:
    ticket = {
        "id": "PLF-201",
        "name": "Failing Taskand Step",
        "executor": {"kind": "taskand", "handler": "proc://taskand.dev/fail/v1"},
        "inputs": {},
        "execution": {"state": "ready", "attempt": 0, "max_attempts": 1},
    }

    planfile_commands = []

    @runnable_fixture_report
    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        args = _ticket_args(command)
        planfile_commands.append(args)
        if args[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def fake_failing_taskand_runner(action: dict, project: Path) -> TaskandRunResult:
        return TaskandRunResult(
            returncode=1,
            stdout="",
            stderr="PROCESS_EXECUTION_FAILED",
            status_code=500,
            uri=action["uri"],
        )

    result = run_next_planfile_task(
        project=tmp_path,
        planfile_runner=planfile_runner,
        taskand_runner=fake_failing_taskand_runner,
    )

    assert result.status == "failed"
    assert result.ticket_id == "PLF-201"
    assert result.executor_kind == "taskand"


def test_cqrs_command_service_taskand_execution(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    command_service = PlanfileQueueCommandService(runtime)

    ticket = {
        "id": "PLF-202",
        "name": "CQRS Taskand Orchestration",
        "executor": {"kind": "taskand"},
        "inputs": {
            "plan": {"steps": [{"name": "step1"}]},
        },
        "execution": {"state": "ready"},
    }

    @runnable_fixture_report
    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        args = _ticket_args(command)
        if args[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def fake_taskand_runner(action: dict, _project: Path) -> TaskandRunResult:
        return TaskandRunResult(
            returncode=0,
            stdout='{"ok": true, "status": "SUCCEEDED"}',
            stderr="",
            status_code=200,
            uri="proc://taskand.dev/orchestrator/execute/v1",
            run_id="orch-cqrs-1",
        )

    cmd = RunNextPlanfileTaskCommand(
        project=tmp_path,
        planfile_runner=planfile_runner,
        taskand_runner=fake_taskand_runner,
    )
    res = command_service.run_next_task(cmd)
    assert res.status == "completed"
    assert res.ticket_id == "PLF-202"
    assert res.executor_kind == "taskand"
