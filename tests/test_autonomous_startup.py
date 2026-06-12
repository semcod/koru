from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from koru import autonomous_startup as startup
from koru.autonomous import _apply_agent_lane_environ
from koru.autopilot.ide import RunningIDE


@pytest.fixture(autouse=True)
def _isolate_desktop_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup, "_focused_agent_lane_from_desktop", lambda: None)


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


def test_resolve_agent_lane_prefers_focused_ide_over_terminal_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=42, exe="/usr/bin/cursor"),
        RunningIDE(id="vscode", label="VS Code", pid=43, exe="/usr/bin/code"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._focused_agent_lane_from_desktop", return_value="cursor"),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscode"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )

    assert lane == "cursor"
    assert source == "focused"


def test_resolve_agent_lane_focus_beats_conflicting_explicit_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=42, exe="/usr/bin/cursor"),
        RunningIDE(id="vscode", label="VS Code", pid=43, exe="/usr/bin/code"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._focused_agent_lane_from_desktop", return_value="cursor"),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value=None),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )

    assert lane == "cursor"
    assert source == "focused"


def test_resolve_agent_lane_focus_maps_to_project_lane_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=42, exe="/usr/bin/cursor"),
        RunningIDE(id="vscode", label="VS Code", pid=43, exe="/usr/bin/code"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._focused_agent_lane_from_desktop", return_value="cursor"),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value=None),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: "cursor-main" if lane_id == "cursor" else lane_id,
        )

    assert lane == "cursor-main"
    assert source == "focused"


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


def test_canonical_autopilot_ide_id_maps_instance_slug() -> None:
    assert startup.canonical_autopilot_ide_id("windsurf-main") == "windsurf"
    assert startup.canonical_autopilot_ide_id("cursor-b") == "cursor"
    assert startup.canonical_autopilot_ide_id("jetbrains") == "jetbrains"


def test_resolve_autopilot_ide_for_autonomous_maps_windsurf_main_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.ide_router import resolve_ide_route

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    ide, source = startup.resolve_autopilot_ide_for_autonomous(
        "auto",
        "windsurf-main",
        resolve_ide_route_fn=resolve_ide_route,
    )
    assert ide == "windsurf"
    assert source == "lane"


def test_build_startup_probe_keeps_instance_socket_for_windsurf_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=[]),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value=None),
    ):
        probe = startup.build_startup_probe(
            tmp_path,
            agent_lane_cli="auto",
            autopilot_ide_cli="auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert probe.resolved_lane == "windsurf-main"
    assert probe.resolved_autopilot_ide == "windsurf"
    assert probe.socket_path.endswith("koru-autopilot-windsurf-main.sock")


def test_resolve_agent_lane_prefers_cursor_over_jetbrains_terminal_when_both_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: koru auto from a JetBrains embedded terminal must not lock the
    lane to jetbrains when Cursor is also running — jetbrains has no autopilot
    plugin and raw ydotool typing lands in the file editor."""
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="jetbrains"),
        patch(
            "koru.autonomous_startup.pick_target",
            return_value=running[0],
        ),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "cursor"
    assert source == "terminal:prefer-cursor-over-jetbrains"


def test_resolve_agent_lane_explicit_jetbrains_env_preserved_when_terminal_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit KORU_AUTOPILOT_INSTANCE=jetbrains is respected when the user is
    actively working from the JetBrains integrated terminal."""
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "jetbrains")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="jetbrains"),
        patch(
            "koru.autonomous_startup.pick_target",
            return_value=running[0],
        ),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "jetbrains"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_explicit_jetbrains_env_preserved_when_terminal_not_plugin_ide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit KORU_AUTOPILOT_INSTANCE=jetbrains is respected when the terminal
    is detected as a non-plugin IDE (e.g., vscode env vars in JetBrains terminal)."""
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "jetbrains")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscode"),
        patch(
            "koru.autonomous_startup.pick_target",
            return_value=running[0],
        ),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "jetbrains"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_explicit_jetbrains_env_preserved_when_terminal_is_plugin_ide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit KORU_AUTOPILOT_INSTANCE=jetbrains is respected even when the terminal
    is a plugin IDE (cursor/windsurf), since jetbrains has no plugin support."""
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "jetbrains")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="cursor"),
        patch(
            "koru.autonomous_startup.pick_target",
            return_value=running[0],
        ),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "jetbrains"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_explicit_plugin_ide_overridden_by_different_plugin_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit KORU_AUTOPILOT_INSTANCE=cursor is overridden when the terminal
    is a different plugin IDE (windsurf)."""
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor")
    running = [
        RunningIDE(id="windsurf", label="Windsurf", pid=10, exe="/usr/bin/windsurf"),
        RunningIDE(id="cursor", label="Cursor", pid=11, exe="/usr/bin/cursor"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="windsurf"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "windsurf"
    assert source == "terminal:over-env:KORU_AUTOPILOT_INSTANCE"


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


def test_resolve_agent_lane_preserves_suffixed_explicit_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="cursor"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "cursor-main"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


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


def test_resolve_agent_lane_prefers_antigravity_target_over_generic_vscode_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(
            id="antigravity",
            label="Antigravity",
            pid=10,
            exe="/usr/share/antigravity/antigravity",
        ),
        RunningIDE(id="vscode", label="VS Code", pid=11, exe="/usr/bin/code"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup.pick_target", return_value=running[0]),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="vscode"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "antigravity"
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


def test_resolve_agent_lane_explicit_zed_beats_generic_vscode_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "zed")
    running = [
        RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
        RunningIDE(id="zed", label="Zed", pid=11, exe="/usr/bin/zed"),
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
    assert lane == "zed"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_terminal_zed_does_not_override_explicit_plugin_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor")
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(id="zed", label="Zed", pid=11, exe="/usr/bin/zed"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="zed"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "cursor"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_resolve_agent_lane_prefers_antigravity_when_terminal_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    running = [
        RunningIDE(id="cursor", label="Cursor", pid=10, exe="/usr/bin/cursor"),
        RunningIDE(
            id="antigravity",
            label="Antigravity",
            pid=11,
            exe="/usr/share/antigravity/antigravity",
        ),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup._terminal_agent_lane_from_env", return_value="unknown"),
    ):
        lane, source = startup.resolve_agent_lane_id(
            tmp_path,
            "auto",
            resolve_project_lane=lambda _p, lane_id: lane_id,
        )
    assert lane == "antigravity"
    assert source == "terminal:prefer-antigravity-over-unknown"


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


def test_format_post_startup_operator_hints_compact_for_disconnected_plugin(
    tmp_path: Path,
) -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="vscode",
        autopilot_ide_cli="vscode",
        resolved_lane="vscode",
        lane_source="cli:vscode",
        resolved_autopilot_ide="vscode",
        autopilot_ide_source="cli:vscode",
        running_ides=("VS Code (pid=1)",),
        terminal_lane="vscode",
        socket_path="/run/user/1000/koru-autopilot-vscode.sock",
        session="wayland",
        term_program="vscode",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )

    text = "\n".join(
        startup.format_post_startup_operator_hints(
            probe,
            plugin_connected=False,
            compact=True,
        ),
    )

    assert "[!] brak zgodnego pluginu" in text
    assert "next reload/reconnect plugin" in text
    assert "koru autopilot status --explain" in text
    assert "koru ide doctor --ide vscode --fix --explain" in text
    assert "co zrobić teraz" not in text
    assert "1) Otwórz" not in text
    assert "require-plugin" not in text


def test_format_post_startup_operator_hints_can_name_plugin_version_mismatch(
    tmp_path: Path,
) -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="vscodium",
        autopilot_ide_cli="vscodium",
        resolved_lane="vscodium",
        lane_source="cli:vscodium",
        resolved_autopilot_ide="vscodium",
        autopilot_ide_source="cli:vscodium",
        running_ides=("VSCodium (pid=1)",),
        terminal_lane="vscodium",
        socket_path="/run/user/1000/koru-autopilot-vscodium.sock",
        session="wayland",
        term_program="vscode",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(
            probe,
            plugin_connected=False,
            plugin_blocker="plugin_version_mismatch",
            plugin_reason="connected=0.1.63 expected=0.1.64",
        ),
    )
    assert "plugin_version_mismatch" in text
    assert "connected=0.1.63 expected=0.1.64" in text
    assert "wersja/protokół aktywnej wtyczki" in text


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
    assert "vdisplay/photo-VQL" in text
    assert "screencast start --force" in text
    assert "screencast probe --via-agent" in text
    assert "KORU_VDISPLAY_CONTROL_FALLBACK=1" not in text
    assert "export KORU_AUTOPILOT_INSTANCE=jetbrains" in text


def test_format_post_startup_operator_hints_for_jetbrains_suffixed_lane() -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=Path("/tmp/project"),
        agent_lane_cli="jetbrains",
        autopilot_ide_cli="auto",
        resolved_lane="jetbrains-main",
        lane_source="cli:jetbrains",
        resolved_autopilot_ide="jetbrains",
        autopilot_ide_source="lane",
        running_ides=("JetBrains IDE (pid=1)",),
        terminal_lane="jetbrains",
        socket_path="/run/user/1000/koru-autopilot-jetbrains-main.sock",
        session="wayland",
        term_program="-",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )

    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=False),
    )

    assert "Socket daemona = /run/user/1000/koru-autopilot-jetbrains-main.sock" in text
    assert "export KORU_AUTOPILOT_INSTANCE=jetbrains-main" in text
    assert "export KORU_AUTOPILOT_INSTANCE=jetbrains\n" not in f"{text}\n"


def test_format_post_startup_operator_hints_warns_when_jetbrains_running_but_windsurf_selected(
    tmp_path: Path,
) -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=tmp_path,
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="windsurf",
        lane_source="env:KORU_AUTOPILOT_INSTANCE",
        resolved_autopilot_ide="windsurf",
        autopilot_ide_source="lane",
        running_ides=("Windsurf (pid=1)", "JetBrains IDE (pid=2)"),
        terminal_lane="windsurf",
        socket_path="/run/user/1000/koru-autopilot-windsurf.sock",
        session="wayland",
        term_program="vscode",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )

    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=True),
    )

    assert "JetBrains IDE działa, ale autopilot wybrał ide=windsurf" in text
    assert "--agent-lane jetbrains --autopilot-ide jetbrains" in text
    assert "vdisplay/photo-VQL" in text


def test_format_post_startup_operator_hints_for_zed_uses_keyboard_path() -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=Path("/tmp/project"),
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="zed",
        lane_source="terminal",
        resolved_autopilot_ide="zed",
        autopilot_ide_source="lane",
        running_ides=("Zed (pid=1)",),
        terminal_lane="zed",
        socket_path="/run/user/1000/koru-autopilot-zed.sock",
        session="wayland",
        term_program="zed",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=False),
    )

    assert "plugin niedostępny dla ide=zed" in text
    assert "export KORU_AUTOPILOT_INSTANCE=zed" in text
    assert "task koru:ide-os:calibrate IDE=zed" in text
    assert "Command Palette" not in text
    assert "--require-plugin" not in text


def test_format_post_startup_operator_hints_for_antigravity_uses_plugin_path() -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=Path("/tmp/project"),
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="antigravity",
        lane_source="terminal",
        resolved_autopilot_ide="antigravity",
        autopilot_ide_source="lane",
        running_ides=("Antigravity (pid=1)",),
        terminal_lane="antigravity",
        socket_path="/run/user/1000/koru-autopilot-antigravity.sock",
        session="wayland",
        term_program="vscode",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=True),
    )

    assert "[ok] plugin połączony (ide=antigravity)" in text
    assert "~/.config/Antigravity/User/settings.json" in text
    assert "koru: Connect autopilot daemon" in text
    assert "--ide antigravity --require-plugin 'probe test'" in text
    assert "task koru:ide-os:calibrate IDE=antigravity" not in text


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


def test_format_startup_banner_includes_terminal_hint_and_lane_details() -> None:
    probe = startup.AutonomousStartupProbe(
        koru_version="0.0-test",
        python_version="3.12",
        project=Path("/tmp/project"),
        agent_lane_cli="auto",
        autopilot_ide_cli="auto",
        resolved_lane="zed",
        lane_source="terminal",
        resolved_autopilot_ide="zed",
        autopilot_ide_source="lane",
        running_ides=("Zed (pid=1)",),
        terminal_lane="zed",
        socket_path="/run/user/1000/koru-autopilot-zed.sock",
        session="wayland",
        term_program="zed",
        headless=False,
        xdg_runtime_dir="/run/user/1000",
    )

    text = "\n".join(startup.format_startup_banner(probe))
    assert "terminal hint" in text
    assert "lane=zed (from terminal" in text
    assert "autopilot IDE=zed (from lane" in text


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


def test_build_startup_probe_ignores_stale_koruenv_socket_for_explicit_ide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv(
        "KORU_AUTOPILOT_SOCKET",
        "/run/user/1000/koru-autopilot-vscode.sock",
    )

    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="none",
        autopilot_ide_cli="cursor",
        resolve_project_lane=lambda _p, _a: None,
    )

    assert probe.socket_path == "/run/user/1000/koru-autopilot-cursor-main.sock"


def test_build_startup_probe_ignores_stale_instance_and_socket_for_explicit_ide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "jetbrains")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv(
        "KORU_AUTOPILOT_SOCKET",
        "/run/user/1000/koru-autopilot-vscode.sock",
    )

    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="none",
        autopilot_ide_cli="cursor",
        resolve_project_lane=lambda _p, _a: None,
    )

    assert probe.socket_path == "/run/user/1000/koru-autopilot-cursor-main.sock"


def test_build_startup_probe_reports_per_ide_socket_for_antigravity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="none",
        autopilot_ide_cli="antigravity",
        resolve_project_lane=lambda _p, _a: None,
    )

    assert probe.socket_path == "/run/user/1000/koru-autopilot-antigravity.sock"
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


def test_apply_agent_lane_environ_nonplugin_terminal_does_not_override_explicit_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "antigravity")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    running = [
        RunningIDE(id="antigravity", label="Antigravity", pid=10, exe="/usr/bin/antigravity"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup.detect_terminal_host_ide_id", return_value="jetbrains"),
    ):
        lane = _apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "antigravity"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "antigravity"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "antigravity"
