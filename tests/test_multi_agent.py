"""Tests for multi-agent orchestration (koru auto <N>)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from koru.multi_agent import (
    MultiAgentConfig,
    MultiAgentOrchestrator,
    TaskItem,
    discover_workspace_projects,
    get_pending_tasks_for_project,
    is_koru_project,
    parse_multi_agent_args,
    run_multi_agent_auto,
)


def test_parse_multi_agent_args_positional():
    config = parse_multi_agent_args(["10"])
    assert config.workers == 10
    assert not config.sync_github
    assert not config.dry_run


def test_parse_multi_agent_args_options(tmp_path: Path):
    config = parse_multi_agent_args(
        [
            "--workers",
            "5",
            "--workspace",
            str(tmp_path),
            "--sync",
            "--client",
            "crush",
            "--provider",
            "z.ai",
            "--dry-run",
            "--max-tickets",
            "20",
        ]
    )
    assert config.workers == 5
    assert config.workspace == tmp_path.resolve()
    assert config.sync_github is True
    assert config.client == "crush"
    assert config.provider == "z.ai"
    assert config.dry_run is True
    assert config.max_tickets == 20


def test_is_koru_project(tmp_path: Path):
    assert not is_koru_project(tmp_path)

    (tmp_path / ".planfile").mkdir()
    assert is_koru_project(tmp_path)


def test_discover_workspace_projects(tmp_path: Path):
    p1 = tmp_path / "proj1"
    p2 = tmp_path / "proj2"
    non_proj = tmp_path / "docs"

    p1.mkdir()
    (p1 / ".planfile").mkdir()

    p2.mkdir()
    (p2 / "koru.yaml").write_text("autonomy:\n  strategy: default\n")

    non_proj.mkdir()

    found = discover_workspace_projects(tmp_path)
    assert p1 in found
    assert p2 in found
    assert non_proj not in found


def test_get_pending_tasks_for_project(tmp_path: Path):
    sprints_dir = tmp_path / ".planfile" / "sprints"
    sprints_dir.mkdir(parents=True)
    current_yaml = sprints_dir / "current.yaml"

    data = {
        "tickets": {
            "TICK-1": {"id": "TICK-1", "name": "Fix bug", "status": "open"},
            "TICK-2": {"id": "TICK-2", "name": "Write docs", "status": "in_progress"},
            "TICK-3": {"id": "TICK-3", "name": "Done task", "status": "completed"},
        }
    }
    current_yaml.write_text(yaml.safe_dump(data))

    tasks = get_pending_tasks_for_project(tmp_path)
    ticket_ids = {t.ticket_id for t in tasks}
    assert ticket_ids == {"TICK-1", "TICK-2"}


def test_orchestrator_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    p1 = tmp_path / "proj1"
    p1.mkdir()
    sprints_dir = p1 / ".planfile" / "sprints"
    sprints_dir.mkdir(parents=True)
    (sprints_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "tickets": {
                    "TICK-101": {"id": "TICK-101", "name": "Multi-agent test", "status": "open"}
                }
            }
        )
    )

    config = MultiAgentConfig(
        workers=3,
        workspace=tmp_path,
        dry_run=True,
        client="crush",
    )
    orchestrator = MultiAgentOrchestrator(config)
    exit_code = orchestrator.run()
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "discovered 1 project(s)" in out
    assert "[Dry Run Plan]" in out
    assert "[proj1] TICK-101: Multi-agent test (client: crush)" in out


def test_orchestrator_build_worker_env():
    config = MultiAgentConfig(
        workers=2,
        client="crush",
        provider="z.ai",
    )
    orchestrator = MultiAgentOrchestrator(config)
    env = orchestrator.build_worker_env()
    assert env.get("KORU_AUTOPILOT_IDE") == "crush"
    assert env.get("KORU_TILLM_CLIENT") == "crush"
    assert env.get("TILLM_PROVIDER") == "z.ai"


def test_build_worker_command():
    config = MultiAgentConfig(workers=2, worker_dry_run=True)
    orchestrator = MultiAgentOrchestrator(config)
    task = TaskItem(project=Path("/tmp/p1"), ticket_id="PLF-1", sprint="backlog")
    cmd = orchestrator.build_worker_command(task)
    assert "ticket" in cmd
    assert "auto" in cmd
    assert "PLF-1" in cmd
    assert "--sprint" in cmd
    assert "backlog" in cmd
    assert "--dry-run" in cmd

