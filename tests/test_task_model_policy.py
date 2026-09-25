from __future__ import annotations

import json
import subprocess
from unittest.mock import Mock

import pytest

from koru.task_model_policy import drive_with_model_policy, load_routing_task, select_task_model

ENV = {"KORU_TILLM_MODEL": "zai/glm-5.3", "KORU_TILLM_SIMPLE_MODEL": "zai/glm-5.3-flash"}


def lint_task():
    return {
        "id": "TEST-1",
        "files": ["src/example.py"],
        "labels": ["ruff"],
        "inputs": {"llm_task_kind": "lint_fix", "ruff_codes": ["F401"]},
    }


def choose(task, **kwargs):
    return select_task_model(task, client_id="opencode", environ=ENV, **kwargs)


def test_bounded_lint_uses_configured_model():
    assert choose(lint_task()) == {"model": "zai/glm-5.3-flash", "reason": "bounded_lint"}


@pytest.mark.parametrize(
    "patch",
    [
        {"files": []},
        {"files": ["src/a.py", "src/b.py"]},
        {"files": ["../src/a.py"]},
        {"files": ["/src/a.py"]},
        {"files": ["src/*.py"]},
        {"files": [".governance/check.py"]},
        {"files": ["src/../a.py"]},
        {"files": ["src\\a.py"]},
        {"files": [None]},
        {"labels": ["refactor"]},
        {"labels": ["code2llm"]},
        {"labels": ["security"]},
        {"inputs": {"llm_task_kind": "lint_fix", "ruff_codes": ["F821"]}},
        {"inputs": {"llm_task_kind": "lint_fix", "ruff_codes": ["F401", "C901"]}},
        {"inputs": {"llm_task_kind": "lint_fix", "ruff_codes": []}},
        {"inputs": {"llm_task_kind": "lint_fix", "ruff_codes": [None]}},
        {"inputs": {"llm_task_kind": "refactor", "ruff_codes": ["F401"]}},
    ],
)
def test_unknown_or_complex_scope_stays_on_default(patch):
    assert choose({**lint_task(), **patch})["model"] == "zai/glm-5.3"


def test_labels_titles_and_priority_alone_cannot_downgrade():
    assert choose({"name": "Simple Ruff F401 fix", "labels": ["ruff"], "priority": "low"})["model"] == "zai/glm-5.3"


def test_opt_in_client_and_explicit_pins():
    task = lint_task()
    assert select_task_model(task, client_id="opencode", environ={"KORU_TILLM_MODEL": "base"})["model"] == "base"
    assert select_task_model(task, client_id="claude-code", environ=ENV)["model"] == "zai/glm-5.3"
    assert choose(task, explicit_model="operator/model")["reason"] == "explicit_request"
    assert choose({**task, "inputs": {**task["inputs"], "llm_model": "ticket/model"}})["model"] == "ticket/model"
    assert (
        select_task_model(task, client_id="opencode", environ={**ENV, "KORU_TILLM_FORCE_MODEL": "pin/model"})["model"]
        == "pin/model"
    )


def test_real_queue_adapter_passes_flash_and_writes_honest_receipt(tmp_path, monkeypatch):
    from koru.queue.runners import run_shell_llm_request
    from koru.queue.ticket import ticket_llm_request

    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("KORU_TILLM_FORCE_MODEL", raising=False)
    drive = Mock(return_value={"ok": True, "exit_code": 0, "stdout": "sensitive response"})
    monkeypatch.setattr("koru.tillm_bridge.drive_shell_chat", drive)
    result = run_shell_llm_request(
        ticket_llm_request({**lint_task(), "description": "sensitive prompt"}), tmp_path, "opencode"
    )
    assert drive.call_args.kwargs["model"] == "zai/glm-5.3-flash"
    assert result.model == "zai/glm-5.3-flash"
    text = (tmp_path / ".planfile/.koru/model-routing.jsonl").read_text()
    rows = [json.loads(x) for x in text.splitlines()]
    assert [x["status"] for x in rows] == ["started", "cli_success"]
    assert all(x["ticket"] == "TEST-1" for x in rows)
    assert "sensitive" not in text and "observed_model" not in text


def test_autonomous_shell_adapter_uses_same_policy(tmp_path, monkeypatch):
    from koru.autonomy.cycle.cycle_drive_retry import _drive_shell_client

    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("KORU_TILLM_FORCE_MODEL", raising=False)
    drive = Mock(return_value={"ok": True})
    monkeypatch.setattr("koru.tillm_bridge.drive_shell_chat", drive)
    _, ok = _drive_shell_client("opencode", prompt="lint", project=tmp_path, task=lint_task())
    assert ok and drive.call_args.kwargs["model"] == "zai/glm-5.3-flash"


def test_logging_failure_does_not_repeat_call(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.model_history.append_routing_event", lambda *args: False)
    drive = Mock(return_value={"ok": True})
    result = drive_with_model_policy(drive, project=tmp_path, client_id="opencode", prompt="private")
    assert result["ok"] and not result["model_routing"]["recorded"]
    drive.assert_called_once()


def test_failed_call_is_recorded_without_exception_contents(tmp_path):
    drive = Mock(side_effect=RuntimeError("private token"))
    with pytest.raises(RuntimeError):
        drive_with_model_policy(drive, project=tmp_path, client_id="opencode", prompt="private")
    text = (tmp_path / ".planfile/.koru/model-routing.jsonl").read_text()
    assert json.loads(text.splitlines()[-1])["status"] == "error"
    assert "private" not in text


def test_task_probe_is_bounded_and_rejects_mismatched_id(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.queue.ticket.resolve_planfile_base_command", lambda p: ["planfile"])
    run = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(lint_task())))
    monkeypatch.setattr("koru.task_model_policy.subprocess.run", run)
    assert load_routing_task(tmp_path, "TEST-1") == lint_task()
    assert run.call_args.kwargs["timeout"] == 8
    assert load_routing_task(tmp_path, "OTHER-1") == {}
    run.side_effect = subprocess.TimeoutExpired("planfile", 8)
    assert load_routing_task(tmp_path, "TEST-1") == {}


@pytest.mark.parametrize("labels", ["ruff", [None], ["security"], ["governance"]])
def test_malformed_or_sensitive_labels_keep_regular_model(labels):
    assert choose({**lint_task(), "labels": labels})["model"] == "zai/glm-5.3"


def test_nonzero_exit_is_not_logged_as_success(tmp_path):
    drive_with_model_policy(
        Mock(return_value={"ok": True, "exit_code": 2}), project=tmp_path, client_id="opencode", task=[]
    )
    row = json.loads((tmp_path / ".planfile/.koru/model-routing.jsonl").read_text().splitlines()[-1])
    assert row["status"] == "error"


def test_ticket_model_pin_is_cli_only(tmp_path, monkeypatch):
    from koru.queue.runners import run_shell_llm_request
    from koru.queue.ticket import ticket_llm_request

    request = ticket_llm_request({**lint_task(), "name": "lint", "inputs": {"llm_model": "operator/pin"}})
    assert "model" not in request  # HTTP model policy belongs to SubLLM.
    drive = Mock(return_value={"ok": True, "exit_code": 0})
    monkeypatch.setattr("koru.tillm_bridge.drive_shell_chat", drive)
    run_shell_llm_request(request, tmp_path, "opencode")
    assert drive.call_args.kwargs["model"] == "operator/pin"


def test_autonomous_ticket_metadata_reaches_real_shell_adapter(tmp_path, monkeypatch):
    from koru.autonomy.cycle import cycle_drive_retry as module
    from koru.autonomy.state import AutoloopState
    from koru.queue import QueueLoopResult

    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("KORU_TILLM_CLIENT", "opencode")
    monkeypatch.delenv("KORU_TILLM_FORCE_MODEL", raising=False)
    decision = Mock(skip=False, kind="ticket_prompt", prompt="lint TEST-1")
    monkeypatch.setattr(module, "_resolve_autopilot_drive_decision", lambda *a, **k: (decision, None))
    monkeypatch.setattr(module, "_resolve_drive_plugin_requirement", lambda *a: False)
    monkeypatch.setattr(module, "_active_decision_engine", lambda *a: None)
    probe = Mock(return_value=lint_task())
    monkeypatch.setattr("koru.task_model_policy.load_routing_task", probe)
    drive = Mock(return_value={"ok": True, "exit_code": 0})
    monkeypatch.setattr("koru.tillm_bridge.drive_shell_chat", drive)
    queue = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["TEST-1"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="TEST-1",
    )
    _, ok, _, _ = module._execute_autopilot_drive(
        project=tmp_path,
        state=AutoloopState(),
        queue_result=queue,
        client=Mock(),
        autopilot_ide="opencode",
        drive_prompt="lint TEST-1",
        submit=True,
        autopilot_action="drive",
        _hp=lambda *a: None,
    )
    probe.assert_called_once_with(tmp_path, "TEST-1")
    assert ok and drive.call_args.kwargs["model"] == "zai/glm-5.3-flash"


def test_planfile_context_contract_survives_input_projection(tmp_path, monkeypatch):
    from koru.queue.runners import run_shell_llm_request
    from koru.queue.ticket import ticket_llm_request
    task = lint_task()
    task["source"] = {"tool": "ruff", "context": {"model_routing": task.pop("inputs")}}
    task["name"] = "lint"
    assert choose(task)["model"] == "zai/glm-5.3-flash"
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("KORU_TILLM_FORCE_MODEL", raising=False)
    drive = Mock(return_value={"ok": True, "exit_code": 0})
    monkeypatch.setattr("koru.tillm_bridge.drive_shell_chat", drive)
    run_shell_llm_request(ticket_llm_request(task), tmp_path, "opencode")
    assert drive.call_args.kwargs["model"] == "zai/glm-5.3-flash"
