"""Shared fixtures for queue/repair tests: one repo lab, not ten copies.

Every queue and repair suite needs the same three things — a throwaway git
repo with an identity, a committed baseline file, and a CommandResult-shaped
reply. They were copied per file until redup flagged the pattern; now the
bodies live here and the suites keep one-line delegates, so a fix to the lab
fixes every suite at once.

Underscore-prefixed on purpose: pytest must not collect this as a test module.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace


def reply(stdout: str = "", stderr: str = "", returncode: int = 0, status_code=None):
    """A CommandResult-shaped stub, superset of every suite's local variant."""
    return SimpleNamespace(
        returncode=returncode, stdout=stdout, stderr=stderr, status_code=status_code,
    )


def git_repo(tmp: str | Path) -> Path:
    """An initialised repo with an identity, ready to commit."""
    project = Path(tmp)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "koru@test"],
        ["config", "user.name", "koru"],
    ):
        subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
    return project


def commit_file(project: Path, rel: str, body: str) -> None:
    """Write, add and commit one file as the repo's baseline."""
    target = project / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-qm", "baseline"], cwd=project, check=True, capture_output=True,
    )


def ticket_args(command) -> list[str]:
    """Strip the interpreter prefix planfile_command puts before ``ticket``."""
    args = [str(part) for part in command]
    return args[args.index("ticket"):] if "ticket" in args else args
