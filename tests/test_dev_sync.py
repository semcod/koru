from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from koru.dev_sync import sync_developer_packages


def test_sync_developer_packages_installs_existing_repos(tmp_path: Path) -> None:
    repo = tmp_path / "redup"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='redup'\n", encoding="utf-8")
    calls: list[tuple[list[str], Path]] = []

    def runner(command, cwd):
        calls.append((list(command), cwd))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    results = sync_developer_packages(root=tmp_path, packages=("redup", "wup"), runner=runner)

    assert [item.status for item in results] == ["synced", "missing"]
    assert calls == [([sys.executable, "-m", "pip", "install", "-e", str(repo)], repo)]


def test_sync_developer_packages_skips_dirty_pull(tmp_path: Path) -> None:
    repo = tmp_path / "koru"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, cwd):
        calls.append(list(command))
        if command[:3] == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(command, 0, stdout=" M file.py\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    results = sync_developer_packages(root=tmp_path, packages=("koru",), pull=True, runner=runner)

    assert results[0].status == "pull-skipped"
    assert "dirty worktree" in results[0].detail
    assert calls == [["git", "status", "--porcelain"]]
