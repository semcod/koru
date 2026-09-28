"""Read-only admission checks before an unattended vendor CLI can edit files.

These checks prevent accidental writes to shared checkouts. They are not a
process sandbox or a substitute for the protected controller's write grant.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class ShellExecutionBlocked(ValueError):
    """No editing process may start for this workspace."""


def _git(project: Path, *args: str) -> str:
    # Resolve the supplied workspace, not a caller's alternate Git index/tree.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ShellExecutionBlocked("Cannot verify shell execution workspace") from exc
    return result.stdout.strip()


def require_shell_execution_workspace(project: Path) -> None:
    """Allow only clean, linked, unmanaged Git workspaces for direct execution.

    Governed workspaces require an independent controller adapter. A repository
    lease JSON or canonical-looking path cannot authorize this direct CLI route.
    """
    if any(
        os.environ.get(key)
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        )
    ):
        raise ShellExecutionBlocked("Git environment overrides can redirect the editor outside its workspace")
    project = Path(os.path.abspath(project))
    if any(path.is_symlink() for path in (project, *project.parents)):
        raise ShellExecutionBlocked("Shell execution through symlink paths is forbidden")
    root = Path(_git(project, "rev-parse", "--show-toplevel"))
    git_dir = Path(_git(project, "rev-parse", "--absolute-git-dir")).resolve()
    common = Path(_git(project, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if git_dir == common:
        raise ShellExecutionBlocked("Shell editing requires an isolated linked worktree, not the primary checkout")
    if any((parent / ".governance").exists() for parent in (root, common.parent)):
        raise ShellExecutionBlocked(
            "Governed shell editing requires protected controller admission; local lease files do not grant it"
        )
    branch = _git(project, "symbolic-ref", "--short", "HEAD")
    remote_default = _git(project, "for-each-ref", "--format=%(symref)", "refs/remotes/origin/HEAD")
    default_branch = remote_default.removeprefix("refs/remotes/origin/")
    if branch in {"main", "master", default_branch}:
        raise ShellExecutionBlocked("Shell editing on a default branch is forbidden")
    if _git(project, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ShellExecutionBlocked("Shell editing requires a clean worktree and index; preserve existing changes")
