"""Closed-loop execution helpers for semcod repositories."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
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


_DISCOVERY_LIMIT = 100_000
_DISCOVERY_EXCLUDES = frozenset({
    "node_modules", "vendor", "venv", "worktrees", "__pycache__", "dist", "build",
})


def discover_repositories(workspace: Path, include_pattern: str = "semcod/*") -> list[Path]:
    """Select checkout roots using segment globs and a bounded directory traversal.

    ``*`` never crosses a slash. Explicit literal paths may select linked
    worktrees; wildcard discovery skips hidden/generated trees and symlinks.
    ``**`` is recursive but stops at checkout roots.
    """
    workspace = workspace.resolve()
    normalized = include_pattern.strip().replace("\\", "/")
    parts = tuple(part for part in normalized.split("/") if part and part != ".")
    if normalized.startswith("/") or ".." in parts or len(parts) > 64 or not parts:
        raise ValueError("include must be a bounded path relative to the workspace")
    remaining = _DISCOVERY_LIMIT
    repositories: set[Path] = set()
    seen: set[tuple[Path, int]] = set()

    def visit(directory: Path, index: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            raise ValueError("repository discovery exceeded its entry budget")
        if len(directory.relative_to(workspace).parts) > 64:
            raise ValueError("repository discovery exceeded its depth budget")
        state = (directory, index)
        if state in seen or directory.is_symlink() or not directory.is_dir():
            return
        seen.add(state)
        if index == len(parts):
            if (directory / ".git").is_dir() or (directory / ".git").is_file():
                repositories.add(directory)
            return
        segment = parts[index]
        if not any(char in segment for char in _GLOB_CHARS):
            visit(directory / segment, index + 1)
            return
        if segment == "**":
            visit(directory, index + 1)
            if (directory / ".git").exists():
                return
        with os.scandir(directory) as entries:
            for entry in entries:
                remaining -= 1
                if remaining < 0:
                    raise ValueError("repository discovery exceeded its entry budget")
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.name in _DISCOVERY_EXCLUDES or entry.name.startswith("."):
                    continue
                if segment == "**" or fnmatch(entry.name, segment):
                    visit(Path(entry.path), index if segment == "**" else index + 1)

    visit(workspace, 0)
    return sorted(repositories)


_COMMAND_TIMEOUT_SECONDS = 1800.0
_OUTPUT_LIMIT_BYTES = 1024 * 1024


def _default_runner(command: Sequence[str], repository: Path) -> subprocess.CompletedProcess[str]:
    """Capture bounded output and include inherited pipes in the command deadline.

    POSIX sessions let cleanup terminate descendants that retain output pipes.
    Non-POSIX hosts fail explicitly rather than execute without these bounds.
    """
    if os.name != "posix":
        return subprocess.CompletedProcess(command, 125, "", "bounded runner requires POSIX")
    try:
        process = subprocess.Popen(
            command, cwd=repository, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(command, 127, "", f"command launch failed: {exc}")

    buffers = [bytearray(), bytearray()]
    truncated = [False, False]
    deadline = time.monotonic() + _COMMAND_TIMEOUT_SECONDS
    timed_out = False
    try:
        with selectors.DefaultSelector() as selector:
            for index, pipe in enumerate((process.stdout, process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, index)
            while selector.get_map() or process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    index = key.data
                    available = _OUTPUT_LIMIT_BYTES - len(buffers[index])
                    buffers[index].extend(chunk[:available])
                    truncated[index] |= len(chunk) > available
    finally:
        # Also clean up descendants after the leader exits or the caller interrupts.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()

    outputs = [bytes(value).decode("utf-8", errors="replace") for value in buffers]
    for index in range(2):
        if truncated[index]:
            outputs[index] += "\n[koru: output truncated]"
    if timed_out:
        outputs[1] += "\n[koru: command deadline exceeded]"
    return subprocess.CompletedProcess(command, 124 if timed_out else process.returncode, *outputs)


def run_closed_loop(
    *,
    command: Sequence[str],
    repositories: Iterable[Path],
    max_rounds: int = 3,
    runner: Callable[[Sequence[str], Path], CommandResult] = _default_runner,
) -> LoopReport:
    """Run a command repeatedly on failed repositories until all pass or rounds end."""
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least one")
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
