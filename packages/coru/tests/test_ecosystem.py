"""Tests for coru ecosystem sync."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from coru import ecosystem
from coru.ecosystem import sync_ecosystem, sync_python_packages


def test_sync_python_packages_editable_monorepo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (tmp_path / "src" / "koru").mkdir(parents=True)
    (tmp_path / "packages" / "koruenv").mkdir(parents=True)
    (tmp_path / "packages" / "koruenv" / "pyproject.toml").write_text(
        "[project]\nname='koruenv'\n",
        encoding="utf-8",
    )
    (tmp_path / "packages" / "coru").mkdir(parents=True)
    (tmp_path / "packages" / "coru" / "pyproject.toml").write_text(
        "[project]\nname='coru'\n",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def _runner(cmd: list[str]) -> int:
        calls.append(list(cmd))
        return 0

    step = sync_python_packages(tmp_path, python="/usr/bin/python3", runner=_runner)
    assert step.ok
    assert calls
    assert "-U" in calls[0]
    assert "-e" in calls[0]


def test_sync_ecosystem_python_only(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (tmp_path / "src" / "koru").mkdir(parents=True)

    report = sync_ecosystem(
        tmp_path,
        python=True,
        plugins=False,
        repair=False,
        python_executable="/usr/bin/python3",
        pip_runner=lambda _cmd: 0,
    )
    assert report.ok
    assert any(step.name == "python_packages" for step in report.steps)


def test_sync_ecosystem_runs_plugin_and_repair_steps(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (tmp_path / "src" / "koru").mkdir(parents=True)

    calls: list[tuple[str, list[str]]] = []

    def _koru_runner(ide: str, args: list[str]) -> int:
        calls.append((ide, list(args)))
        return 0

    report = sync_ecosystem(
        tmp_path,
        ide="windsurf",
        python=False,
        plugins=True,
        repair=True,
        koru_runner=_koru_runner,
    )
    assert report.ok
    assert any(ide == "windsurf" and "install-plugin" in " ".join(args) for ide, args in calls)
    assert any(ide == "windsurf" and "manage" in " ".join(args) for ide, args in calls)
    assert any(ide == "windsurf" and "self" in " ".join(args) for ide, args in calls)


def test_sync_all_ides_skips_antigravity_to_avoid_gui_window_spam(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (tmp_path / "src" / "koru").mkdir(parents=True)
    monkeypatch.setattr(
        ecosystem,
        "_detect_running_plugin_ides",
        lambda: ["antigravity", "vscodium"],
    )

    calls: list[tuple[str, list[str]]] = []

    def _koru_runner(ide: str, args: list[str]) -> int:
        calls.append((ide, list(args)))
        return 0

    report = sync_ecosystem(
        tmp_path,
        python=False,
        plugins=True,
        repair=True,
        all_running_ides=True,
        koru_runner=_koru_runner,
    )

    assert report.ok
    assert {ide for ide, _args in calls} == {"vscodium"}


def test_detect_running_plugin_ides_excludes_antigravity_for_all_ides_sync(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "koru.autopilot.ide.detect_running_ides",
        lambda: [
            SimpleNamespace(id="antigravity"),
            SimpleNamespace(id="cursor"),
            SimpleNamespace(id="vscodium"),
        ],
    )

    assert ecosystem._detect_running_plugin_ides() == ["cursor", "vscodium"]


def test_sync_plugins_for_ide_does_not_pass_project_flag() -> None:
    from coru.ecosystem import sync_plugins_for_ide

    calls: list[tuple[str, list[str]]] = []

    def _koru_runner(ide: str, args: list[str]) -> int:
        calls.append((ide, list(args)))
        return 0

    step = sync_plugins_for_ide("cursor", koru_runner=_koru_runner)
    assert step.ok
    assert calls == [
        (
            "cursor",
            ["autopilot", "install-plugin", "--ide", "cursor", "--format", "json"],
        )
    ]
