from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from koru import autonomous_runtime
from koru.autonomous import _apply_agent_lane_environ
from koru.autonomous_startup import resolve_autopilot_ide_for_autonomous
from koru.autopilot import default_socket_path
from koru.autopilot.ide import RunningIDE
from koru.ide_router import resolve_ide_route


def test_project_venv_warning_when_running_from_other_venv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "koru").write_text("#!/bin/sh\n", encoding="utf-8")

    other_python = tmp_path / "other" / ".venv" / "bin" / "python"
    other_python.parent.mkdir(parents=True)
    other_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(other_python))

    lines = autonomous_runtime.project_venv_warning_lines(tmp_path)

    assert "lokalne repo .venv" in "\n".join(lines)
    assert str(local_bin) in "\n".join(lines)
    assert str(other_python) in "\n".join(lines)


def test_project_venv_warning_skips_local_venv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "koru").write_text("#!/bin/sh\n", encoding="utf-8")
    local_python = local_bin / "python"
    local_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(local_python))

    assert autonomous_runtime.project_venv_warning_lines(tmp_path) == []


def test_project_venv_warning_skips_symlinked_local_venv_python(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "koru").write_text("#!/bin/sh\n", encoding="utf-8")
    local_python = local_bin / "python"
    target_python = tmp_path / "python-real"
    target_python.write_text("", encoding="utf-8")
    local_python.symlink_to(target_python)
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(local_python))
    monkeypatch.setattr(autonomous_runtime.sys, "prefix", str(tmp_path / ".venv"))

    assert autonomous_runtime.project_venv_warning_lines(tmp_path) == []


def test_project_venv_reexec_argv_when_running_from_other_venv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    local_koru = local_bin / "koru"
    local_koru.write_text("#!/bin/sh\n", encoding="utf-8")
    local_koru.chmod(0o755)

    other_python = tmp_path / "other" / ".venv" / "bin" / "python"
    other_python.parent.mkdir(parents=True)
    other_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(other_python))
    monkeypatch.setattr(autonomous_runtime.sys, "argv", ["koru", "auto", "--max-cycles", "1"])
    monkeypatch.delenv("KORU_AUTONOMOUS_REEXECED", raising=False)
    monkeypatch.delenv("KORU_AUTO_REEXEC", raising=False)

    assert autonomous_runtime.project_venv_reexec_argv(tmp_path) == [
        str(local_koru),
        "auto",
        "--max-cycles",
        "1",
    ]


def test_project_venv_reexec_env_aligns_virtual_env_and_path(
    tmp_path: Path,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    other_bin = tmp_path / "venv" / "bin"
    other_bin.mkdir(parents=True)

    env = autonomous_runtime.project_venv_reexec_env(
        tmp_path,
        base_env={
            "PATH": f"/usr/bin{os.pathsep}{other_bin}",
            "VIRTUAL_ENV": str(tmp_path / "venv"),
        },
    )

    assert env["VIRTUAL_ENV"] == str((tmp_path / ".venv").resolve())
    assert env["PATH"].split(os.pathsep)[0] == str(local_bin.resolve())
    assert str(other_bin) in env["PATH"].split(os.pathsep)


def test_project_venv_reexec_argv_uses_current_project_when_no_project_arg(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    local_koru = local_bin / "koru"
    local_koru.write_text("#!/bin/sh\n", encoding="utf-8")
    local_koru.chmod(0o755)
    other_python = tmp_path / "other" / ".venv" / "bin" / "python"
    other_python.parent.mkdir(parents=True)
    other_python.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(other_python))
    monkeypatch.setattr(autonomous_runtime.sys, "argv", ["koru", "auto"])
    monkeypatch.delenv("KORU_AUTONOMOUS_REEXECED", raising=False)
    monkeypatch.delenv("KORU_AUTO_REEXEC", raising=False)

    assert autonomous_runtime.project_venv_reexec_argv(tmp_path) == [str(local_koru), "auto"]


def test_project_venv_reexec_argv_skips_when_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "koru").write_text("#!/bin/sh\n", encoding="utf-8")
    other_python = tmp_path / "other" / ".venv" / "bin" / "python"
    other_python.parent.mkdir(parents=True)
    other_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(autonomous_runtime.sys, "executable", str(other_python))
    monkeypatch.setenv("KORU_AUTO_REEXEC", "0")

    assert autonomous_runtime.project_venv_reexec_argv(tmp_path) is None


def test_setup_autopilot_daemon_keeps_lane_and_socket_in_sync(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "antigravity")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    args = SimpleNamespace(
        enable_autopilot=True,
        agent_lane="auto",
        autopilot_ide="auto",
        socket=None,
        emit_events="human",
    )

    info_lines: list[str] = []
    captured: dict[str, object] = {}

    def _stdio_info(msg: str, *, fmt: str) -> None:
        info_lines.append(msg)

    def _start_or_reuse_daemon(*, project: Path, socket_path: Path, stdio_format: str):
        captured["project"] = project
        captured["socket_path"] = socket_path
        captured["stdio_format"] = stdio_format
        return None, None, None

    running = [
        RunningIDE(id="antigravity", label="Antigravity", pid=10, exe="/usr/bin/antigravity"),
        RunningIDE(id="jetbrains", label="JetBrains IDE", pid=11, exe="/usr/bin/pycharm"),
    ]

    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=running),
        patch("koru.autonomous_startup.detect_terminal_host_ide_id", return_value="jetbrains"),
    ):
        _client, _daemon, _thread, socket_path = autonomous_runtime.setup_autopilot_daemon(
            args,
            tmp_path,
            apply_agent_lane_environ=_apply_agent_lane_environ,
            resolve_autopilot_ide=resolve_autopilot_ide_for_autonomous,
            resolve_ide_route_fn=resolve_ide_route,
            default_socket_path=default_socket_path,
            start_or_reuse_daemon=_start_or_reuse_daemon,
            stdio_info=_stdio_info,
        )

    assert socket_path is not None
    # Socket and ide match the lane (antigravity) from KORU_AUTOPILOT_INSTANCE
    assert str(socket_path).endswith("koru-autopilot-antigravity.sock")
    assert captured["socket_path"] == socket_path
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "antigravity"
    assert any(
        "autopilot socket decision: lane=antigravity ide=antigravity" in line
        for line in info_lines
    )


def test_build_and_log_startup_probe_reconciles_stale_koruenv_socket(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setenv(
        "KORU_AUTOPILOT_SOCKET",
        "/run/user/1000/koru-autopilot-windsurf-main.sock",
    )

    args = SimpleNamespace(
        enable_autopilot=True,
        agent_lane="auto",
        autopilot_ide="auto",
        socket=None,
        emit_events="human",
    )
    probe = SimpleNamespace(
        resolved_lane="cursor",
        resolved_autopilot_ide="cursor",
        socket_path="/run/user/1000/koru-autopilot-cursor.sock",
    )

    autonomous_runtime.build_and_log_startup_probe(
        args,
        tmp_path,
        apply_agent_lane_environ=lambda *_args, **_kwargs: None,
        build_startup_probe=lambda *_args, **_kwargs: probe,
        format_startup_banner=lambda _probe: [],
        resolve_project_lane=lambda *_args, **_kwargs: "cursor",
        stdio_info=lambda *_args, **_kwargs: None,
    )

    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "cursor"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "cursor"
    assert os.environ["KORU_AUTOPILOT_SOCKET"] == "/run/user/1000/koru-autopilot-cursor.sock"
    for key in ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_SOCKET"):
        os.environ.pop(key, None)


def test_setup_autopilot_daemon_sets_instance_before_default_socket(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    args = SimpleNamespace(
        enable_autopilot=True,
        agent_lane="auto",
        autopilot_ide="vscodium",
        socket=None,
        emit_events="human",
    )
    captured: dict[str, object] = {}

    def _start_or_reuse_daemon(*, project: Path, socket_path: Path, stdio_format: str):
        captured["socket_path"] = socket_path
        return None, None, None

    def _default_socket_path():
        # Use resolved autopilot_ide (vscodium) instead of KORU_AUTOPILOT_INSTANCE
        return Path("/run/user/1000/koru-autopilot-vscodium.sock")

    _client, _daemon, _thread, socket_path = autonomous_runtime.setup_autopilot_daemon(
        args,
        tmp_path,
        apply_agent_lane_environ=_apply_agent_lane_environ,
        resolve_autopilot_ide=resolve_autopilot_ide_for_autonomous,
        resolve_ide_route_fn=resolve_ide_route,
        default_socket_path=_default_socket_path,
        start_or_reuse_daemon=_start_or_reuse_daemon,
        stdio_info=lambda *_args, **_kwargs: None,
    )

    assert socket_path is not None
    assert str(socket_path).endswith("koru-autopilot-vscodium.sock")
    assert captured["socket_path"] == socket_path
    # Explicit --autopilot-ide wins over auto-detect; instance must be set before socket resolution.
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscodium"
