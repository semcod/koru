from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
        "koru_run_ci",
        "koru_propose_edits",
        "koru_ide_command_catalog",
        "koru_ide_command_scenario_schema",
        "koru_validate_ide_command_scenario",
        "koru_ide_commands",
        "koru_ide_list_uris",
        "koru_ide_control_plan",
        "koru_ide_control_execute",
        "koru_ide_drive",
        "koru_ide_dsl_recent",
        "koru_strategy_prompt",
        "koru_desktop_uri_plan",
        "koru_desktop_uri_handle",
        "koru_desktop_uri_list_getv_uris",
        "koru_desktop_uri_resolve_getv",
        "koru_desktop_uri_get_getv_var",
        "koru_desktop_uri_resolve_system_map",
        "koru_desktop_uri_list_system_uris",
        "koru_env2llm_get_registry",
        "koru_env2llm_render_registry",
        "koru_env2llm_refresh_registry",
        "koru_env2llm_get_desktop",
        "koru_env2llm_list_commands",
        "koru_env2llm_list_uris",
        "koru_env2llm_mqtt_status",
    }.issubset(names)


def test_ci_tool_is_exported_by_compatibility_facade() -> None:
    assert "tool_run_ci" in mcp_server.__all__
    assert mcp_server.tool_run_ci is mcp_server.TOOL_DISPATCH["koru_run_ci"]


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


def test_run_ticket_delegates_to_shared_single_shot_helper(monkeypatch, tmp_path: Path) -> None:
    import koruapi.mcp_server_planfile as mcp_planfile
    from koru.queue.types import QueueRunResult

    calls: list[dict[str, Any]] = []

    def _fake_single_shot(**kwargs):
        calls.append(kwargs)
        return QueueRunResult(
            status="completed",
            ticket_id=kwargs["ticket_id"],
            executor_kind="shell",
            exit_code=0,
            stdout="ok",
        )

    monkeypatch.setattr(mcp_planfile, "run_queue_single_shot", _fake_single_shot)

    result = mcp_server.tool_run_ticket(
        {
            "project_root": str(tmp_path),
            "ticket_id": "PLF-123",
            "mode": "dry",
            "actor": " koru-mcp ",
            "queue_name": " default ",
        },
    )

    assert result["status"] == "success"
    assert result["queue_status"] == "completed"
    assert result["ticket_id"] == "PLF-123"
    assert result["executor_kind"] == "shell"
    assert calls == [
        {
            "project": tmp_path.resolve(),
            "ticket_id": "PLF-123",
            "mode": "dry",
            "actor": "koru-mcp",
            "queue_name": "default",
        }
    ]

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "success"
    assert status_payload["current_step"] == "completed"


def test_run_ticket_maps_failed_queue_result(monkeypatch, tmp_path: Path) -> None:
    import koruapi.mcp_server_planfile as mcp_planfile
    from koru.queue.types import QueueRunResult

    def _fake_single_shot(**kwargs):
        return QueueRunResult(
            status="failed",
            ticket_id=kwargs["ticket_id"],
            executor_kind="llm",
            exit_code=2,
            stderr="model 500",
        )

    monkeypatch.setattr(mcp_planfile, "run_queue_single_shot", _fake_single_shot)

    result = mcp_server.tool_run_ticket(
        {"project_root": str(tmp_path), "ticket_id": "PLF-FAIL"},
    )

    assert result["status"] == "failed"
    assert result["queue_status"] == "failed"
    assert result["exit_code"] == 2
    assert any("model 500" in line for line in result["logs"])

    status_payload = mcp_server.tool_job_status({"job_id": result["job_id"]})
    assert status_payload["status"] == "failed"
    assert status_payload["current_step"] == "failed"


def test_run_ticket_waiting_input_maps_to_success_like_cli(monkeypatch, tmp_path: Path) -> None:
    import koruapi.mcp_server_planfile as mcp_planfile
    from koru.queue.types import QueueRunResult

    def _fake_single_shot(**kwargs):
        return QueueRunResult(
            status="waiting_input",
            ticket_id=kwargs["ticket_id"],
            executor_kind="human",
            message="need operator input",
        )

    monkeypatch.setattr(mcp_planfile, "run_queue_single_shot", _fake_single_shot)

    result = mcp_server.tool_run_ticket(
        {"project_root": str(tmp_path), "ticket_id": "PLF-HUMAN"},
    )

    assert result["status"] == "success"
    assert result["queue_status"] == "waiting_input"
    assert "exit_code" not in result
    assert any("need operator input" in line for line in result["logs"])


def test_run_ticket_error_updates_job_status(monkeypatch, tmp_path: Path) -> None:
    import koruapi.mcp_server_planfile as mcp_planfile

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(mcp_planfile, "run_queue_single_shot", _boom)

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


def test_single_shot_helper_maps_args_to_queue_runner(monkeypatch, tmp_path: Path) -> None:
    import koru.queue.runner as queue_runner
    from koru.queue.types import QueueRunResult

    captured: dict[str, Any] = {}

    def _fake_run_next(**kwargs):
        captured.update(kwargs)
        return QueueRunResult(status="dry_run", ticket_id=kwargs["target_ticket_id"])

    monkeypatch.setattr(queue_runner, "run_next_planfile_task", _fake_run_next)

    result = queue_runner.run_queue_single_shot(
        project=tmp_path,
        ticket_id="PLF-9",
        mode="dry",
    )

    assert result.status == "dry_run"
    assert captured == {
        "project": tmp_path,
        "actor": "koru-shell",
        "dry_run": True,
        "queue_name": None,
        "target_ticket_id": "PLF-9",
        "interactive": False,
    }


def test_queue_exit_success_matches_cli_contract() -> None:
    from koru.queue import SUCCESS_QUEUE_STATUSES, queue_run_exit_success

    assert SUCCESS_QUEUE_STATUSES == {"completed", "idle", "waiting_input", "dry_run"}
    assert queue_run_exit_success("dry_run")
    assert queue_run_exit_success("waiting_input")
    assert not queue_run_exit_success("failed")
    assert not queue_run_exit_success("target_not_runnable")


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


def test_vallm_and_sumr_gate_commands_use_supported_cli_shapes(tmp_path: Path) -> None:
    gate_commands = mcp_server._gate_commands(tmp_path)

    assert gate_commands["vallm"] == [
        sys.executable,
        "-m",
        "vallm",
        "batch",
        "-r",
        "--format",
        "json",
        str(tmp_path),
    ]
    assert gate_commands["sumr"][0] == sys.executable
    assert gate_commands["sumr"][1] == "-c"
    assert "main_sumr" in gate_commands["sumr"][2]
    assert gate_commands["sumr"][3] == str(tmp_path)


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
