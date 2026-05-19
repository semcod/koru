from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from koru import autonomous_startup as startup
from koru.autonomous import _apply_agent_lane_environ
from koru.autopilot.ide import RunningIDE


def test_resolve_agent_lane_prefers_running_vscode_over_cursor_marker(tmp_path: Path) -> None:
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


def test_format_post_startup_operator_hints_mentions_socket(tmp_path: Path) -> None:
    probe = startup.build_startup_probe(
        tmp_path,
        agent_lane_cli="cursor",
        autopilot_ide_cli="cursor",
        resolve_project_lane=lambda _p, _a: "cursor",
    )
    text = "\n".join(
        startup.format_post_startup_operator_hints(probe, plugin_connected=False),
    )
    assert probe.socket_path in text
    assert "koru autopilot status" in text
    assert "require-plugin" in text
    assert "[!] brak pluginu" in text


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
