"""Regression: doctor must detect PATH ``koru`` that rejects ``koru auto``."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from koru.doctor import _check_koru_runtime_identity, _path_koru_supports_auto_subcommand


def test_path_koru_supports_auto_detects_legacy_rejection() -> None:
    proc = mock.Mock(returncode=2, stdout="", stderr="koru: error: unrecognized arguments: auto\n")
    with mock.patch("koru.doctor_runtime_checks.subprocess.run", return_value=proc):
        assert _path_koru_supports_auto_subcommand("/usr/bin/koru") is False


def test_path_koru_supports_auto_detects_modern_help() -> None:
    proc = mock.Mock(
        returncode=0,
        stdout="usage: koru autonomous\nBootstrap (alias: koru auto)\n",
        stderr="",
    )
    with mock.patch("koru.doctor_runtime_checks.subprocess.run", return_value=proc):
        assert _path_koru_supports_auto_subcommand("/repo/.venv/bin/koru") is True


def test_runtime_identity_warns_when_auto_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "proj"
    venv_bin = project / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "koru").write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    (project / "pyproject.toml").write_text('version = "9.9.9"\n', encoding="utf-8")

    monkeypatch.setattr(
        "koru.doctor_runtime_checks._installed_koru_version",
        lambda: "9.9.9",
    )
    monkeypatch.setattr(
        "koru.doctor_runtime_checks._read_project_version",
        lambda _p: "9.9.9",
    )
    monkeypatch.setattr(
        "koru.doctor_runtime_checks.shutil.which",
        lambda _name: "/home/tom/.pyenv/shims/koru",
    )
    monkeypatch.setattr(
        "koru.doctor_runtime_checks._path_koru_supports_auto_subcommand",
        lambda _p: False,
    )

    status, detail = _check_koru_runtime_identity(project)
    assert status == "warn"
    assert "koru_auto_unsupported=true" in detail
    assert "path_mismatch=true" in detail
