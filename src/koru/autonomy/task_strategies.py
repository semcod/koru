"""Task execution strategies for Koru autonomy and execution planning.

Defines pluggable strategies for prioritizing work:
- in_flight_first (default, alias pr_worktree_issues):
    1. Pending PRs: check/validate/merge open PRs before starting new work.
    2. Pending local worktrees: complete/verify/publish local unmerged/dirty worktrees.
    3. New tasks / issues: planfile queue tickets, then whole-project discovery.
- accordion_detail_to_general:
    Legacy strategy: planfile queue first, then whole-project discovery.
- worktree_first:
    Worktrees first, then PRs, then issues.
- issues_first:
    Issues first, then PRs, then worktrees.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Strategy definitions and aliases
DEFAULT_TASK_STRATEGY = "in_flight_first"

STRATEGY_ORDER: dict[str, tuple[str, ...]] = {
    "in_flight_first": ("pending_prs", "pending_worktrees", "issues"),
    "pr_worktree_issues": ("pending_prs", "pending_worktrees", "issues"),
    "accordion_detail_to_general": ("issues",),
    "worktree_first": ("pending_worktrees", "pending_prs", "issues"),
    "issues_first": ("issues", "pending_prs", "pending_worktrees"),
    "prs_only": ("pending_prs",),
    "worktrees_only": ("pending_worktrees",),
    "issues_only": ("issues",),
}

_TICKET_ID_RE = re.compile(r"ticket-(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class PendingPR:
    """Represents an open Pull Request awaiting check, review, or merge."""

    number: int
    title: str
    head_branch: str
    url: str = ""
    mergeable: str = "UNKNOWN"
    review_decision: str = ""
    checks_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingWorktree:
    """Represents a local worktree or branch with unmerged or uncommitted work."""

    path: str
    branch: str
    ticket_id: str | None
    head_sha: str
    is_dirty: bool
    commits_ahead: int
    is_merged: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_pending_prs(
    project: Path,
    *,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> list[PendingPR]:
    """Detect open Pull Requests via GitHub CLI (gh pr list).

    Returns a list of PendingPR objects sorted by PR number ascending.
    If gh fails (not authenticated, network error, or not installed), returns empty list.
    """
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,headRefName,url,mergeable,reviewDecision,statusCheckRollup",
    ]
    try:
        if runner is not None:
            proc = runner(cmd, project)
        else:
            proc = subprocess.run(cmd, cwd=str(project), capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
        if not isinstance(data, list):
            return []

        prs: list[PendingPR] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            number = item.get("number")
            if not isinstance(number, int):
                continue
            title = str(item.get("title") or "")
            branch = str(item.get("headRefName") or "")
            url = str(item.get("url") or "")
            mergeable = str(item.get("mergeable") or "UNKNOWN")
            review_dec = str(item.get("reviewDecision") or "")

            checks = item.get("statusCheckRollup")
            checks_status = ""
            if isinstance(checks, list):
                states = [str(c.get("state") or c.get("conclusion") or "") for c in checks if isinstance(c, dict)]
                checks_status = ",".join(filter(None, states))

            prs.append(
                PendingPR(
                    number=number,
                    title=title,
                    head_branch=branch,
                    url=url,
                    mergeable=mergeable,
                    review_decision=review_dec,
                    checks_status=checks_status,
                )
            )
        prs.sort(key=lambda p: p.number)
        return prs
    except Exception:
        return []


def _extract_ticket_id(text: str) -> str | None:
    match = _TICKET_ID_RE.search(text)
    if match:
        return f"ticket-{match.group(1)}"
    return None


def find_pending_worktrees(
    project: Path,
    *,
    base_branch: str = "main",
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> list[PendingWorktree]:
    """Detect local worktrees that have in-progress, dirty, or unmerged work.

    Filters out:
    - The primary checkout itself.
    - Disposable temporary run checkouts (e.g. .koru-run-* or worktrees/run-*).
    - Worktrees whose branch is already merged into base_branch (and clean).
    """
    def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if runner is not None:
            return runner(args, cwd)
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)

    resolved_project = project.resolve()
    proc = _run_git(["worktree", "list", "--porcelain"], resolved_project)
    if proc.returncode != 0:
        return []

    lines = proc.stdout.splitlines()
    worktrees_raw: list[tuple[str, str, str]] = []
    curr_wt = ""
    curr_head = ""
    curr_br = ""

    for line in lines:
        if line.startswith("worktree "):
            curr_wt = line.split(" ", 1)[1].strip()
        elif line.startswith("HEAD "):
            curr_head = line.split(" ", 1)[1].strip()
        elif line.startswith("branch "):
            curr_br = line.split(" ", 1)[1].strip()
            worktrees_raw.append((curr_wt, curr_head, curr_br))
            curr_wt, curr_head, curr_br = "", "", ""
        elif not line.strip() and curr_wt:
            # detached worktree
            worktrees_raw.append((curr_wt, curr_head, ""))
            curr_wt, curr_head, curr_br = "", "", ""

    pending: list[PendingWorktree] = []
    for wt_path_str, head_sha, branch_ref in worktrees_raw:
        wt_path = Path(wt_path_str).resolve()
        # Skip primary checkout
        if wt_path == resolved_project:
            continue
        # Skip temporary runner throwaway worktrees
        is_runner_wt = (
            wt_path.name.startswith(".koru-run-")
            or "worktrees/run-" in str(wt_path)
            or wt_path.name.endswith("-verify")
        )
        if is_runner_wt:
            continue

        branch_name = branch_ref.replace("refs/heads/", "") if branch_ref else ""
        ticket_id = _extract_ticket_id(wt_path.name) or (_extract_ticket_id(branch_name) if branch_name else None)

        # Check dirty state
        status_proc = _run_git(["status", "--short"], wt_path)
        is_dirty = bool(status_proc.stdout.strip())

        # Check if merged
        is_merged = False
        commits_ahead = 0
        if branch_name:
            merge_proc = _run_git(["merge-base", "--is-ancestor", branch_name, base_branch], resolved_project)
            is_merged = (merge_proc.returncode == 0)

            ahead_proc = _run_git(["rev-list", "--count", f"{base_branch}..{branch_name}"], resolved_project)
            if ahead_proc.returncode == 0 and ahead_proc.stdout.strip().isdigit():
                commits_ahead = int(ahead_proc.stdout.strip())
        elif head_sha:
            merge_proc = _run_git(["merge-base", "--is-ancestor", head_sha, base_branch], resolved_project)
            is_merged = (merge_proc.returncode == 0)

        # A worktree is pending if it is dirty, or not yet merged, or has unpushed commits ahead of base
        if is_dirty or (not is_merged) or (commits_ahead > 0):
            pending.append(
                PendingWorktree(
                    path=str(wt_path),
                    branch=branch_name,
                    ticket_id=ticket_id,
                    head_sha=head_sha,
                    is_dirty=is_dirty,
                    commits_ahead=commits_ahead,
                    is_merged=is_merged,
                )
            )

    # Sort pending worktrees: dirty/active first, then by ticket id
    pending.sort(key=lambda w: (not w.is_dirty, w.is_merged, w.ticket_id or ""))
    return pending


def resolve_task_strategy(
    project: Path,
    explicit_strategy: str | None = None,
) -> str:
    """Resolve the active task execution strategy name.

    Precedence:
    1. explicit_strategy parameter (CLI flag --strategy)
    2. KORU_TASK_STRATEGY environment variable
    3. koru.yaml -> autonomy.strategy.task_strategy or autonomy.strategy.id
    4. DEFAULT_TASK_STRATEGY ('in_flight_first')
    """
    if explicit_strategy and explicit_strategy.strip():
        chosen = explicit_strategy.strip().lower()
        if chosen in STRATEGY_ORDER:
            return chosen

    env_val = os.environ.get("KORU_TASK_STRATEGY", "").strip().lower()
    if env_val and env_val in STRATEGY_ORDER:
        return env_val

    # Read from koru.yaml strategy
    try:
        from koru.autonomy_strategy import load_autonomy_strategy

        strat = load_autonomy_strategy(project) or {}
        task_strat = str(strat.get("task_strategy") or "").strip().lower()
        if task_strat and task_strat in STRATEGY_ORDER:
            return task_strat
        strat_id = str(strat.get("id") or "").strip().lower()
        if strat_id and strat_id in STRATEGY_ORDER:
            return strat_id
    except Exception:
        pass

    return DEFAULT_TASK_STRATEGY


__all__ = [
    "DEFAULT_TASK_STRATEGY",
    "STRATEGY_ORDER",
    "PendingPR",
    "PendingWorktree",
    "find_pending_prs",
    "find_pending_worktrees",
    "resolve_task_strategy",
]
