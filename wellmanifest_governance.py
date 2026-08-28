"""Pytest lifecycle bridge for the adopted wellmanifest governance gate."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


class GovernanceGateError(RuntimeError):
    """Raised when deterministic governance rejects the current checkout."""


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return None
    return result.stdout.strip()


def _resolve_base(root: Path) -> str:
    explicit = os.environ.get("WELLMANIFEST_BASE_SHA", "").strip()
    if explicit and _git(root, "cat-file", "-e", f"{explicit}^{{commit}}") is not None:
        return explicit

    candidates: list[str] = []
    github_base = os.environ.get("GITHUB_BASE_REF", "").strip()
    if github_base:
        candidates.append(f"origin/{github_base}")
    candidates.append("origin/main")
    for candidate in candidates:
        if _git(root, "rev-parse", "--verify", f"{candidate}^{{commit}}") is None:
            continue
        merge_base = _git(root, "merge-base", "HEAD", candidate)
        if merge_base:
            return merge_base

    head = _git(root, "rev-parse", "HEAD")
    if not head:
        raise GovernanceGateError("GOV-PACKAGING-003: cannot resolve Git base")
    return head


def _changed_paths(root: Path, base: str) -> list[str]:
    paths: set[str] = set()
    commands = (
        ("diff", "--name-only", base, "HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    )
    for command in commands:
        output = _git(root, *command)
        if output:
            paths.update(line for line in output.splitlines() if line)
    return sorted(paths)


def pytest_sessionstart(session: object) -> None:
    """Run repository governance once before pytest collects product tests."""
    config = getattr(session, "config", None)
    rootpath = getattr(config, "rootpath", Path.cwd())
    root = Path(str(rootpath)).resolve()
    gate = root / "project" / "governance-check.sh"
    if not gate.is_file():
        raise GovernanceGateError(
            "GOV-PACKAGING-003: managed governance gate is missing"
        )
    if os.environ.get("WELLMANIFEST_GOVERNANCE_ACTIVE") == "1":
        raise GovernanceGateError("GOV-PACKAGING-003: recursive gate invocation")

    base = _resolve_base(root)
    command = [str(gate), "--base", base]
    for path in _changed_paths(root, base):
        command.extend(("--changed-file", path))

    environment = dict(os.environ)
    environment["WELLMANIFEST_GOVERNANCE_ACTIVE"] = "1"
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode:
        raise GovernanceGateError(
            f"GOV-PACKAGING-003: governance gate failed with exit code {result.returncode}"
        )
