"""Native readiness must precede ticket lifecycle and executor effects."""

import json
import sys
from types import SimpleNamespace

import pytest
from planfile import Planfile

from koru.queue.admission import admitted_payload
from koru.queue.runner import run_next_planfile_task


def result(payload, returncode=0):
    return SimpleNamespace(returncode=returncode, stdout=json.dumps(payload), stderr="")


@pytest.mark.parametrize("report", [None, {}, [], {"servable": "PLF-001"}, {"servable": [None]}])
def test_invalid_report_never_claims_or_executes(tmp_path, report):
    calls = []
    ticket = {"id": "PLF-001", "status": "open", "executor": {"kind": "shell", "handler": "false"}}

    def runner(command, project):
        args = command[command.index("ticket"):]
        calls.append(args)
        return result([ticket] if args[1] == "list" else report)

    execution = []
    outcome = run_next_planfile_task(
        project=tmp_path, planfile_runner=runner,
        shell_runner=lambda *args: execution.append(args),
    )
    assert outcome.status == "planfile_error"
    assert [args[1] for args in calls] == ["list", "next"]
    assert execution == []


def test_unavailable_native_report_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="readiness query failed"):
        admitted_payload(tmp_path, '[{"id":"PLF-001"}]', queue_name=None,
                         runner=lambda *args: result(None, returncode=2))


def test_disappearing_planfile_command_is_reported_without_execution(tmp_path):
    def unavailable(*args):
        raise FileNotFoundError("Planfile launcher vanished")

    with pytest.raises(ValueError, match="readiness query unavailable"):
        admitted_payload(tmp_path, '[{"id":"PLF-001"}]', queue_name=None, runner=unavailable)


@pytest.mark.parametrize("single", [False, True])
def test_explicit_target_cannot_bypass_native_readiness(tmp_path, single):
    ticket = {"id": "PLF-002", "status": "open", "blocked_by": ["PLF-001"]}
    calls = []

    def runner(command, project):
        args = command[command.index("ticket"):]
        calls.append(args)
        return result((ticket if single else [ticket]) if args[1] == "list" else {"servable": []})

    outcome = run_next_planfile_task(project=tmp_path, target_ticket_id="PLF-002", planfile_runner=runner)
    assert outcome.status == "target_not_runnable"
    assert [args[1] for args in calls] == ["list", "next"]


def native_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KORU_PLANFILE_CMD", f"{sys.executable} -m planfile.cli")
    monkeypatch.setenv("KORU_PLANFILE_SYNC", "0")
    monkeypatch.delenv("PLANFILE_NO_AUTONOMY_FILTER", raising=False)
    monkeypatch.delenv("CURRENT_GOAL", raising=False)
    return Planfile(str(tmp_path))


def shell_ticket(store, name, **kwargs):
    return store.create_ticket(name, executor={"kind": "shell", "mode": "automatic"},
                               inputs={"script": "echo local-pilot"}, **kwargs)




@pytest.mark.parametrize("kwargs", [
    {"blocked_by": ["PLF-999"]},
    {"execution": {"state": "waiting_input"}},
    {"labels": ["autonomy-frontier"]},
    {"labels": ["waiting:resource"]},
])
def test_native_waits_leave_ticket_unclaimed(tmp_path, monkeypatch, kwargs):
    store = native_store(tmp_path, monkeypatch)
    ticket = shell_ticket(store, "must wait", **kwargs)
    executed = []
    outcome = run_next_planfile_task(project=tmp_path, shell_runner=lambda *args: executed.append(args))
    assert outcome.status == "idle"
    assert executed == []
    unchanged = Planfile(str(tmp_path)).get_ticket(ticket.id)
    assert unchanged.status.value == "open"
    assert unchanged.execution is None or unchanged.execution.assigned_to is None
