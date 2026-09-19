"""Bounded read-only Git observations for one repository.

Every helper takes an injectable ``git_runner`` so tests and the scanner can
observe real checkouts without shelling out implicitly.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from koru.standard_fleet.models import GitObservation, GitRunner

_REMOTE_IDENTITY = re.compile(r"(?:git@|https://|ssh://git@)(?:[^/:]+)[/:]([^/]+)/(.+?)(?:\.git)?/?$")


def _subprocess_git(repo: Path, args: Sequence[str]) -> GitObservation:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return GitObservation(127, stderr=str(exc))
    return GitObservation(completed.returncode, completed.stdout, completed.stderr)


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _origin_identity(repo: Path, *, git_runner: GitRunner) -> str:
    observed = git_runner(repo, ["remote", "get-url", "origin"])
    remote = _clean_text(observed.stdout)
    match = _REMOTE_IDENTITY.match(remote)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return f"local:{repo}"


def _is_linked_worktree(repo: Path, *, git_runner: GitRunner) -> bool:
    """Return whether *repo* is a linked worktree rather than its primary checkout."""
    git_dir_result = git_runner(repo, ["rev-parse", "--git-dir"])
    common_dir_result = git_runner(repo, ["rev-parse", "--git-common-dir"])
    if git_dir_result.returncode != 0 or common_dir_result.returncode != 0:
        return False
    git_dir = Path(_clean_text(git_dir_result.stdout))
    common_dir = Path(_clean_text(common_dir_result.stdout))
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    if not common_dir.is_absolute():
        common_dir = repo / common_dir
    return git_dir.resolve() != common_dir.resolve()


def _git_state(repo: Path, *, git_runner: GitRunner) -> tuple[bool, int, str | None]:
    dirty_result = git_runner(repo, ["status", "--porcelain"])
    if dirty_result.returncode != 0:
        return False, 0, "git-status-unavailable"
    worktrees_result = git_runner(repo, ["worktree", "list", "--porcelain"])
    if worktrees_result.returncode != 0:
        return bool(worktrees_result.stdout.strip()), 0, "git-worktree-unavailable"
    worktree_lines = [line for line in worktrees_result.stdout.splitlines() if line.startswith("worktree ")]
    return bool(dirty_result.stdout.strip()), max(0, len(worktree_lines) - 1), None


@dataclass(frozen=True)
class _RepositoryObservation:
    path: Path
    identity: str
    dirty: bool
    linked_worktrees: int
    git_error: str | None
    linked_worktree: bool


def _observe_repository(repo: Path, *, git_runner: GitRunner) -> _RepositoryObservation:
    dirty, linked_worktrees, git_error = _git_state(repo, git_runner=git_runner)
    return _RepositoryObservation(
        path=repo.resolve(),
        identity=_origin_identity(repo, git_runner=git_runner),
        dirty=dirty,
        linked_worktrees=linked_worktrees,
        git_error=git_error,
        linked_worktree=_is_linked_worktree(repo, git_runner=git_runner),
    )
