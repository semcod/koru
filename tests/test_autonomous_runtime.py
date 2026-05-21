from __future__ import annotations

from pathlib import Path

from koru import autonomous_runtime


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
