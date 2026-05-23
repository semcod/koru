from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from koruobserve.bootstrap import ensure_mesh_key, ensure_observe_config
from koruobserve.lifecycle import observe_down, observe_status, observe_up
from koruobserve.paths import pidfile, state_file
from koruvision.capture_probe import resolve_observe_python


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
    monkeypatch.setattr("koruobserve.lifecycle.resolve_observe_python", lambda: sys.executable)
    monkeypatch.setattr("koruobserve.cli._require_observe_runtime", lambda: None)
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
    assert not state.relay_url.endswith(":0")
    assert not state.dashboard_url.endswith(":0")
    vision_args = fake_spawn[1][1]
    assert "vision" in vision_args and "agent" in vision_args
    assert "--project" not in vision_args
    payload = json.loads(state_file(project).read_text(encoding="utf-8"))
    assert payload["python"] == sys.executable
    assert payload["grid_url"].endswith("/grid")


def test_observe_status_reports_pids(tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    observe_up(project, relay_port=0, dashboard_port=0)
    with mock.patch("koruobserve.lifecycle._is_alive", return_value=True):
        status = observe_status(project)
    assert set(status) == {"relay", "vision", "dashboard"}
    assert all(status[name]["pid"] for name in status)


def test_observe_down_stops_orphan_vision_agents(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    killed: list[int] = []
    probes: list[str] = []

    def _fake_pids(proj: Path, needle: str) -> list[int]:
        probes.append(needle)
        return [4242] if needle == " vision " else []

    monkeypatch.setattr("koruobserve.lifecycle._pids_matching_koru_cmdline", _fake_pids)
    monkeypatch.setattr("koruobserve.lifecycle.os.kill", lambda pid, sig: killed.append(pid))
    observe_down(project)
    assert " mesh relay " in probes
    assert " vision " in probes
    assert " serve " in probes
    assert killed == [4242]


def test_resolve_observe_python_prefers_working_interpreter(monkeypatch) -> None:
    monkeypatch.delenv("KORU_OBSERVE_PYTHON", raising=False)
    monkeypatch.setattr(
        "koruvision.capture_probe.python_can_capture",
        lambda exe: exe == "/good/python",
    )
    monkeypatch.setattr("koruvision.capture_probe.sys.executable", "/bad/koru")
    monkeypatch.setattr("koruvision.capture_probe.shutil.which", lambda _: "/good/python")
    assert resolve_observe_python() == "/good/python"


def test_python_can_capture_uses_koruvision_capture_script(monkeypatch) -> None:
    from koruvision import capture_probe

    captured: dict[str, list[str]] = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(capture_probe.subprocess, "run", _fake_run)
    assert capture_probe.python_can_capture("/probe/python") is True
    assert captured["cmd"][:2] == ["/probe/python", "-c"]
    assert "capture_monitor_png" in captured["cmd"][2]


def test_require_observe_runtime_reports_missing_packages(monkeypatch) -> None:
    from koruobserve import cli as observe_cli

    monkeypatch.setattr(
        observe_cli.importlib.util,
        "find_spec",
        lambda name: None if name in {"websockets", "mss"} else object(),
    )
    monkeypatch.setattr(observe_cli, "_pip_install", lambda specs: 1)
    with pytest.raises(RuntimeError, match="automatic installation.*failed"):
        observe_cli._require_observe_runtime()


def test_cmd_install_invokes_pip_with_missing_specs(monkeypatch) -> None:
    from koruobserve import cli as observe_cli

    monkeypatch.setattr(
        observe_cli.importlib.util,
        "find_spec",
        lambda name: None if name == "mss" else object(),
    )
    captured: list[list[str]] = []
    monkeypatch.setattr(observe_cli.subprocess, "call", lambda cmd: captured.append(cmd) or 0)
    rc = observe_cli._cmd_install(None)
    assert rc == 0
    assert captured, "pip install was not invoked"
    assert any(arg.startswith("mss") for arg in captured[0])
    assert not any(arg.startswith("websockets") for arg in captured[0])


def test_cmd_install_skips_when_all_present(monkeypatch, capsys) -> None:
    from koruobserve import cli as observe_cli

    monkeypatch.setattr(observe_cli.importlib.util, "find_spec", lambda name: object())
    rc = observe_cli._cmd_install(None)
    assert rc == 0
    assert "already installed" in capsys.readouterr().out


def test_project_path_resolves_from_args() -> None:
    from argparse import Namespace

    from koruobserve.cli_parser import project_path

    assert project_path(Namespace(project=Path("/tmp/demo"))) == Path("/tmp/demo").resolve()


def test_project_path_defaults_to_cwd_when_unset() -> None:
    from argparse import Namespace

    from koruobserve.cli_parser import project_path

    assert project_path(Namespace(project=None)) == Path.cwd().resolve()


def test_observe_main_up_uses_parent_project_default(monkeypatch, tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    monkeypatch.chdir(project)
    from koruobserve.cli import observe_main

    rc = observe_main(["up", "--relay-port", "19987", "--dashboard-port", "18765"])
    assert rc == 0
    assert (project / ".koru" / "run" / "relay.pid").is_file()


def test_observe_main_up_accepts_project_after_subcommand(tmp_path: Path, fake_spawn) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    from koruobserve.cli import observe_main

    rc = observe_main(
        [
            "up",
            "--project",
            str(project),
            "--relay-port",
            "19988",
            "--dashboard-port",
            "18766",
        ],
    )
    assert rc == 0
    assert (project / ".koru" / "run" / "relay.pid").is_file()


def test_observe_main_up_reports_missing_optional_dependencies(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    from koruobserve.cli import observe_main

    def _missing() -> None:
        raise RuntimeError("missing observation dependency websockets")

    monkeypatch.setattr("koruobserve.cli._require_observe_runtime", _missing)
    rc = observe_main(["up", "--project", str(project)])
    assert rc == 2
    assert not (project / ".koru" / "run" / "relay.pid").exists()


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
