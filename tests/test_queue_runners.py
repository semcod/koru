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


