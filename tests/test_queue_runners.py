from __future__ import annotations

import sys
from pathlib import Path

from koru.queue.runners import run_process


def test_run_process_falls_back_to_preferred_encoding(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.queue.runners.locale.getpreferredencoding", lambda _do_setlocale: "cp1250")

    result = run_process(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write('fóó'.encode('cp1250')); "
                "sys.stderr.buffer.write('błąd'.encode('cp1250'))"
            ),
        ],
        tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "fóó"
    assert result.stderr == "błąd"


def test_run_process_prefers_utf8_before_locale_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.queue.runners.locale.getpreferredencoding", lambda _do_setlocale: "cp1250")

    result = run_process(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write('żółw'.encode('utf-8')); "
                "sys.stderr.buffer.write('zażółć'.encode('utf-8'))"
            ),
        ],
        tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "żółw"
    assert result.stderr == "zażółć"


def test_ticket_taskand_request_parsing() -> None:
    from koru.queue.ticket import ticket_taskand_request

    # Missing uri and plan -> None
    assert ticket_taskand_request({}) is None
    assert ticket_taskand_request({"executor": {"kind": "taskand"}}) is None

    # Via executor.handler
    req1 = ticket_taskand_request({
        "executor": {"kind": "taskand", "handler": "proc://taskand.dev/shell/run/v1"},
        "inputs": {"input": {"command": "ls"}},
    })
    assert req1 is not None
    assert req1["uri"] == "proc://taskand.dev/shell/run/v1"
    assert req1["data"] == {"command": "ls"}
    assert req1["plan"] is None

    # Via inputs.plan (orchestrator DAG)
    req2 = ticket_taskand_request({
        "executor": {"kind": "taskand"},
        "inputs": {
            "plan": {"steps": [{"name": "s1", "process": "proc://taskand.dev/test/v1"}]},
            "run_id": "run-test-1",
        },
    })
    assert req2 is not None
    assert req2["plan"] == {"steps": [{"name": "s1", "process": "proc://taskand.dev/test/v1"}]}
    assert req2["run_id"] == "run-test-1"


class _MockHttpResponse:
    def __init__(self, data: bytes, status: int = 200):
        self.data = data
        self.status = status
        self.headers = {}

    def read(self, *args):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_run_taskand_request_http_proc_success(monkeypatch, tmp_path: Path) -> None:
    from urllib.error import HTTPError

    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/healthz" in url:
            return _MockHttpResponse(b"OK", 200)
        if "/api/proc/call" in url:
            body = b'{"ok": true, "requestId": "req-123", "result": {"reply": "executed"}}'
            return _MockHttpResponse(body, 200)
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)

    res = run_taskand_request(
        {
            "uri": "proc://taskand.dev/shell/run/v1",
            "data": {"command": "echo test"},
            "gateway_url": "http://127.0.0.1:8077",
        },
        tmp_path,
    )
    assert res.returncode == 0
    assert res.status_code == 200
    assert res.uri == "proc://taskand.dev/shell/run/v1"
    assert res.run_id == "req-123"
    assert res.data == {"reply": "executed"}


def test_run_taskand_request_http_orchestrator_success(monkeypatch, tmp_path: Path) -> None:
    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/healthz" in url:
            return _MockHttpResponse(b"OK", 200)
        if "/api/orchestrator" in url:
            body = b'{"ok": true, "result": {"runId": "orch-abc", "status": "SUCCEEDED", "summary": ["step1 ok"]}}'
            return _MockHttpResponse(body, 200)
        raise RuntimeError(f"Unexpected url: {url}")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)

    res = run_taskand_request(
        {
            "plan": {"goal": "test DAG", "steps": []},
            "run_id": "orch-abc",
            "gateway_url": "http://127.0.0.1:8077",
        },
        tmp_path,
    )
    assert res.returncode == 0
    assert res.status_code == 200
    assert res.run_id == "orch-abc"
    assert res.uri == "proc://taskand.dev/orchestrator/execute/v1"


def test_run_taskand_request_cli_fallback(monkeypatch, tmp_path: Path) -> None:
    import subprocess

    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        raise ConnectionRefusedError("Gateway offline")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)
    fake_cli = tmp_path / "bin" / "taskand"
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("#!/bin/sh\nexit 0\n")
    fake_cli.chmod(0o755)

    monkeypatch.setenv("TASKAND_BIN", str(fake_cli))

    def mock_run_captured(cmd, cwd=None, env=None, shell=False):
        return subprocess.CompletedProcess(
            cmd, 0, '{"ok": true, "requestId": "cli-req", "reply": "local cli ok"}', ""
        )

    monkeypatch.setattr("koru.queue.runners._run_captured_subprocess", mock_run_captured)

    res = run_taskand_request(
        {
            "uri": "proc://taskand.dev/shell/run/v1",
            "data": {"cmd": "hello"},
        },
        tmp_path,
    )
    assert res.returncode == 0
    assert res.run_id == "cli-req"


def test_run_taskand_request_missing_uri_or_plan(monkeypatch, tmp_path: Path) -> None:
    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/healthz" in url:
            return _MockHttpResponse(b"OK", 200)
        raise RuntimeError(f"Unexpected url: {url}")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)

    res = run_taskand_request({"gateway_url": "http://127.0.0.1:8077"}, tmp_path)
    assert res.returncode == 1
    assert res.status_code == 400
    assert res.stderr == "Missing uri or plan in taskand request"
    assert res.uri == ""


def test_run_taskand_request_gateway_and_cli_unavailable(monkeypatch, tmp_path: Path) -> None:
    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        raise ConnectionRefusedError("Gateway offline")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("koru.queue.runners._find_taskand_cli", lambda _project: None)

    res = run_taskand_request(
        {"uri": "proc://taskand.dev/shell/run/v1", "gateway_url": "http://127.0.0.1:8077"},
        tmp_path,
    )
    assert res.returncode == 1
    assert res.status_code == 503
    assert "Taskand gateway unavailable" in res.stderr
    assert res.uri == "proc://taskand.dev/shell/run/v1"


def test_run_taskand_request_http_orchestrator_failure(monkeypatch, tmp_path: Path) -> None:
    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/healthz" in url:
            return _MockHttpResponse(b"OK", 200)
        if "/api/orchestrator" in url:
            body = b'{"ok": true, "result": {"runId": "orch-fail", "status": "FAILED"}}'
            return _MockHttpResponse(body, 200)
        raise RuntimeError(f"Unexpected url: {url}")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)

    res = run_taskand_request(
        {
            "plan": {"goal": "failing DAG", "steps": []},
            "gateway_url": "http://127.0.0.1:8077",
        },
        tmp_path,
    )
    assert res.returncode == 1
    assert res.run_id == "orch-fail"
    assert res.stderr == "Orchestrator finished with status: FAILED"


def test_run_taskand_request_cli_invalid_json(monkeypatch, tmp_path: Path) -> None:
    import subprocess

    from koru.queue.runners import run_taskand_request

    def mock_urlopen(req, timeout=None):
        raise ConnectionRefusedError("Gateway offline")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)
    fake_cli = tmp_path / "bin" / "taskand"
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("#!/bin/sh\nexit 0\n")
    fake_cli.chmod(0o755)
    monkeypatch.setenv("TASKAND_BIN", str(fake_cli))

    def mock_run_captured(cmd, cwd=None, env=None, shell=False):
        return subprocess.CompletedProcess(cmd, 3, "not-json", "")

    monkeypatch.setattr("koru.queue.runners._run_captured_subprocess", mock_run_captured)

    res = run_taskand_request(
        {
            "uri": "proc://taskand.dev/shell/run/v1",
            "data": {"cmd": "hello"},
        },
        tmp_path,
    )
    assert res.returncode == 3
    assert res.status_code == 500
    assert res.stderr == "Invalid JSON output from taskand CLI"


def test_normalize_taskand_plan() -> None:
    from koru.queue.runners import normalize_taskand_plan

    raw_plan = {
        "goal": "Test goal",
        "steps": [
            {
                "id": "1",
                "uri": "proc://taskand.dev/hw/monitor/v1",
                "inputs": {"sample": True},
            },
            {
                "name": "custom_step",
                "process": "proc://taskand.dev/cluster/monitor/v1",
                "deps": "step_1",
                "input": {"depth": 2},
            },
        ],
    }

    norm = normalize_taskand_plan(raw_plan)
    assert norm["goal"] == "Test goal"
    assert len(norm["steps"]) == 2

    s1 = norm["steps"][0]
    assert s1["id"] == 1
    assert s1["name"] == "step_1"
    assert s1["process"] == "proc://taskand.dev/hw/monitor/v1"
    assert s1["deps"] == []
    assert s1["params"] == {"sample": True}

    s2 = norm["steps"][1]
    assert s2["id"] == 2
    assert s2["name"] == "custom_step"
    assert s2["process"] == "proc://taskand.dev/cluster/monitor/v1"
    assert s2["deps"] == ["step_1"]
    assert s2["params"] == {"depth": 2}


def test_run_taskand_request_sends_normalized_plan(monkeypatch, tmp_path: Path) -> None:
    import json

    from koru.queue.runners import run_taskand_request

    sent_body = {}

    def mock_urlopen(req, timeout=None):
        nonlocal sent_body
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/healthz" in url:
            return _MockHttpResponse(b"OK", 200)
        if "/api/orchestrator" in url:
            sent_body = json.loads(req.data.decode("utf-8"))
            body = b'{"ok": true, "result": {"runId": "orch-norm", "status": "SUCCEEDED"}}'
            return _MockHttpResponse(body, 200)
        raise RuntimeError(f"Unexpected url: {url}")

    monkeypatch.setattr("koru.queue.runners.urllib.request.urlopen", mock_urlopen)

    res = run_taskand_request(
        {
            "plan": {
                "steps": [
                    {"id": "42", "uri": "proc://taskand.dev/hw/monitor/v1"}
                ]
            },
            "gateway_url": "http://127.0.0.1:8077",
        },
        tmp_path,
    )
    assert res.returncode == 0
    assert "plan" in sent_body
    norm_step = sent_body["plan"]["steps"][0]
    assert norm_step["id"] == 42
    assert norm_step["process"] == "proc://taskand.dev/hw/monitor/v1"
    assert norm_step["params"] == {}
    assert norm_step["deps"] == []


def test_finalize_ticket_appends_taskand_evidence(monkeypatch, tmp_path: Path) -> None:
    from types import SimpleNamespace

    from koru.queue.runner import _finalize_ticket
    from koru.queue.shell_evidence import TASKAND_RUN_NOTE_TAG
    from koru.queue.types import TaskandRunResult

    recorded_tags = []

    def mock_append_evidence(project, ticket_id, result, planfile_runner, tag=None):
        recorded_tags.append(tag)

    ok_reply = SimpleNamespace(returncode=0, stdout="{}", stderr="")
    empty_reply = SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr("koru.queue.runner._append_shell_evidence", mock_append_evidence)
    monkeypatch.setattr("koru.queue.runner.planfile_lifecycle_command", lambda *args, **kwargs: ok_reply)
    monkeypatch.setattr("koru.queue.runner.update_living_status", lambda *args, **kwargs: None)

    res = _finalize_ticket(
        project=tmp_path,
        ticket={"id": "T-1", "executor": {"kind": "taskand"}},
        ticket_id="T-1",
        executor_kind="taskand",
        result=TaskandRunResult(returncode=0, stdout='{"ok": true}', stderr=""),
        action_label="taskand proc://hw",
        actor="koru",
        planfile_runner=lambda *args, **kwargs: empty_reply,
    )
    assert res.status == "completed"
    assert recorded_tags == [TASKAND_RUN_NOTE_TAG]


