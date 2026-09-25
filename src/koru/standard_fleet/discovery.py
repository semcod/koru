"""Standard-source loading and governed-repository discovery."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from koru.standard_fleet.git_observation import (
    GitRunner,
    _clean_text,
    _read_text,
    _subprocess_git,
)
from koru.standard_fleet.models import StandardRelease

_PRUNE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".worktrees",
    "worktrees",
    "build",
    "dist",
    "__pycache__",
}


def load_standard_release(
    source_root: Path,
    *,
    git_runner: GitRunner = _subprocess_git,
) -> StandardRelease:
    """Load a clean, immutable local standard source observation."""
    source_root = source_root.resolve()
    version = _read_text(source_root / "VERSION")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("standard source VERSION is not a semantic version")
    dirty = git_runner(source_root, ["status", "--porcelain"])
    if dirty.returncode != 0:
        raise ValueError("standard source Git status could not be observed")
    if dirty.stdout.strip():
        raise ValueError("standard source checkout is dirty")
    revision_result = git_runner(source_root, ["rev-parse", "--verify", "HEAD"])
    revision = _clean_text(revision_result.stdout).lower()
    if revision_result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("standard source HEAD is not a full commit SHA")
    return StandardRelease(version, revision, source_root)


def discover_governed_repositories(workspace: Path) -> list[Path]:
    """Find repositories with an adopted governance lock, without worktrees."""
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise NotADirectoryError(workspace)
    found: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(workspace):
        dirnames[:] = [name for name in dirnames if name not in _PRUNE_DIRS]
        candidate = Path(dirpath)
        if (candidate / ".governance" / "manifest.lock.json").is_file():
            found.append(candidate)
            dirnames[:] = []
    return sorted(found)


def _lock_standard(repo: Path) -> tuple[str | None, str | None, str | None]:
    path = repo / ".governance" / "manifest.lock.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None, "invalid-standard-lock"
    standard = data.get("standard") if isinstance(data, dict) else None
    if not isinstance(standard, dict):
        return None, None, "invalid-standard-lock"
    version = standard.get("version")
    revision = standard.get("sourceRevision")
    if not isinstance(version, str) or not isinstance(revision, str):
        return None, None, "invalid-standard-lock"
    return version.strip(), revision.strip().lower(), None
