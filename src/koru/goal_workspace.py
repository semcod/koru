"""Fail-closed Git target resolution for ``koru goal``."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GoalProjectResolutionError(Exception):
    """A workspace cannot be resolved to one safe Goal target."""

    reason: str
    project: Path
    candidates: tuple[str, ...] = ()

    def __str__(self) -> str:
        suffix = f" Candidates: {', '.join(self.candidates)}." if self.candidates else ""
        return f"{self.reason}{suffix}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "koru.goal-project-resolution/v1",
            "error": "project_resolution_failed",
            "reason": self.reason,
            "project": str(self.project),
            "candidates": list(self.candidates),
        }


def _git(
    project: Path,
    *args: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> subprocess.CompletedProcess[str] | None:
    try:
        return runner(
            ["git", "-C", str(project), *args],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None


def _is_git_root(
    project: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    result = _git(project, "rev-parse", "--show-toplevel", runner=runner)
    if result is None or result.returncode != 0:
        return False
    try:
        return Path(result.stdout.strip()).resolve() == project.resolve()
    except (OSError, RuntimeError):
        return False


def _is_dirty(
    project: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool | None:
    result = _git(
        project,
        "status",
        "--porcelain",
        "--untracked-files=normal",
        runner=runner,
    )
    if result is None or result.returncode != 0:
        return None
    return bool(result.stdout)


def _explicit_project(
    workspace: Path,
    repo: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> Path:
    relative = Path(repo)
    if relative.is_absolute():
        raise GoalProjectResolutionError(
            "--repo must be a relative path contained by --project",
            workspace,
        )
    try:
        candidate = (workspace / relative).resolve()
    except (OSError, RuntimeError) as exc:
        raise GoalProjectResolutionError(
            "--repo cannot be resolved safely inside --project",
            workspace,
            (repo,),
        ) from exc
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise GoalProjectResolutionError(
            "--repo escapes the --project workspace",
            workspace,
        ) from exc
    if not candidate.is_dir() or not _is_git_root(candidate, runner=runner):
        raise GoalProjectResolutionError(
            "--repo must identify a Git repository root contained by --project",
            workspace,
            (repo,),
        )
    return candidate


def resolve_goal_project(
    project: Path,
    repo: str | None = None,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Path:
    """Resolve one repository before Goal or a remediation agent may run."""
    try:
        workspace = project.expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise GoalProjectResolutionError(
            "--project cannot be resolved safely",
            project,
        ) from exc
    if not workspace.is_dir():
        raise GoalProjectResolutionError(
            "--project is not a directory",
            workspace,
        )
    if repo is not None:
        return _explicit_project(workspace, repo, runner=runner)
    if _is_git_root(workspace, runner=runner):
        return workspace

    try:
        children = sorted(workspace.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise GoalProjectResolutionError(
            "--project cannot be inspected for Git repositories",
            workspace,
        ) from exc
    repositories = tuple(
        child
        for child in children
        if child.is_dir()
        and not child.is_symlink()
        and _is_git_root(child, runner=runner)
    )
    dirty: list[Path] = []
    unreadable: list[str] = []
    for candidate in repositories:
        state = _is_dirty(candidate, runner=runner)
        if state is None:
            unreadable.append(candidate.name)
        elif state:
            dirty.append(candidate)

    if unreadable:
        raise GoalProjectResolutionError(
            "Git status failed for workspace repositories; select only after inspection",
            workspace,
            tuple(unreadable),
        )
    if len(dirty) == 1:
        return dirty[0]
    if not repositories:
        raise GoalProjectResolutionError(
            "--project is neither a Git repository nor an umbrella with Git children",
            workspace,
        )
    if not dirty:
        raise GoalProjectResolutionError(
            "umbrella workspace has no dirty repository; use --repo to select one",
            workspace,
            tuple(candidate.name for candidate in repositories),
        )
    raise GoalProjectResolutionError(
        "umbrella workspace has multiple dirty repositories; use --repo to select one",
        workspace,
        tuple(candidate.name for candidate in dirty),
    )
