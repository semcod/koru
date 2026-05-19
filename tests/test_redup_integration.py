import json
import subprocess
import sys
from pathlib import Path

from koru import redup_integration


def test_changed_scan_command_uses_current_python_module():
    command = redup_integration.redup_changed_scan_command()

    assert command[:4] == [sys.executable, "-m", "redup", "scan"]
    assert "--changed-only" in command


def test_scan_and_check_commands_use_current_python_module(tmp_path: Path):
    assert redup_integration.redup_scan_command(tmp_path) == [
        sys.executable,
        "-m",
        "redup",
        "scan",
        str(tmp_path),
        "--min-lines",
        "10",
    ]
    assert redup_integration.redup_check_command(tmp_path) == [
        sys.executable,
        "-m",
        "redup",
        "check",
        str(tmp_path),
        "--min-lines",
        "10",
    ]


def test_changed_scan_runner_uses_current_python():
    command = redup_integration.redup_changed_scan_runner_command()

    assert command[:4] == [sys.executable, "-m", "koru.redup_integration", "changed-scan"]


def test_run_changed_scan_skips_full_fallback_by_default(monkeypatch, tmp_path: Path):
    output = tmp_path / "wup-changed.json"
    calls: list[list[str]] = []

    monkeypatch.setattr(redup_integration, "_redup_scan_supports", lambda option: False)

    def fake_run(command, check=False):
        calls.append(list(command))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(redup_integration.subprocess, "run", fake_run)
    monkeypatch.delenv(redup_integration.FULL_SCAN_FALLBACK_ENV, raising=False)

    rc = redup_integration.run_changed_scan(output=output)

    assert rc == 0
    assert calls == []
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["groups"] == []
    assert data["meta"]["changed_only"] is True
    assert data["meta"]["skipped"] is True


def test_run_changed_scan_full_fallback_is_opt_in(monkeypatch, tmp_path: Path):
    output = tmp_path / "wup-changed.json"
    calls: list[list[str]] = []

    monkeypatch.setattr(redup_integration, "_redup_scan_supports", lambda option: False)

    def fake_run(command, check=False):
        calls.append(list(command))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(redup_integration.subprocess, "run", fake_run)
    monkeypatch.setenv(redup_integration.FULL_SCAN_FALLBACK_ENV, "1")

    rc = redup_integration.run_changed_scan(output=output, min_lines=12)

    assert rc == 0
    assert calls == [
        [
            sys.executable,
            "-m",
            "redup",
            "scan",
            ".",
            "--format",
            "json",
            "--output",
            str(output),
            "--min-lines",
            "12",
        ]
    ]
