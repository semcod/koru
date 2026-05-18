"""Tests for interactive operator pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.autonomous_startup import AutonomousStartupProbe
from koru.autonomy import operator_pipeline as op


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


def test_build_operator_steps_mcp_pending_without_config(tmp_path: Path, probe: AutonomousStartupProbe) -> None:
    steps = op.build_operator_steps(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
    )
    mcp = next(s for s in steps if s.step_id == "mcp_koru")
    assert mcp.status == "pending"
    assert mcp.task_command == "task koru:mcp:bootstrap"


def test_build_operator_steps_mcp_ok_when_configured(
    tmp_path: Path, probe: AutonomousStartupProbe
) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )
    steps = op.build_operator_steps(project=tmp_path, probe=probe, plugin_connected=True)
    mcp = next(s for s in steps if s.step_id == "mcp_koru")
    assert mcp.status == "ok"


def test_run_startup_operator_pipeline_creates_tickets(
    tmp_path: Path, probe: AutonomousStartupProbe, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1\n", encoding="utf-8"
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  name: current\n  tickets: {}\n", encoding="utf-8"
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
    assert result.tickets_created
    assert any(s.step_id == "autopilot_plugin" and s.ticket_id for s in result.steps)


def test_run_startup_operator_pipeline_dedup_markers(
    tmp_path: Path, probe: AutonomousStartupProbe, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".planfile" / "sprints").mkdir(parents=True)
    (tmp_path / ".planfile" / "config.yaml").write_text(
        "prefix: PLF\nnext_id: 1\n", encoding="utf-8"
    )
    (tmp_path / ".planfile" / "sprints" / "current.yaml").write_text(
        "sprint:\n  name: current\n  tickets: {}\n", encoding="utf-8"
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
    second = op.run_startup_operator_pipeline(
        project=tmp_path,
        probe=probe,
        plugin_connected=False,
        create_tickets=True,
    )
    assert first.tickets_created
    assert not second.tickets_created
