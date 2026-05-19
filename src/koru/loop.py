"""Closed-loop execution helpers for semcod repositories."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Protocol

_GLOB_CHARS = frozenset("*?[")


class CommandResult(Protocol):
    """Protocol for subprocess-like command results."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RunRecord:
    """Single command execution result for one repository in one attempt."""

    repository: Path
    attempt: int
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class LoopReport:
    """Aggregated execution report for a full closed-loop run."""

    records: tuple[RunRecord, ...]
    succeeded: tuple[Path, ...]
    failed: tuple[Path, ...]
    rounds_executed: int


def _search_root_for_include(workspace: Path, include_pattern: str) -> Path:
    """Return the narrowest safe root to scan before applying include_pattern."""
    normalized = include_pattern.strip().replace("\\", "/")
    literal_parts: list[str] = []

    for part in normalized.split("/"):
        if not part or any(char in part for char in _GLOB_CHARS):
            break
        literal_parts.append(part)

    if not literal_parts:
        return workspace

    return workspace.joinpath(*literal_parts)


def discover_repositories(workspace: Path, include_pattern: str = "semcod/*") -> list[Path]:
    """Return git repositories under workspace matching include_pattern."""
    workspace = workspace.resolve()
    search_root = _search_root_for_include(workspace, include_pattern).resolve()
    if not search_root.exists():
        return []

    repositories: list[Path] = []
    for git_dir in search_root.rglob(".git"):
        candidate = git_dir.parent
        rel_path = candidate.relative_to(workspace).as_posix()
        if include_pattern == "*" or fnmatch(rel_path, include_pattern):
            repositories.append(candidate)
    return sorted(set(repositories))


def _default_runner(command: Sequence[str], repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )


def run_closed_loop(
    *,
    command: Sequence[str],
    repositories: Iterable[Path],
    max_rounds: int = 3,
    runner: Callable[[Sequence[str], Path], CommandResult] = _default_runner,
) -> LoopReport:
    """Run a command repeatedly on failed repositories until all pass or rounds end."""
    pending = sorted(set(Path(repo).resolve() for repo in repositories))
    records: list[RunRecord] = []

    for attempt in range(1, max_rounds + 1):
        if not pending:
            break

        failures: list[Path] = []
        for repository in pending:
            result = runner(command, repository)
            records.append(
                RunRecord(
                    repository=repository,
                    attempt=attempt,
                    exit_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                ),
            )
            if result.returncode != 0:
                failures.append(repository)

        pending = failures

    by_repository: dict[Path, RunRecord] = {}
    for record in records:
        by_repository[record.repository] = record

    succeeded = tuple(sorted(repo for repo, rec in by_repository.items() if rec.exit_code == 0))
    failed = tuple(sorted(repo for repo, rec in by_repository.items() if rec.exit_code != 0))
    rounds_executed = max((record.attempt for record in records), default=0)

    return LoopReport(
        records=tuple(records),
        succeeded=succeeded,
        failed=failed,
        rounds_executed=rounds_executed,
    )
