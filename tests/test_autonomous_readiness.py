"""Regression tests for autonomous readiness gates."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from koru.autonomous_readiness import (
    check_daemon_client_alignment,
    check_lane_terminal_socket_alignment,
    check_queue_runner_contention,
    check_runtime_consistency,
    check_workspace_socket_ownership,
    plugin_workspace_covers_project,
    run_plugin_reconnect_pipeline,
)
from koru.autonomy.environment import SocketHealth


def test_runtime_consistency_warns_when_package_differs_from_pyproject(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "koru"\nversion = "0.1.309"\n',
        encoding="utf-8",
    )
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python3").write_text("", encoding="utf-8")
    (tmp_path / ".venv" / "bin" / "koru").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "koru.autonomous_readiness._installed_koru_version",
        lambda: "0.1.308",
    )
    monkeypatch.setattr(
        "koru.autonomous_readiness._check_python_venv_alignment",
        lambda _p: ("pass", "aligned"),
    )

    result = check_runtime_consistency(tmp_path, launcher_executable="/usr/bin/python3")
    codes = {i.code for i in result.issues}
    assert "koru_package_version_drift" in codes
    assert result.ok is True


def test_runtime_consistency_fail_fast_when_strict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "koru"\nversion = "0.1.309"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "koru.autonomous_readiness._installed_koru_version",
        lambda: "0.1.308",
    )
    monkeypatch.setattr(
        "koru.autonomous_readiness._check_python_venv_alignment",
        lambda _p: ("pass", "aligned"),
    )

    result = check_runtime_consistency(
        tmp_path,
        launcher_executable="/usr/bin/python3",
        strict=True,
    )
    assert result.ok is False
    assert result.primary_fix is not None


def test_daemon_client_alignment_detects_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "koru.autonomous_readiness.daemon_status_compatible",
        lambda _s: (False, "daemon version 0.1.308 != current koru 0.1.309"),
    )
    result = check_daemon_client_alignment({"daemon_version": "0.1.308"})
    assert result.ok is False
    assert any(i.code == "daemon_version_mismatch" for i in result.issues)


def test_plugin_workspace_covers_project() -> None:
    status = {
        "plugins": [
            {
                "ide": "cursor",
                "workspaceFolders": ["/home/tom/proj"],
            }
        ]
    }
    ok, reason = plugin_workspace_covers_project(
        status,
        "cursor",
        Path("/home/tom/proj"),
    )
    assert ok is True
    assert reason == ""

    bad, bad_reason = plugin_workspace_covers_project(
        status,
        "cursor",
        Path("/other/root"),
    )
    assert bad is False
    assert "workspaceFolders" in bad_reason


def test_socket_stale_detected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sock = tmp_path / "koru-autopilot-cursor.sock"
    sock.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "koru.autonomous_readiness.probe_socket_health",
        lambda _p: SocketHealth(path=sock, exists=True, listening=False, stale=True),
    )
    result = check_workspace_socket_ownership(
        tmp_path,
        sock,
        None,
        autopilot_ide="cursor",
    )
    assert result.ok is False
    assert any(i.code == "socket_stale" for i in result.issues)


def test_live_status_metadata_wins_over_stale_project_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sock = tmp_path / "koru-autopilot-vscodium.sock"
    sock.write_text("", encoding="utf-8")
    live_inode = sock.stat().st_ino
    project_meta = tmp_path / ".planfile" / ".koru" / "koru-autopilot-vscodium.daemon.json"
    project_meta.parent.mkdir(parents=True)
    project_meta.write_text(
        json.dumps(
            {
                "pid": 999999,
                "socket": str(sock),
                "socket_inode": live_inode + 10,
                "project": str(tmp_path),
            }
        ),
        encoding="utf-8",
    )
    status = {
        "daemon_metadata": {
            "pid": os.getpid(),
            "socket": str(sock),
            "socket_inode": live_inode,
            "project": str(tmp_path),
            "python_executable": os.sys.executable,
        },
        "plugins": [
            {
                "ide": "vscodium",
                "workspaceFolders": [str(tmp_path)],
            }
        ],
    }
    monkeypatch.setattr(
        "koru.autonomous_readiness.probe_socket_health",
        lambda _p: SocketHealth(path=sock, exists=True, listening=True, stale=False),
    )

    result = check_workspace_socket_ownership(
        tmp_path,
        sock,
        status,
        autopilot_ide="vscodium",
    )

    assert result.ok is True
    assert not result.issues


def test_plugin_reconnect_pipeline_succeeds_on_second_attempt() -> None:
    calls = {"reload": 0, "wait": 0}

    def reload() -> bool:
        calls["reload"] += 1
        return True

    def wait(_timeout: float) -> bool:
        calls["wait"] += 1
        return calls["wait"] >= 2

    ok = run_plugin_reconnect_pipeline(
        reload_window=reload,
        wait_connected=wait,
        attempts=2,
        base_timeout_seconds=1.0,
        poll_interval_seconds=0.01,
        sleep=lambda _s: None,
    )
    assert ok is True
    assert calls["reload"] >= 1


def test_lane_terminal_mismatch_when_integrated_terminal_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "koru.autonomous_readiness.detect_terminal_host_ide_id",
        lambda: "vscode",
    )
    monkeypatch.setattr(
        "koruide.ide.detect_terminal_host_context",
        lambda: type("Ctx", (), {"integrated": True, "kind": "integrated"})(),
    )
    result = check_lane_terminal_socket_alignment(
        autopilot_ide="cursor",
        lane_instance="cursor-main",
        socket_path=None,
        terminal_integrated=True,
    )
    assert result.ok is True  # cross-IDE is now a warning, not a failure
    mismatch_issues = [i for i in result.issues if i.code == "terminal_lane_mismatch"]
    assert len(mismatch_issues) == 1
    assert mismatch_issues[0].severity == "warn"


def test_socket_lane_mismatch_detected(tmp_path: Path) -> None:
    sock = tmp_path / "koru-autopilot-vscodium.sock"
    result = check_lane_terminal_socket_alignment(
        autopilot_ide="cursor",
        lane_instance="cursor-main",
        socket_path=sock,
        terminal_ide="cursor",
        terminal_integrated=False,
    )
    assert any(i.code == "socket_lane_mismatch" for i in result.issues)


def test_queue_runner_contention_warns_when_lock_held(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import fcntl

    lock_path = tmp_path / ".planfile" / ".koru" / "queue-runner.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        result = check_queue_runner_contention(tmp_path)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert any(i.code == "queue_runner_lock_held" for i in result.issues)
