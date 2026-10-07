"""Ignored-but-tracked koru runtime files are reported (ticket-442)."""

import subprocess
from pathlib import Path

import pytest

from koru.doctor_constants import PASS, WARN
from koru.doctor_project_health import check_gitignore, tracked_ignored_runtime_files
from koru.scan import scan_gitignore_drift


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".koru").mkdir()
    (tmp_path / ".koru" / "event-store.jsonl").write_text("{}\n")
    (tmp_path / "README.md").write_text("x\n")
    _git(tmp_path, "add", "-f", ".")
    _git(tmp_path, "commit", "-qm", "seed")
    (tmp_path / ".gitignore").write_text(".planfile/.koru/\n.koru/\n")
    return tmp_path


def test_tracked_runtime_file_is_reported(repo: Path) -> None:
    assert tracked_ignored_runtime_files(repo) == [".koru/event-store.jsonl"]
    status, detail = check_gitignore(repo)
    assert status == WARN
    assert "git rm --cached" in detail
    [suggestion] = scan_gitignore_drift(repo)
    assert suggestion.files == (".koru/event-store.jsonl",)


def test_untracked_runtime_passes(repo: Path) -> None:
    _git(repo, "rm", "-q", "--cached", ".koru/event-store.jsonl")
    assert tracked_ignored_runtime_files(repo) == []
    assert check_gitignore(repo)[0] == PASS
    assert scan_gitignore_drift(repo) == []


def test_outside_git_checkout_is_empty(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".planfile/.koru/\n")
    assert tracked_ignored_runtime_files(tmp_path) == []
    assert check_gitignore(tmp_path)[0] == PASS
