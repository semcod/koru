"""Tests for the packaged ``koru autoloop`` wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from koru.autoloop_cli import _packaged_script_path, autoloop_main


def test_packaged_autoloop_script_matches_repo_script() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert _packaged_script_path().read_text() == (
        repo_root / "scripts/koru-autoloop.sh"
    ).read_text()


def test_autoloop_print_script(capsys: pytest.CaptureFixture[str]) -> None:
    assert autoloop_main(["--print-script"]) == 0
    assert "koru-autoloop.sh" in capsys.readouterr().out


def test_autoloop_runs_packaged_script_with_env_assignments(tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_call(cmd: list[str], env: dict[str, str]) -> int:
        calls.append((cmd, env))
        return 0

    with mock.patch.object(subprocess, "call", side_effect=fake_call):
        rc = autoloop_main(
            [
                "--project",
                str(tmp_path),
                "TICKET_SOURCES=all",
                "ENABLE_SCAN=true",
            ],
        )

    assert rc == 0
    assert calls
    cmd, env = calls[0]
    assert cmd[:1] == ["bash"]
    assert cmd[1].endswith("koru-autoloop.sh")
    assert env["PROJECT"] == str(tmp_path)
    assert env["TICKET_SOURCES"] == "all"
    assert env["ENABLE_SCAN"] == "true"

