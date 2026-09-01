"""Orchestrate ticket creation, git branch publication, and validator merge."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from koru.ci.publication import dispatch_validator_merge
from koru.ci.runner import run_local_ci
from koru.tasks import create_nl_task

_DEFAULT_BASE = "main"


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len].strip("-") or "work"


def _run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_repo(project: Path) -> None:
    if _run_git(project, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise RuntimeError(f"not a git repository: {project}")


def _current_branch(project: Path) -> str:
    result = _run_git(project, ["branch", "--show-current"])
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch:
        raise RuntimeError("cannot resolve current branch")
    return branch


def _branch_name(ticket_id: str, title: str) -> str:
    return f"{ticket_id}-{_slugify(title)}"


def _planfile_paths(project: Path) -> list[Path]:
    planfile = project / ".planfile"
    if not planfile.is_dir():
        return []
    paths: list[Path] = []
    for pattern in ("**/*.yaml", "**/*.yml", "**/*.json"):
        paths.extend(planfile.glob(pattern))
    return sorted({path for path in paths if path.is_file()})


def _commit_planfile_sync(project: Path, ticket_id: str, message: str) -> str | None:
    paths = _planfile_paths(project)
    if not paths:
        return None
    _run_git(project, ["add", "--"] + [str(path.relative_to(project)) for path in paths])
    diff = _run_git(project, ["diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        return None
    subject = message or f"planfile: bind {ticket_id}"
    commit = _run_git(project, ["commit", "-m", subject])
    if commit.returncode != 0:
        detail = (commit.stderr or commit.stdout or "").strip()
        raise RuntimeError(f"planfile commit failed: {detail}")
    sha = _run_git(project, ["rev-parse", "HEAD"]).stdout.strip()
    try:
        from koru.work.llm_provenance import notify_work_commit

        notify_work_commit(
            project,
            ticket_id=ticket_id,
            commit_sha=sha or None,
            message=subject,
        )
    except Exception:
        pass
    return sha or None


def _ensure_branch(project: Path, branch: str, base: str) -> None:
    if _run_git(project, ["show-ref", "--verify", f"refs/heads/{branch}"]).returncode == 0:
        checkout = _run_git(project, ["checkout", branch])
    else:
        checkout = _run_git(project, ["checkout", "-b", branch, base])
    if checkout.returncode != 0:
        detail = (checkout.stderr or checkout.stdout or "").strip()
        raise RuntimeError(f"cannot checkout branch {branch}: {detail}")


def _push_branch(project: Path, branch: str, *, remote: str = "origin") -> None:
    push = _run_git(project, ["push", "-u", remote, branch])
    if push.returncode != 0:
        detail = (push.stderr or push.stdout or "").strip()
        raise RuntimeError(f"git push failed: {detail}")


def _find_open_pr(project: Path, branch: str) -> int | None:
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number",
            "-q",
            ".[0].number",
        ],
        cwd=str(project),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip().isdigit():
        return int(proc.stdout.strip())
    return None


def _open_pr_if_needed(project: Path, branch: str, title: str, base: str) -> int | None:
    existing = _find_open_pr(project, branch)
    if existing is not None:
        return existing
    create = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            "Koru work lifecycle PR. Merge via validator-agent (not GitHub Actions).",
        ],
        cwd=str(project),
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0:
        detail = (create.stderr or create.stdout or "").strip()
        raise RuntimeError(f"gh pr create failed: {detail}")
    url = create.stdout.strip()
    number_proc = subprocess.run(
        ["gh", "pr", "view", url, "--json", "number", "-q", ".number"],
        cwd=str(project),
        capture_output=True,
        text=True,
        check=False,
    )
    if number_proc.returncode == 0 and number_proc.stdout.strip().isdigit():
        return int(number_proc.stdout.strip())
    return None


def start_work(
    project: Path,
    *,
    title: str,
    description: str | None = None,
    ticket_id: str | None = None,
    base_branch: str = _DEFAULT_BASE,
    push: bool = True,
    remote: str = "origin",
) -> dict[str, Any]:
    """Create planfile ticket, sync carrier to git, create/push feature branch."""
    project = project.resolve()
    _ensure_repo(project)

    task_text = description or title
    if ticket_id:
        created_id = ticket_id
        reused = True
    else:
        created = create_nl_task(project, task_text, scaffold={"title": title})
        created_id = created.ticket_id
        reused = created.reused

    branch = _branch_name(created_id, title)
    if _current_branch(project) != branch:
        _ensure_branch(project, branch, base_branch)

    planfile_sha = _commit_planfile_sync(
        project,
        created_id,
        f"planfile: start {created_id} — {title}",
    )

    pushed = False
    if push:
        _push_branch(project, branch, remote=remote)
        pushed = True

    return {
        "status": "started",
        "ticket_id": created_id,
        "ticket_reused": reused,
        "branch": branch,
        "base_branch": base_branch,
        "planfile_commit": planfile_sha,
        "pushed": pushed,
        "remote": remote if pushed else None,
        "next": [
            f"koru work finish --ticket {created_id} --project .",
            "Implement changes, then finish runs CI and validator-agent publish.",
        ],
    }


def finish_work(
    project: Path,
    *,
    ticket_id: str,
    base_branch: str = _DEFAULT_BASE,
    run_ci: bool = True,
    open_pr: bool = False,
    pr_number: int | None = None,
    publish: bool = True,
    merge: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run CI, optionally open PR, dispatch validator-agent (skip GitHub Actions merge)."""
    project = project.resolve()
    _ensure_repo(project)
    branch = _current_branch(project)
    stages: list[dict[str, Any]] = []

    if run_ci:
        ci_result = run_local_ci(project)
        stages.append({"stage": "ci", **ci_result})
        if ci_result.get("overall_status") != "passed":
            return {
                "status": "blocked",
                "reason": "ci_failed",
                "ticket_id": ticket_id,
                "branch": branch,
                "stages": stages,
            }

    resolved_pr = pr_number
    if open_pr and resolved_pr is None:
        try:
            resolved_pr = _open_pr_if_needed(project, branch, f"{ticket_id}: koru work", base_branch)
            stages.append({"stage": "pr", "status": "ready", "pr": resolved_pr})
        except Exception as exc:
            stages.append({"stage": "pr", "status": "error", "error": str(exc)})
            return {
                "status": "blocked",
                "reason": "pr_failed",
                "ticket_id": ticket_id,
                "branch": branch,
                "stages": stages,
            }
    elif resolved_pr is None:
        resolved_pr = _find_open_pr(project, branch)
        if resolved_pr is not None:
            stages.append({"stage": "pr", "status": "found", "pr": resolved_pr})

    if publish:
        if resolved_pr is None:
            return {
                "status": "blocked",
                "reason": "missing_pr",
                "ticket_id": ticket_id,
                "branch": branch,
                "stages": stages,
                "hint": "Pass --pr N, use --open-pr, or open a PR for the current branch.",
            }
        pub = dispatch_validator_merge(
            project,
            ticket_id=ticket_id,
            pr_number=resolved_pr,
            dry_run=dry_run,
            merge=merge,
        )
        stages.append({"stage": "publish", **pub})
        if pub.get("status") not in {"published", "dry_run"}:
            return {
                "status": "blocked",
                "reason": "publish_failed",
                "ticket_id": ticket_id,
                "branch": branch,
                "stages": stages,
            }

    return {
        "status": "finished" if not dry_run else "dry_run",
        "ticket_id": ticket_id,
        "branch": branch,
        "pr": resolved_pr,
        "stages": stages,
        "publication": "validator-agent (not GitHub Actions)",
    }
