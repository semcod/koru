"""Small GitHub helpers for Koru publication (read-only + dispatch wrapper)."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


class GitHubCliError(RuntimeError):
    pass


def _run_gh(args: list[str], *, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["gh", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise GitHubCliError(detail or f"gh {' '.join(args)} failed")
    return proc.stdout.strip()


def gh_available() -> bool:
    proc = subprocess.run(["gh", "--version"], capture_output=True, text=True, check=False)
    return proc.returncode == 0


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


def resolve_github_repo(project: Path) -> GitHubRepo:
    url = _run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd=project)
    if "/" not in url:
        raise GitHubCliError(f"unexpected repo slug: {url!r}")
    owner, name = url.split("/", 1)
    return GitHubRepo(owner=owner, name=name)


def resolve_pr_head_sha(repo: GitHubRepo, pr_number: int) -> str:
    return _run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo.slug,
            "--json",
            "headRefOid",
            "-q",
            ".headRefOid",
        ],
    )


def resolve_pr_merge_state(repo: GitHubRepo, pr_number: int) -> dict[str, str]:
    raw = _run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo.slug,
            "--json",
            "mergeable,mergeStateStatus,headRefOid",
        ],
    )
    payload = json.loads(raw or "{}")
    if not isinstance(payload, dict):
        raise GitHubCliError(f"unexpected merge state payload for PR #{pr_number}")
    return {
        "mergeable": str(payload.get("mergeable") or "UNKNOWN"),
        "mergeStateStatus": str(payload.get("mergeStateStatus") or "UNKNOWN"),
        "headRefOid": str(payload.get("headRefOid") or ""),
    }


def wait_for_pr_mergeable(
    repo: GitHubRepo,
    pr_number: int,
    *,
    timeout_seconds: float = 120.0,
    poll_seconds: float = 5.0,
) -> dict[str, str]:
    """Poll GitHub until mergeability is known or timeout."""
    deadline = time.monotonic() + max(timeout_seconds, poll_seconds)
    last: dict[str, str] = {
        "mergeable": "UNKNOWN",
        "mergeStateStatus": "UNKNOWN",
        "headRefOid": "",
    }
    while time.monotonic() <= deadline:
        last = resolve_pr_merge_state(repo, pr_number)
        if last["mergeable"] != "UNKNOWN" and last["mergeStateStatus"] != "UNKNOWN":
            return last
        time.sleep(poll_seconds)
    return last


def find_open_pr_for_branch(repo: GitHubRepo, branch: str) -> int | None:
    raw = _run_gh(
        [
            "pr",
            "list",
            "--repo",
            repo.slug,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number",
        ],
    )
    items = json.loads(raw or "[]")
    if not items:
        return None
    return int(items[0]["number"])


def current_branch(project: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(project), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    branch = proc.stdout.strip()
    if proc.returncode != 0 or not branch:
        raise GitHubCliError("cannot resolve current git branch")
    return branch
