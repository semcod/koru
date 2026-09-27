"""Tests for Taskand operational profile and Twinerd sandbox integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from koru.queue.runners import (
    _find_twinerd_cli,
    _resolve_sandbox_project,
    create_twinerd_sandbox,
    run_taskand_request,
)


def test_find_twinerd_cli_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_bin = tmp_path / "twinerd"
    fake_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)
    monkeypatch.setenv("TWINERD_BIN", str(fake_bin))

    cli = _find_twinerd_cli()
    assert cli == fake_bin


def test_find_twinerd_cli_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TWINERD_BIN", raising=False)
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr("pathlib.Path.is_file", lambda _self: False)

    cli = _find_twinerd_cli()
    assert cli is None


def test_create_twinerd_sandbox_no_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.queue.runners._find_twinerd_cli", lambda: None)
    res = create_twinerd_sandbox(tmp_path)
    assert res is None


def test_create_twinerd_sandbox_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin" / "twinerd"
    fake_mount = tmp_path / "sandboxes" / "twin-1"

    def fake_run(cmd: list[str], cwd: Path) -> Any:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({
            "status": "ok",
            "name": "twin-1",
            "driver": "overlayfs",
            "mount_point": str(fake_mount),
        })
        return mock_proc

    monkeypatch.setattr("koru.queue.runners._run_captured_subprocess", fake_run)
    res = create_twinerd_sandbox(tmp_path, name="twin-1", cli_bin=fake_bin)
    assert res is not None
    assert res["status"] == "ok"
    assert res["mount_point"] == str(fake_mount)


def test_create_twinerd_sandbox_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin" / "twinerd"

    def fake_run(cmd: list[str], cwd: Path) -> Any:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "error creating sandbox"
        return mock_proc

    monkeypatch.setattr("koru.queue.runners._run_captured_subprocess", fake_run)
    res = create_twinerd_sandbox(tmp_path, name="twin-1", cli_bin=fake_bin)
    assert res is None


def test_create_twinerd_sandbox_invalid_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin" / "twinerd"

    def fake_run(cmd: list[str], cwd: Path) -> Any:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "not-json"
        return mock_proc

    monkeypatch.setattr("koru.queue.runners._run_captured_subprocess", fake_run)
    res = create_twinerd_sandbox(tmp_path, name="twin-1", cli_bin=fake_bin)
    assert res is None


def test_resolve_sandbox_project_no_sandbox(tmp_path: Path) -> None:
    proj, info = _resolve_sandbox_project(tmp_path, {})
    assert proj == tmp_path
    assert info is None

    proj2, info2 = _resolve_sandbox_project(tmp_path, {"sandbox": "other"})
    assert proj2 == tmp_path
    assert info2 is None


def test_resolve_sandbox_project_twinerd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_mount = tmp_path / "sandboxes" / "twin-sandbox"

    def fake_create(source_project: Path, name: str = "twin-sandbox") -> dict[str, Any]:
        return {
            "status": "ok",
            "name": name,
            "mount_point": str(fake_mount),
        }

    monkeypatch.setattr("koru.queue.runners.create_twinerd_sandbox", fake_create)
    proj, info = _resolve_sandbox_project(tmp_path, {"sandbox": "twinerd", "twin_name": "custom-twin"})
    assert proj == fake_mount
    assert info is not None
    assert info["name"] == "custom-twin"


def test_run_taskand_request_with_sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_mount = tmp_path / "sandboxes" / "twin-sandbox"

    monkeypatch.setattr(
        "koru.queue.runners.create_twinerd_sandbox",
        lambda source_project, name="twin-sandbox": {
            "status": "ok",
            "name": name,
            "mount_point": str(fake_mount),
        },
    )

    recorded_projects: list[Path] = []

    def fake_find_cli(project: Path) -> Path | None:
        recorded_projects.append(project)
        fake_bin = tmp_path / "taskand"
        fake_bin.touch()
        return fake_bin

    def fake_run_cli(cli_bin: Path, uri: str, data: dict[str, Any], project: Path) -> Any:
        from koru.queue.runners import TaskandRunResult
        return TaskandRunResult(
            returncode=0,
            stdout="ok",
            stderr="",
            data={"result": "pass"},
        )

    monkeypatch.setattr("koru.queue.runners._probe_taskand_gateway", lambda _url: False)
    monkeypatch.setattr("koru.queue.runners._find_taskand_cli", fake_find_cli)
    monkeypatch.setattr("koru.queue.runners._run_taskand_cli_call", fake_run_cli)

    request = {
        "uri": "proc://test/run",
        "sandbox": "twinerd",
        "twin_name": "ops-twin",
    }
    result = run_taskand_request(request, tmp_path)
    assert result.returncode == 0
    assert result.stdout == "ok"
    assert recorded_projects == [fake_mount]

