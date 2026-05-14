from __future__ import annotations

import subprocess
from pathlib import Path

from koru import mcp_server


def test_initialize_message_returns_server_info() -> None:
    response = mcp_server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "koru"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_includes_required_koru_tools() -> None:
    response = mcp_server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    assert response is not None
    tools = response["result"]["tools"]
    names = {item["name"] for item in tools}
    assert {
        "koru_list_tickets",
        "koru_run_ticket",
        "koru_job_status",
        "koru_run_quality_gates",
        "koru_propose_edits",
    }.issubset(names)


def test_tools_call_unknown_tool_returns_error_payload() -> None:
    response = mcp_server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_tool_job_status_unknown_job() -> None:
    payload = mcp_server.tool_job_status({"job_id": "JOB-DOES-NOT-EXIST"})
    assert payload["status"] == "not_found"
    assert payload["job_id"] == "JOB-DOES-NOT-EXIST"


def test_run_ticket_invokes_queue_mode_without_ticket_flag(monkeypatch, tmp_path: Path) -> None:
    called: dict[str, list[str]] = {}

    def _fake_run(cmd, **kwargs):
        called["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(mcp_server.subprocess, "run", _fake_run)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-123",
            "mode": "dry",
            "max_steps": 2,
        }
    )

    assert result["status"] == "success"
    assert "cmd" in called
    assert "--queue" in called["cmd"]
    assert "--dry-run" in called["cmd"]
    assert "--ticket" not in called["cmd"]


def test_run_ticket_timeout_updates_job_status(monkeypatch, tmp_path: Path) -> None:
    def _fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(mcp_server.subprocess, "run", _fake_run)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-TIMEOUT",
            "mode": "apply",
        }
    )

    assert result["status"] == "timeout"
    assert "timed out" in result["logs"][0]

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "timeout"
    assert status_payload["current_step"] == "timeout"


def test_run_ticket_error_updates_job_status(monkeypatch, tmp_path: Path) -> None:
    def _fake_run(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(mcp_server.subprocess, "run", _fake_run)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-ERROR",
            "mode": "apply",
        }
    )

    assert result["status"] == "error"
    assert result["error"] == "boom"

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "error"
    assert status_payload["current_step"] == "error"
