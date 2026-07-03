"""Doctor must expose toolchain versions and PATH-vs-import skew (2026-07-03 trap)."""

from __future__ import annotations

from pathlib import Path

import koru.doctor_project_health as dph
from koru.doctor_project_health import check_ecosystem_versions


def test_reports_all_toolchain_packages(tmp_path: Path) -> None:
    status, detail = check_ecosystem_versions(tmp_path)
    for pkg in ("tillm=", "gillm=", "planfile=", "koruide="):
        assert pkg in detail


def test_warns_on_cli_import_skew(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(dph, "_installed_version", lambda p: "0.1.104")
    monkeypatch.setattr(dph, "planfile_version_argv", lambda: ["true"])

    class _Proc:
        stdout = "Planfile CLI version: 0.1.106"
        stderr = ""

    monkeypatch.setattr(dph.subprocess, "run", lambda *a, **k: _Proc())

    status, detail = check_ecosystem_versions(tmp_path)

    assert "0.1.106" in detail and "0.1.104" in detail
    assert "shadow" in detail


def test_pass_when_cli_matches_import(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(dph, "_installed_version", lambda p: "0.1.106")
    monkeypatch.setattr(dph, "planfile_version_argv", lambda: ["true"])

    class _Proc:
        stdout = "Planfile CLI version: 0.1.106"
        stderr = ""

    monkeypatch.setattr(dph.subprocess, "run", lambda *a, **k: _Proc())

    status, detail = check_ecosystem_versions(tmp_path)

    assert "shadow" not in detail
