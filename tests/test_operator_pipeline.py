"""Tests for interactive operator pipeline."""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.autonomous_startup import AutonomousStartupProbe
from koru.autonomy import operator_pipeline as op

REAL_SELF_CONTROL_OK = op._self_control_ok


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


@pytest.fixture
def probe(tmp_path: Path) -> AutonomousStartupProbe:
    return AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="cursor",
        lane_source="test",
        resolved_autopilot_ide="cursor",
        autopilot_ide_source="test",
        running_ides=(),
        terminal_lane="cursor",
        socket_path="/tmp/koru-autopilot.sock",
        session="wayland",
        term_program="-",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )


@pytest.fixture(autouse=True)
def self_control_ok_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(op, "_self_control_ok", lambda *_args: (True, "ok", None))


def test_build_operator_steps_mcp_pending_without_config(
    tmp_path: Path, probe: AutonomousStartupProbe
) -> None:
    steps = op.build_operator_steps(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
    )
    mcp = next(s for s in steps if s.step_id == "mcp_koru")
    assert mcp.status == "pending"
    assert mcp.task_command == "task koru:mcp:bootstrap"


def test_build_operator_steps_mcp_ok_when_configured(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    steps = op.build_operator_steps(project=tmp_path, probe=probe, plugin_connected=True)
    mcp = next(s for s in steps if s.step_id == "mcp_koru")
    assert mcp.status == "ok"


def test_build_operator_steps_vscode_ignores_cursor_mcp_config(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    vscode_probe = replace(
        probe,
        resolved_lane="vscode",
        resolved_autopilot_ide="vscode",
        terminal_lane="vscode",
    )

    steps = op.build_operator_steps(project=tmp_path, probe=vscode_probe, plugin_connected=True)
    mcp = next(s for s in steps if s.step_id == "mcp_koru")

    assert mcp.status == "pending"
    assert ".vscode/mcp.json" in mcp.detail


def test_build_operator_steps_skips_plugin_for_jetbrains(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
) -> None:
    jetbrains_probe = replace(
        probe,
        resolved_lane="jetbrains",
        resolved_autopilot_ide="jetbrains",
        terminal_lane="jetbrains",
    )
    steps = op.build_operator_steps(
        project=tmp_path,
        probe=jetbrains_probe,
        plugin_connected=False,
    )
    plugin = next(s for s in steps if s.step_id == "autopilot_plugin")
    assert plugin.status == "skipped"
    assert plugin.task_command is None
    assert "plugin niedostępny" in plugin.detail


def test_build_operator_steps_plugin_probe_uses_resolved_ide(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
) -> None:
    steps = op.build_operator_steps(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
    )
    plugin = next(s for s in steps if s.step_id == "autopilot_plugin")

    assert plugin.status == "pending"
    assert plugin.task_command == "koru ide doctor --ide cursor --fix --gc-sockets"


def test_build_operator_steps_skips_os_calibration_for_plugin_ide(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vscodium_probe = replace(
        probe,
        resolved_lane="vscodium",
        resolved_autopilot_ide="vscodium",
        terminal_lane="vscodium",
    )
    profile_checks: list[str] = []
    monkeypatch.setattr(
        op,
        "_os_profile_ok",
        lambda ide, _project: profile_checks.append(ide) or (False, "missing"),
    )

    steps = op.build_operator_steps(
        project=tmp_path,
        probe=vscodium_probe,
        plugin_connected=True,
    )
    os_step = next(s for s in steps if s.step_id == "os_calibrate")

    assert os_step.status == "skipped"
    assert os_step.task_command is None
    assert "wtyczki/socketu" in os_step.detail
    assert profile_checks == []


def test_build_operator_steps_skips_os_calibration_for_windsurf_main_instance(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    windsurf_probe = replace(
        probe,
        resolved_lane="windsurf-main",
        resolved_autopilot_ide="windsurf",
        terminal_lane="windsurf-main",
        socket_path="/run/user/1000/koru-autopilot-windsurf-main.sock",
    )
    profile_checks: list[str] = []
    monkeypatch.setattr(
        op,
        "_os_profile_ok",
        lambda ide, _project: profile_checks.append(ide) or (False, "missing"),
    )

    steps = op.build_operator_steps(
        project=tmp_path,
        probe=windsurf_probe,
        plugin_connected=True,
    )
    os_step = next(s for s in steps if s.step_id == "os_calibrate")

    assert os_step.status == "skipped"
    assert os_step.task_command is None
    assert profile_checks == []


def test_build_operator_steps_adds_self_control_step(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(op, "_self_control_ok", lambda *_args: (False, "package stale", "koru self repair --yes"))
    steps = op.build_operator_steps(
        project=tmp_path,
        probe=probe,
        plugin_connected=True,
    )

    self_step = next(s for s in steps if s.step_id == "self_control")
    assert self_step.status == "pending"
    assert self_step.actor == "taskfile"
    assert self_step.task_command == "koru self repair --yes"


def _self_report(
    tmp_path: Path,
    *,
    status: str,
    repair: str = "",
    actions: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    check = SimpleNamespace(
        name="autopilot_install_manager",
        status=status,
        detail="installed=old; expected=new",
        repair=repair,
    )
    return SimpleNamespace(
        project=tmp_path,
        checks=[check],
        actions=actions or [],
        needs_repair=bool(repair and status in {"warn", "fail"}),
    )


def test_self_control_ok_auto_repairs_when_fix_clears_problem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_TEST_REAL_SELF_CONTROL", "1")
    from koru import self_control

    reports = iter(
        [
            _self_report(tmp_path, status="warn", repair="koru autopilot manage --fix"),
            _self_report(tmp_path, status="ok"),
        ]
    )
    monkeypatch.setattr(self_control, "run_self_control", lambda *_args, **_kwargs: next(reports))
    monkeypatch.setattr(
        self_control,
        "repair_self_control",
        lambda *_args, **_kwargs: _self_report(
            tmp_path,
            status="warn",
            repair="koru autopilot manage --fix",
            actions=[{"action": "install_plugin"}],
        ),
    )

    ok, detail, task = REAL_SELF_CONTROL_OK(tmp_path, "vscodium", "/tmp/koru.sock")

    assert ok is True
    assert task is None
    assert "auto-repaired" in detail


def test_self_control_ok_keeps_task_when_auto_repair_still_needs_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_TEST_REAL_SELF_CONTROL", "1")
    from koru import self_control

    reports = iter(
        [
            _self_report(tmp_path, status="warn", repair="koru autopilot manage --fix"),
            _self_report(tmp_path, status="warn", repair="koru autopilot manage --fix"),
        ]
    )
    monkeypatch.setattr(self_control, "run_self_control", lambda *_args, **_kwargs: next(reports))
    monkeypatch.setattr(
        self_control,
        "repair_self_control",
        lambda *_args, **_kwargs: _self_report(
            tmp_path,
            status="warn",
            repair="koru autopilot manage --fix",
            actions=[{"action": "install_plugin"}, {"action": "reload_ide_and_reconnect"}],
        ),
    )

    ok, detail, task = REAL_SELF_CONTROL_OK(tmp_path, "vscodium", "/tmp/koru.sock")

    assert ok is False
    assert "auto-repair ran" in detail
    assert task == f"koru self --project {tmp_path} --ide vscodium repair --yes"


def test_self_control_ok_respects_autorepair_opt_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_TEST_REAL_SELF_CONTROL", "1")
    from koru import self_control

    monkeypatch.setenv("KORU_SELF_CONTROL_AUTOREPAIR", "0")
    monkeypatch.setattr(
        self_control,
        "run_self_control",
        lambda *_args, **_kwargs: _self_report(
            tmp_path,
            status="warn",
            repair="koru autopilot manage --fix",
        ),
    )

    ok, detail, task = REAL_SELF_CONTROL_OK(tmp_path, "vscodium", "/tmp/koru.sock")

    assert ok is False
    assert detail == "autopilot_install_manager: installed=old; expected=new"
    assert task == f"koru self --project {tmp_path} --ide vscodium repair --yes"


def test_run_startup_operator_pipeline_creates_tickets(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  name: current\n  tickets: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))
    monkeypatch.setattr(op, "_self_control_ok", lambda *_args: (True, "ok", None))

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    assert result.tickets_created
    assert any(s.step_id == "autopilot_plugin" and s.ticket_id for s in result.steps)


def test_run_startup_operator_pipeline_autostarts_planfile_api_when_missing(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = iter([(False, "missing"), (True, "started")])
    started: list[Path] = []
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: next(checks))
    monkeypatch.setattr(
        op,
        "_try_start_planfile_api",
        lambda project, **_kwargs: started.append(project),
    )
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))
    monkeypatch.setattr(op, "_self_control_ok", lambda *_args: (True, "ok", None))

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=True,
        create_tickets=False,
    )

    assert started == [tmp_path]
    api_step = next(s for s in result.steps if s.step_id == "planfile_api")
    assert api_step.status == "ok"


def test_candidate_planfile_health_urls_use_serve_endpoint(tmp_path: Path) -> None:
    endpoint = tmp_path / ".planfile" / ".koru" / "serve-endpoint.json"
    endpoint.parent.mkdir(parents=True)
    endpoint.write_text(
        json.dumps({"http_base": "http://127.0.0.1:8766"}),
        encoding="utf-8",
    )

    assert op._candidate_planfile_health_urls(tmp_path) == [
        "http://127.0.0.1:8766/health",
        "http://127.0.0.1:8765/health",
    ]


def test_run_startup_operator_pipeline_dedup_markers(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  name: current\n  tickets: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))
    monkeypatch.setattr(op, "_self_control_ok", lambda *_args: (True, "ok", None))

    first = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    second = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    assert first.tickets_created
    assert not second.tickets_created


def test_run_startup_operator_pipeline_recovers_missing_marker_from_open_ticket(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  name: current\n  tickets: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    first = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    first_plugin = next(s for s in first.steps if s.step_id == "autopilot_plugin")
    assert first_plugin.ticket_id is not None

    marker = tmp_path / ".planfile" / ".koru" / "operator-steps" / "autopilot_plugin.ticket"
    marker.unlink()
    second = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    second_plugin = next(s for s in second.steps if s.step_id == "autopilot_plugin")

    assert second.tickets_created == []
    assert second_plugin.ticket_id == first_plugin.ticket_id
    assert marker.read_text(encoding="utf-8") == first_plugin.ticket_id


def test_run_startup_operator_pipeline_replaces_stale_ide_marker(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vscode_probe = replace(
        probe,
        resolved_lane="vscode",
        resolved_autopilot_ide="vscode",
        socket_path="/run/user/1000/koru-autopilot-vscode.sock",
        terminal_lane="vscode",
    )
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1281\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
  name: current
  tickets:
    PLF-1280:
      id: PLF-1280
      name: >-
        [OPERATOR] Autopilot: Connect + plugin w czacie
        brak pluginu na /run/user/1000/koru-autopilot-windsurf.sock
      status: waiting_input
      labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
      description: "brak pluginu na /run/user/1000/koru-autopilot-windsurf.sock"
      execution:
        queue: operator
      source:
        context:
          step_id: autopilot_plugin
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=vscode_probe,
        plugin_connected=False,
        create_tickets=True,
    )

    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert plugin_step.ticket_id is not None
    assert plugin_step.ticket_id != "PLF-1280"
    assert plugin_step.task_command == "koru ide doctor --ide vscode --fix --gc-sockets"
    assert marker.read_text(encoding="utf-8") == plugin_step.ticket_id
    assert [_ticket_args(call) for call in calls] == [["ticket", "done", "PLF-1280"]]


def test_run_startup_operator_pipeline_keeps_plugin_ticket_with_matching_dedupe_key(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1281\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
    name: current
    tickets:
        PLF-1280:
            id: PLF-1280
            name: "[OPERATOR] Autopilot: Connect + plugin w czacie"
            status: waiting_input
            labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
            description: "legacy detail text that no longer matches"
            execution:
                queue: operator
            source:
                context:
                    step_id: autopilot_plugin
                    detail: "legacy detail text that no longer matches"
                    task_command: "koru ide doctor --ide cursor --fix --gc-sockets"
                    dedupe_key: "koru:operator-pipeline:autopilot-plugin:cursor"
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )

    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert result.tickets_created == []
    assert plugin_step.ticket_id == "PLF-1280"
    assert marker.read_text(encoding="utf-8") == "PLF-1280"
    assert calls == []


def test_run_startup_operator_pipeline_closes_resolved_marker_ticket(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
  name: current
  tickets:
    PLF-1280:
      id: PLF-1280
      name: "[OPERATOR] Autopilot: Connect + plugin w czacie"
      status: waiting_input
      labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
      execution:
        queue: operator
      source:
        context:
          step_id: autopilot_plugin
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=True,
        create_tickets=True,
    )

    assert [_ticket_args(call) for call in calls] == [["ticket", "done", "PLF-1280"]]
    assert not marker.exists()
    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert plugin_step.status == "ok"
    assert plugin_step.ticket_id is None


def test_run_startup_operator_pipeline_replaces_closed_pending_marker(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1281\n",
        encoding="utf-8",
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
  name: current
  tickets:
    PLF-1280:
      id: PLF-1280
      name: "[OPERATOR] Autopilot: Connect + plugin w czacie"
      status: done
      labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
      execution:
        queue: operator
      source:
        context:
          detail: "old detail"
          step_id: autopilot_plugin
          task_command: koru ide doctor --ide vscodium --fix --gc-sockets
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )

    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert result.tickets_created == ["PLF-1281"]
    assert plugin_step.ticket_id == "PLF-1281"
    assert marker.read_text(encoding="utf-8") == "PLF-1281"


def test_run_startup_operator_pipeline_clears_missing_resolved_marker_ticket(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=True,
        create_tickets=True,
    )

    assert calls == []
    assert not marker.exists()
    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert plugin_step.status == "ok"
    assert plugin_step.ticket_id is None


def test_run_startup_operator_pipeline_keeps_marker_when_close_times_out(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
  name: current
  tickets:
    PLF-1280:
      id: PLF-1280
      name: "[OPERATOR] Autopilot: Connect + plugin w czacie"
      status: waiting_input
      labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
      execution:
        queue: operator
      source:
        context:
          step_id: autopilot_plugin
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 60))

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=True,
        create_tickets=True,
    )

    assert marker.read_text(encoding="utf-8") == "PLF-1280"
    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert plugin_step.status == "ok"
    assert plugin_step.ticket_id == "PLF-1280"


def test_run_startup_operator_pipeline_closes_marker_when_plugin_step_skipped(
    tmp_path: Path,
    probe: AutonomousStartupProbe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jetbrains_probe = replace(
        probe,
        resolved_lane="jetbrains",
        resolved_autopilot_ide="jetbrains",
        terminal_lane="jetbrains",
    )
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    marker_dir = tmp_path / ".planfile" / ".koru" / "operator-steps"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / "autopilot_plugin.ticket"
    marker.write_text("PLF-1280", encoding="utf-8")
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        """
sprint:
  name: current
  tickets:
    PLF-1280:
      id: PLF-1280
      name: "[OPERATOR] Autopilot: Connect + plugin w czacie"
      status: waiting_input
      labels: [koru, operator, auto-pipeline, step:autopilot_plugin]
      execution:
        queue: operator
      source:
        context:
          step_id: autopilot_plugin
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(op, "_planfile_api_ok", lambda _p: (True, "ok"))
    monkeypatch.setattr(op, "_host_injectors_ok", lambda: (True, "ok"))
    monkeypatch.setattr(op, "_os_profile_ok", lambda _i, _p: (True, "ok"))

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    monkeypatch.setattr(op.subprocess, "run", fake_run)

    result = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=jetbrains_probe,
        plugin_connected=False,
        create_tickets=True,
    )

    assert [_ticket_args(call) for call in calls] == [["ticket", "done", "PLF-1280"]]
    assert not marker.exists()
    plugin_step = next(s for s in result.steps if s.step_id == "autopilot_plugin")
    assert plugin_step.status == "skipped"
    assert plugin_step.ticket_id is None
