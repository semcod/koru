from __future__ import annotations

import os
import subprocess
from pathlib import Path

from koru.git_attribution import (
    KORU_AGENT_COAUTHOR_TRAILER,
    install_koru_agent_coauthor_hook,
)


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_install_hook_adds_koru_coauthor_to_commit(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Human User")
    _git(tmp_path, "config", "user.email", "human@example.com")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")

    result = install_koru_agent_coauthor_hook(tmp_path)

    assert result.status == "installed"
    assert result.hook_path is not None
    assert os.access(result.hook_path, os.X_OK)

    _git(tmp_path, "commit", "-m", "chore: initial")
    message = _git(tmp_path, "log", "-1", "--format=%B").stdout

    assert "chore: initial" in message
    assert KORU_AGENT_COAUTHOR_TRAILER in message


def test_install_hook_is_idempotent(tmp_path: Path) -> None:
    _git(tmp_path, "init")

    install_koru_agent_coauthor_hook(tmp_path)
    install_koru_agent_coauthor_hook(tmp_path)

    hook = tmp_path / ".git" / "hooks" / "prepare-commit-msg"
    text = hook.read_text(encoding="utf-8")
    assert text.count(KORU_AGENT_COAUTHOR_TRAILER) == 2


def test_install_hook_can_be_disabled(tmp_path: Path, monkeypatch) -> None:
    _git(tmp_path, "init")
    monkeypatch.setenv("KORU_AGENT_COAUTHOR", "0")

    result = install_koru_agent_coauthor_hook(tmp_path)

    assert result.status == "disabled"
    assert not (tmp_path / ".git" / "hooks" / "prepare-commit-msg").exists()
