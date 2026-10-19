"""Queue promotion must honor real Git hooks and preserve rejected work."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from koru.queue.workspace import commit_worktree
from tests import _repolab


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = _repolab.git_repo(tmp_path)
    _repolab.commit_file(root, "change.txt", "original\n")
    _repolab.commit_file(root, "unrelated.txt", "preserve\n")
    hooks = root / ".git" / "promotion-hooks"
    hooks.mkdir()
    git(root, "config", "core.hooksPath", str(hooks))
    (root / "change.txt").write_text("proposed\n")
    (root / "unrelated.txt").write_text("unrelated edit\n")
    (root / "untracked.txt").write_text("untracked evidence\n")
    return root


def install_hook(root: Path, exit_code: int) -> Path:
    marker = root / ".git" / "promotion-hook-ran"
    hook = root / ".git" / "promotion-hooks" / "pre-commit"
    hook.write_text(
        '#!/bin/sh\n'
        'printf "hook ran\\n" > "$(git rev-parse --git-dir)/promotion-hook-ran"\n'
        'echo "promotion hook decision" >&2\n'
        f"exit {exit_code}\n"
    )
    hook.chmod(0o755)
    return marker


@pytest.mark.parametrize("governed", [False, True])
@pytest.mark.parametrize("branch", ["ticket/475-run-check", "koru/check", "feature-run-check", "feature/check"])
def test_rejected_hook_preserves_head_and_patch(repository: Path, monkeypatch, governed: bool, branch: str) -> None:
    monkeypatch.setenv("KORU_GOVERNED_WORKTREE_OK", "1" if governed else "0")
    marker = install_hook(repository, 42)
    before = git(repository, "rev-parse", "HEAD")

    ok, detail = commit_worktree(repository, branch, "reviewed patch", ("change.txt",))

    assert marker.read_text() == "hook ran\n"
    assert not ok
    assert "promotion hook decision" in detail
    assert git(repository, "rev-parse", "HEAD") == before
    assert (repository / "change.txt").read_text() == "proposed\n"
    assert git(repository, "diff", "--cached", "--name-only") == "change.txt"
    assert (repository / "unrelated.txt").read_text() == "unrelated edit\n"
    assert (repository / "untracked.txt").read_text() == "untracked evidence\n"


@pytest.mark.parametrize("governed", [False, True])
def test_accepted_hook_commits_only_declared_paths(repository: Path, monkeypatch, governed: bool) -> None:
    monkeypatch.setenv("KORU_GOVERNED_WORKTREE_OK", "1" if governed else "0")
    marker = install_hook(repository, 0)
    before = git(repository, "rev-parse", "HEAD")

    ok, head = commit_worktree(repository, "ticket/475-run-check", "reviewed patch", ("change.txt",))

    assert marker.read_text() == "hook ran\n"
    assert ok, head
    assert head == git(repository, "rev-parse", "HEAD") != before
    assert git(repository, "diff-tree", "--no-commit-id", "--name-only", "-r", head) == "change.txt"
    assert git(repository, "show", "HEAD:unrelated.txt") == "preserve"
    assert (repository / "unrelated.txt").read_text() == "unrelated edit\n"
    assert (repository / "untracked.txt").read_text() == "untracked evidence\n"
