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


def test_project_venv_reexec_argv_uses_current_project_when_no_project_arg(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_bin = tmp_path / ".venv" / "bin"
    local_bin.mkdir(parents=True)
    local_koru = local_bin / "koru"
    local_koru.write_text("#!/bin/sh\n", encoding="utf-8")
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
