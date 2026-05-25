from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from koru import mcp_server


def test_initialize_message_returns_server_info() -> None:
    response = mcp_server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "koru"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_includes_required_koru_tools() -> None:
    response = mcp_server.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )

    assert response is not None
    tools = response["result"]["tools"]
    names = {item["name"] for item in tools}
    assert {
        "koru_list_tickets",
        "koru_run_ticket",
        "koru_job_status",
        "koru_run_quality_gates",
        "koru_propose_edits",
        "koru_ide_command_catalog",
        "koru_ide_command_scenario_schema",
        "koru_validate_ide_command_scenario",
        "koru_ide_commands",
        "koru_ide_drive",
        "koru_ide_dsl_recent",
        "koru_strategy_prompt",
    }.issubset(names)


def test_tools_call_unknown_tool_returns_error_payload() -> None:
    response = mcp_server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        },
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_tool_job_status_unknown_job() -> None:
    payload = mcp_server.tool_job_status({"job_id": "JOB-DOES-NOT-EXIST"})
    assert payload["status"] == "not_found"
    assert payload["job_id"] == "JOB-DOES-NOT-EXIST"


def test_tool_ide_command_catalog_for_llm() -> None:
    payload = mcp_server.tool_ide_command_catalog({"ide": "cursor", "for_llm": True})

    assert set(payload["catalog"]["ides"]) == {"cursor"}
    assert "submit" in payload["catalog"]["ides"]["cursor"]["categories"]


def test_tool_validate_ide_command_scenario() -> None:
    payload = mcp_server.tool_validate_ide_command_scenario(
        {
            "scenario": {
                "ide": "windsurf",
                "steps": [{"action": "atomic_send", "command": "windsurf.sendTextToChat"}],
            },
        },
    )

    assert payload["ok"] is True
    assert payload["validation"]["normalized"]["ide"] == "windsurf"


def test_run_ticket_invokes_queue_mode_without_ticket_flag(monkeypatch, tmp_path: Path) -> None:
    called: dict[str, list[str]] = {}

    def _fake_popen(cmd, **kwargs):
        called["cmd"] = list(cmd)

        # Return a mock Popen object with communicate() returning success
        class MockPopen:
            def communicate(self, timeout=None):
                return "ok", ""

            def poll(self):
                return 0

            returncode = 0
            pid = 12345

        return MockPopen()

    monkeypatch.setattr(mcp_server.subprocess, "Popen", _fake_popen)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-123",
            "mode": "dry",
            "max_steps": 2,
        },
    )

    assert result["status"] == "success"
    assert "cmd" in called
    assert "--queue" in called["cmd"]
    assert "--dry-run" in called["cmd"]
    assert "--ticket" not in called["cmd"]


def test_run_ticket_timeout_updates_job_status(monkeypatch, tmp_path: Path) -> None:
    def _fake_popen(cmd, **kwargs):
        # Return a mock Popen object that raises TimeoutExpired on communicate()
        class MockPopen:
            def __init__(self):
                self.killed = False

            def communicate(self, timeout=None):
                if self.killed:
                    return "", ""
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

            def kill(self):
                self.killed = True

            def poll(self):
                return None

            pid = 12345

        return MockPopen()

    monkeypatch.setattr(mcp_server.subprocess, "Popen", _fake_popen)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-TIMEOUT",
            "mode": "apply",
        },
    )

    assert result["status"] == "timeout"
    assert "timed out" in result["logs"][0]

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "timeout"
    assert status_payload["current_step"] == "timeout"


def test_run_ticket_error_updates_job_status(monkeypatch, tmp_path: Path) -> None:
    def _fake_popen(cmd, **kwargs):
        # Return a mock Popen object that raises exception on communicate()
        class MockPopen:
            def communicate(self, timeout=None):
                raise RuntimeError("boom")

            def poll(self):
                return None

            pid = 12345

        return MockPopen()

    monkeypatch.setattr(mcp_server.subprocess, "Popen", _fake_popen)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-ERROR",
            "mode": "apply",
        },
    )

    assert result["status"] == "error"
    assert result["error"] == "boom"

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "error"
    assert status_payload["current_step"] == "error"


def test_regix_gate_command_uses_workdir_not_project(tmp_path: Path) -> None:
    """Verify regix command uses --workdir flag instead of --project."""
    gate_commands = mcp_server._gate_commands(tmp_path)

    assert "regix" in gate_commands
    regix_cmd = gate_commands["regix"]
    assert regix_cmd[0] == "regix"
    assert regix_cmd[1] == "gates"
    assert "--workdir" in regix_cmd
    assert str(tmp_path) in regix_cmd
    assert "--project" not in regix_cmd


def test_redup_gate_command_uses_supported_cli_shape(tmp_path: Path) -> None:
    gate_commands = mcp_server._gate_commands(tmp_path)

    assert gate_commands["redup"] == [
        sys.executable,
        "-m",
        "redup",
        "check",
        str(tmp_path),
        "--min-lines",
        "10",
    ]


def test_job_store_is_ephemeral_across_imports(tmp_path: Path) -> None:
    """Demonstrate that job store is in-memory and lost across module reloads."""
    # Create a job in the current module state
    from koru import mcp_server as mcp1

    job_id = mcp1._create_job("TEST-001", "apply", tmp_path)
    mcp1._update_job(job_id, tmp_path, status="running", progress=0.5)

    # Verify job exists in current state
    status = mcp1.tool_job_status({"job_id": job_id})
    assert status["status"] == "running"
    assert status["progress"] == 0.5

    # Clear the job store to simulate process restart
    mcp1._jobs.clear()

    # Job is now lost
    status_after_clear = mcp1.tool_job_status({"job_id": job_id})
    assert status_after_clear["status"] == "not_found"
    assert "Unknown job" in status_after_clear["error"]


def test_tool_ide_dsl_recent_reads_persisted_file(tmp_path: Path) -> None:
    dsl_path = tmp_path / ".planfile" / ".koru" / "dsl_recent.json"
    dsl_path.parent.mkdir(parents=True, exist_ok=True)
    dsl_path.write_text(
        '{"lines": ["#001 act=paste ok=true", "#999 act=drive ok=false"]}',
        encoding="utf-8",
    )
    payload = mcp_server.tool_ide_dsl_recent(
        {"project_root": str(tmp_path), "limit": 5},
    )
    assert payload["count"] == 2
    assert "#001" in payload["lines"][0]


def test_job_store_persists_to_disk_and_reloads(tmp_path: Path) -> None:
    """Demonstrate that job store persists to disk and can be reloaded."""
    from koru import mcp_server as mcp1

    # Create a job with a specific project
    job_id = mcp1._create_job("TEST-PERSIST-001", "apply", tmp_path)
    mcp1._update_job(job_id, tmp_path, status="running", progress=0.7)

    # Verify job exists in current state
    status = mcp1.tool_job_status({"job_id": job_id})
    assert status["status"] == "running"
    assert status["progress"] == 0.7

    # Clear in-memory store
    mcp1._jobs.clear()

    # Reload from disk
    reloaded_jobs = mcp1._load_jobs(tmp_path)
    assert job_id in reloaded_jobs
    assert reloaded_jobs[job_id]["status"] == "running"

    # Restore to in-memory store
    mcp1._jobs.update(reloaded_jobs)

    # Job is now accessible again
    status_after_reload = mcp1.tool_job_status({"job_id": job_id})
    assert status_after_reload["status"] == "running"
