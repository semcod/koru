from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from koru import autonomous_startup as startup
from koru.autonomous import _apply_agent_lane_environ
from koru.autopilot.ide import RunningIDE


def test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    (tmp_path / ".cursor").mkdir()
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=42, exe="/snap/code/code"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value=None),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, _a: "cursor",
        )
    assert lane == "vscode"
    assert source.startswith("running:")


def test_resolve_autopilot_ide_for_autonomous_returns_string_lane() -> None:
    from koru.ide_router import resolve_ide_route

    ide, source = startup.resolve_autopilot_ide_for_autonomous(
        "auto",
        "vscode",
        resolve_ide_route_fn=resolve_ide_route,
    )
    assert isinstance(ide, str)
    assert ide == "vscode"
    assert source == "lane"


def test_resolve_agent_lane_respects_terminal_jetbrains_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="jetbrains"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "jetbrains"
    assert source == "terminal"


def test_resolve_agent_lane_terminal_hint_overrides_conflicting_env_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
        RunningIDE(id="vscodium", label="VSCodium", pid=11, exe="/usr/bin/codium"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscodium"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "vscodium"
    assert source == "terminal:over-env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_prefers_vscodium_target_over_generic_vscode_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
        RunningIDE(id="vscodium", label="VSCodium", pid=11, exe="/usr/bin/codium"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup.pick_target", return_value=running[1]),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscode"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "vscodium"
    assert source == "target:over-terminal:vscode"


def test_resolve_agent_lane_env_instance_used_without_terminal_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
        RunningIDE(id="vscodium", label="VSCodium", pid=11, exe="/usr/bin/codium"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value=None),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "vscode"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_explicit_vscodium_beats_generic_vscode_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
        RunningIDE(id="vscodium", label="VSCodium", pid=11, exe="/usr/bin/codium"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscode"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "vscodium"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_autopilot_ide_keeps_jetbrains_lane_when_plugin_ide_running() -> None:
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    ide, source = startup.resolve_autopilot_ide_for_autonomous(
        "auto",
        "jetbrains",
        resolve_ide_route_fn=lambda **_k: None,
        detect_running_ides_fn=lambda: running,
    )
    assert ide == "jetbrains"
    assert source == "lane"


def test_resolve_autopilot_ide_keeps_jetbrains_when_no_plugin_ide_running() -> None:
    running = [
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    ide, source = startup.resolve_autopilot_ide_for_autonomous(
        "auto",
        "jetbrains",
        resolve_ide_route_fn=lambda **_k: None,
        detect_running_ides_fn=lambda: running,
    )
    assert ide == "jetbrains"
    assert source == "lane"


def test_format_post_startup_operator_hints_mentions_socket(tmp_path: Path) -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="cursor",
        autopilot_ide_cli="cursor",
        resolved_lane="cursor",
        lane_source="cli:cursor",
        resolved_autopilot_ide="cursor",
        autopilot_ide_source="cli:cursor",
        running_ides=("Cursor (pid=1)",),
        terminal_lane="cursor",
        socket_path="/run/user/1000/koru-autopilot-cursor.sock",
        session="wayland",
        term_program="-",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=False),
    )
    assert probe.socket_path in text
    assert "koru autopilot status" in text
    assert "require-plugin" in text
    assert "[!] brak zgodnego pluginu" in text
    assert "drive jest wstrzymany" in text


def test_format_post_startup_operator_hints_warns_when_vscode_selected_with_vscodium_running(
    tmp_path: Path,
) -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="vscode",
        lane_source="terminal",
        resolved_autopilot_ide="vscode",
        autopilot_ide_source="lane",
        running_ides=("VS Code (pid=1)", "VSCodium (pid=2)"),
        terminal_lane="vscode",
        socket_path="/run/user/1000/koru-autopilot-vscode.sock",
        session="wayland",
        term_program="vscode",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )

    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=True),
    )

    assert "wybrano ide=vscode, ale działa też VSCodium" in text
    assert "--agent-lane vscodium --autopilot-ide vscodium" in text
    assert "~/.config/Code/User/settings.json" in text


def test_format_post_startup_operator_hints_for_jetbrains_skips_plugin_steps() -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=Path("/tmp/project"),
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="jetbrains",
        lane_source="terminal",
        resolved_autopilot_ide="jetbrains",
        autopilot_ide_source="lane",
        running_ides=("JetBrains IDE (pid=1)",),
        terminal_lane="jetbrains",
        socket_path="/run/user/1000/koru-autopilot-jetbrains.sock",
        session="wayland",
        term_program="-",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=False),
    )
    assert "plugin niedostępny dla ide=jetbrains" in text
    assert "Command Palette" not in text
    assert "--require-plugin" not in text
    assert "koru: Connect autopilot daemon" not in text


def test_format_startup_banner_includes_version(tmp_path: Path) -> None:
    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolve_project_lane=lambda _p, _a: "local",
    )
    text = "\n".join(startup.format_startup_banner(probe))
    assert "koru autonomous: koru " in text
    assert "python " in text
    assert "autopilot socket" in text


def test_build_startup_probe_reports_per_ide_socket_for_explicit_ide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="none",
        autopilot_ide_cli="vscodium",
        resolve_project_lane=lambda _p, _a: None,
    )

    assert probe.socket_path == "/run/user/1000/koru-autopilot-vscodium.sock"
    assert os.environ.get("KORU_AUTOPILOT_INSTANCE") is None


def test_apply_agent_lane_environ_uses_running_ide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    for key in (
        "VSCODE_NLS_CONFIG",
        "VSCODE_IPC_HOOK",
        "VSCODE_PID",
        "VSCODE_CWD",
        "VSCODE_CODE_CACHE_PATH",
        "TERM_PROGRAM",
    ):
        monkeypatch.delenv(key, raising=False)
    running = [RunningIDE(id="vscode", label="VS Code", pid=99, exe="/usr/share/code/code")]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup.detect_terminal_host_ide_id", return_value=None),
    ):
        lane = _apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "vscode"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscode"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "vscode"
