"""Execution step models and step generators for Koru execution planning."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autonomy.execution_plan_profiles import (
    fallback_profile_id,
    load_task_profiles,
    select_profile,
    ticket_name,
)
from koru.autonomy.task_strategies import PendingPR, PendingWorktree


@dataclass
class ExecutionStep:
    id: str
    kind: str
    reason: str
    commands: list[str] = field(default_factory=list)
    ticket_id: str | None = None
    profile_id: str | None = None
    repo: str | None = None
    auto_runnable: bool = False
    hint: str | None = None


def _git_toplevel(path: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    top = proc.stdout.strip()
    return Path(top) if top else None


def resolve_ticket_repo(project: Path, ticket: dict[str, Any]) -> str | None:
    """Resolve the git repo root for the first file path declared on a ticket."""
    files = ticket.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        rel = str(entry).strip()
        if not rel or rel.endswith(".toon.yaml") or rel.startswith("project/"):
            continue
        candidate = (project / rel).resolve()
        parent = candidate.parent if candidate.suffix else candidate
        top = _git_toplevel(parent)
        if top is not None:
            return str(top)
    return str(project.resolve())


def format_command(template: str, *, project: Path, repo: Path, ticket: dict[str, Any] | None) -> str:
    ticket_id = str((ticket or {}).get("id") or "")
    return (
        template.replace("{project}", str(project.resolve()))
        .replace("{repo}", str(repo.resolve()))
        .replace("{ticket_id}", ticket_id)
    )


def workflow_steps(
    profile: dict[str, Any],
    *,
    project: Path,
    repo: Path,
    ticket: dict[str, Any] | None,
    profile_id: str,
    phase: str,
) -> list[ExecutionStep]:
    steps: list[ExecutionStep] = []
    workflow = profile.get("workflow")
    if not isinstance(workflow, list):
        return steps
    for entry in workflow:
        if not isinstance(entry, dict):
            continue
        step_id = str(entry.get("id") or "step")
        kind = str(entry.get("kind") or "shell")
        auto = bool(entry.get("auto"))
        hint = str(entry.get("hint") or "").strip() or None
        commands: list[str] = []
        if entry.get("command"):
            commands.append(format_command(str(entry["command"]), project=project, repo=repo, ticket=ticket))
        reason = str(profile.get("description") or profile_id)
        steps.append(
            ExecutionStep(
                id=step_id,
                kind=kind,
                reason=reason,
                commands=commands,
                ticket_id=str(ticket.get("id")) if ticket else None,
                profile_id=profile_id,
                repo=str(repo.resolve()),
                auto_runnable=auto and bool(commands),
                hint=hint,
            ),
        )
    return steps


def queued_ticket_steps(
    project: Path,
    selected: dict[str, Any],
    phase: str,
) -> list[ExecutionStep]:
    repo = Path(resolve_ticket_repo(project, selected) or project)
    profile_id, profile = select_profile(selected, phase)
    if profile is None:
        profiles_doc = load_task_profiles()
        fallback_id = fallback_profile_id(profiles_doc)
        profile = (profiles_doc.get("profiles") or {}).get(fallback_id)
        profile_id = fallback_id if isinstance(profile, dict) else None
    if isinstance(profile, dict):
        steps = workflow_steps(
            profile,
            project=project,
            repo=repo,
            ticket=selected,
            profile_id=profile_id or "generic",
            phase=phase,
        )
    else:
        steps = [
            ExecutionStep(
                id="work_ticket",
                kind="ide_work",
                reason="Runnable planfile ticket without a matching profile.",
                ticket_id=str(selected.get("id")),
                repo=str(repo.resolve()),
                hint=ticket_name(selected),
            ),
        ]
    return steps


def pr_steps(project: Path, pr: PendingPR) -> list[ExecutionStep]:
    """Build execution steps for triaging, validating, and merging an open PR."""
    return [
        ExecutionStep(
            id="view_pr",
            kind="shell",
            reason=f"Inspect open PR #{pr.number} checks, mergeability, and details.",
            commands=[f"gh pr view {pr.number} --json number,title,state,checks,mergeable"],
            hint=f"Review PR #{pr.number} ({pr.title}) on branch {pr.head_branch}",
            repo=str(project.resolve()),
            auto_runnable=True,
        ),
        ExecutionStep(
            id="finish_pr",
            kind="validator_merge",
            reason=f"Validate and autonomously merge open PR #{pr.number}.",
            commands=[f"koru work finish --pr {pr.number} --merge --project {project.resolve()}"],
            hint=f"Merge PR #{pr.number} via validator-agent when checks pass",
            repo=str(project.resolve()),
            auto_runnable=False,
        ),
    ]


def worktree_steps(project: Path, wt: PendingWorktree) -> list[ExecutionStep]:
    """Build execution steps for resuming, testing, and completing a pending worktree."""
    tid = wt.ticket_id or "work"
    return [
        ExecutionStep(
            id="status_worktree",
            kind="shell",
            reason=f"Inspect git status in pending worktree {wt.path}.",
            commands=[f"git -C {wt.path} status --short"],
            hint=f"Check uncommitted or unmerged state in {wt.path}",
            repo=wt.path,
            auto_runnable=True,
        ),
        ExecutionStep(
            id="test_worktree",
            kind="shell",
            reason=f"Run verification tests in pending worktree {wt.path}.",
            commands=[f"sh -c 'cd {wt.path} && koru ci run'"],
            hint=f"Run verification tests in {wt.path}",
            repo=wt.path,
            auto_runnable=True,
        ),
        ExecutionStep(
            id="finish_worktree",
            kind="worktree_finish",
            reason=f"Commit, push, and open PR for pending worktree {wt.path}.",
            commands=[f"sh -c 'cd {wt.path} && koru work finish --ticket {tid} --open-pr'"],
            hint=f"Finish work in {wt.path} and open PR",
            repo=wt.path,
            auto_runnable=False,
        ),
    ]


def discovery_steps(project: Path, phase: str) -> list[ExecutionStep]:
    profile_id, profile = select_profile(None, phase)
    if not isinstance(profile, dict):
        return []
    return workflow_steps(
        profile,
        project=project,
        repo=project,
        ticket=None,
        profile_id=profile_id or phase,
        phase=phase,
    )


def run_auto_steps(plan: Any, *, dry_run: bool = False) -> list[dict[str, Any]]:
    """Execute auto-runnable shell steps from a compiled plan."""
    results: list[dict[str, Any]] = []
    for step in plan.steps:
        if not step.auto_runnable or not step.commands:
            results.append(
                {
                    "step": step.id,
                    "status": "skipped",
                    "reason": "not auto-runnable",
                },
            )
            continue
        for command in step.commands:
            if dry_run:
                results.append({"step": step.id, "status": "dry_run", "command": command})
                continue
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
            results.append(
                {
                    "step": step.id,
                    "status": "ok" if proc.returncode == 0 else "failed",
                    "command": command,
                    "returncode": proc.returncode,
                    "stdout_tail": (proc.stdout or "")[-500:],
                    "stderr_tail": (proc.stderr or "")[-500:],
                },
            )
            if proc.returncode != 0:
                break
    return results
