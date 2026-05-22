from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from koruobserve.bootstrap import ensure_mesh_key, ensure_observe_config
from koruobserve.lifecycle import observe_down, observe_status, observe_up
from koruobserve.paths import pidfile, state_file


@pytest.fixture
def fake_spawn(monkeypatch):
    next_pid = iter(range(10001, 10999))
    spawned: list[tuple[str, list[str]]] = []

    def _fake_spawn(name, args, project):
        pid = next(next_pid)
        spawned.append((name, args))
        pidfile(project, name).parent.mkdir(parents=True, exist_ok=True)
        pidfile(project, name).write_text(f"{pid}\n", encoding="utf-8")
        return pid

    monkeypatch.setattr("koruobserve.lifecycle._spawn", _fake_spawn)
    return spawned


def test_ensure_observe_config_enables_vision_and_mesh(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    config = ensure_observe_config(project)
    assert config["vision"]["enabled"] is True
    assert config["mesh"]["enabled"] is True
    assert config["schema"].endswith("/v2")


def test_ensure_mesh_key_creates_key_file(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    config = ensure_observe_config(project)
    key_path = ensure_mesh_key(project, config)
    assert key_path.is_file()
    assert len(key_path.read_bytes()) >= 16


def test_observe_up_spawns_three_processes(tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    state = observe_up(project, relay_port=0, dashboard_port=0)
    names = [name for name, _ in fake_spawn]
    assert names == ["relay", "vision", "dashboard"]
    assert state.relay_pid and state.vision_pid and state.dashboard_pid
    payload = json.loads(state_file(project).read_text(encoding="utf-8"))
    assert payload["grid_url"].endswith("/grid")


def test_observe_status_reports_pids(tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    observe_up(project, relay_port=0, dashboard_port=0)
    with mock.patch("koruobserve.lifecycle._is_alive", return_value=True):
        status = observe_status(project)
    assert set(status) == {"relay", "vision", "dashboard"}
    assert all(status[name]["pid"] for name in status)


def test_project_path_resolves_from_args() -> None:
    from argparse import Namespace

    from koruobserve.cli import _project_path

    assert _project_path(Namespace(project=Path("/tmp/demo"))) == Path("/tmp/demo").resolve()


def test_observe_main_up_uses_parent_project_default(monkeypatch, tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    monkeypatch.chdir(project)
    from koruobserve.cli import observe_main

    rc = observe_main(["up", "--relay-port", "19987", "--dashboard-port", "18765"])
    assert rc == 0
    assert (project / ".koru" / "run" / "relay.pid").is_file()


def test_observe_down_removes_pidfiles(tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    observe_up(project, relay_port=0, dashboard_port=0)
    with mock.patch("os.kill"):
        stopped = observe_down(project)
    assert stopped == {"relay": True, "vision": True, "dashboard": True}
    for name in ("relay", "vision", "dashboard"):
        assert not pidfile(project, name).exists()
    assert not state_file(project).exists()
