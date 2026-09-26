"""Compile a dynamic execution plan from koru.yaml strategy, signals, and task profiles."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from koru.autonomy.ide_work import _current_sprint_tickets, sprint_ticket_status_summary
from koru.autonomy.task_strategies import (
    DEFAULT_TASK_STRATEGY,
    STRATEGY_ORDER,
    PendingPR,
    PendingWorktree,
    find_pending_prs,
    find_pending_worktrees,
    resolve_task_strategy,
)
from koru.autonomy_strategy import load_autonomy_strategy
from koru.autonomy_strategy.heuristics import build_strategy_heuristics

_SCHEMA = "koru.execution_plan/v1"
_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}
_SKIP_TICKET_IDS = frozenset({"STARTER-001", "STARTER-002"})
_OPEN_STATUSES = frozenset({"open", "ready", "todo"})


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


@dataclass
class ExecutionPlan:
    schema: str
    project: str
    strategy_id: str
    phase: str
    steps: list[ExecutionStep]
    signals: dict[str, Any]
    selected_ticket: dict[str, Any] | None = None
    selected_pr: dict[str, Any] | None = None
    selected_worktree: dict[str, Any] | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.selected_ticket is not None:
            payload["selected_ticket"] = _ticket_summary(self.selected_ticket, Path(self.project))
        if self.selected_pr is not None:
            payload["selected_pr"] = self.selected_pr
        if self.selected_worktree is not None:
            payload["selected_worktree"] = self.selected_worktree
        return payload


def _ticket_summary(ticket: dict[str, Any], project: Path) -> dict[str, Any]:
    files = ticket.get("files")
    repo = resolve_ticket_repo(project, ticket) if files else None
    return {
        "id": ticket.get("id"),
        "name": ticket.get("name"),
        "priority": ticket.get("priority"),
        "status": ticket.get("status"),
        "labels": ticket.get("labels") or [],
        "files": files if isinstance(files, list) else [],
        "repo": repo,
    }


@lru_cache(maxsize=1)
def _load_task_profiles() -> dict[str, Any]:
    raw = resources.files("koru.autonomy").joinpath("task_profiles.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return data if isinstance(data, dict) else {}


def _ticket_labels(ticket: dict[str, Any]) -> set[str]:
    labels = ticket.get("labels")
    if isinstance(labels, list):
        return {str(label).lower() for label in labels}
    return set()


def _ticket_signal(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    if not isinstance(source, dict):
        return None
    context = source.get("context")
    if isinstance(context, dict) and context.get("signal"):
        return str(context["signal"])
    return None


def _ticket_name(ticket: dict[str, Any]) -> str:
    return str(ticket.get("name") or ticket.get("id") or "").strip()


def _profile_labels_match(labels: set[str], wanted: Any) -> bool:
    if not wanted:
        return True
    return bool(labels.intersection({str(value).lower() for value in wanted}))


def _ticket_matches_profile(match: dict[str, Any], ticket: dict[str, Any]) -> bool:
    labels = _ticket_labels(ticket)
    labels_any = match.get("labels_any") or []
    if not _profile_labels_match(labels, labels_any):
        return False
    signal = _ticket_signal(ticket)
    signals_any = match.get("signals_any") or []
    if signals_any and (signal is None or signal not in signals_any):
        return False
    patterns = match.get("name_patterns") or []
    name = _ticket_name(ticket)
    if patterns and not any(fnmatch.fnmatch(name, str(pat)) for pat in patterns):
        return False
    return bool(labels_any or signals_any or patterns)


def _profile_matches(profile: dict[str, Any], *, ticket: dict[str, Any] | None, phase: str) -> bool:
    match = profile.get("match")
    if not isinstance(match, dict):
        return False
    if match.get("phase"):
        return str(match["phase"]) == phase
    if ticket is None:
        return False
    return _ticket_matches_profile(match, ticket)


def _profile_order(profiles_doc: dict[str, Any]) -> tuple[str, ...]:
    defaults = profiles_doc.get("defaults")
    if isinstance(defaults, dict):
        order = defaults.get("profile_order")
        if isinstance(order, list):
            return tuple(str(item).strip() for item in order if str(item).strip())
    return ("cc_hotspot_refactor", "god_module_split")


def _fallback_profile_id(profiles_doc: dict[str, Any]) -> str:
    defaults = profiles_doc.get("defaults")
    if isinstance(defaults, dict):
        token = str(defaults.get("fallback_profile") or "").strip()
        if token:
            return token
    return "god_module_split"


def _select_profile(ticket: dict[str, Any] | None, phase: str) -> tuple[str | None, dict[str, Any] | None]:
    profiles_doc = _load_task_profiles()
    profiles = profiles_doc.get("profiles") or {}
    if not isinstance(profiles, dict):
        return None, None
    profile_order = _profile_order(profiles_doc)
    ordered_ids = [pid for pid in profile_order if pid in profiles]
    ordered_ids.extend(pid for pid in profiles if pid not in ordered_ids)
    for profile_id in ordered_ids:
        profile = profiles.get(profile_id)
        if isinstance(profile, dict) and _profile_matches(profile, ticket=ticket, phase=phase):
            return str(profile_id), profile
    return None, None


def _target_source_lines(project: Path, ticket: dict[str, Any]) -> int | None:
    files = ticket.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        rel = str(entry).strip()
        if not rel or rel.startswith("project/") or rel.endswith(".toon.yaml"):
            continue
        path = project / rel
        if not path.is_file():
            continue
        try:
            return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            return None
    return None


def _first_code_file(project: Path, ticket: dict[str, Any]) -> Path | None:
    files = ticket.get("files")
    if not isinstance(files, list):
        return None
    for entry in files:
        rel = str(entry).strip()
        if not rel or rel.endswith(".toon.yaml") or rel.startswith("project/"):
            continue
        candidate = project / rel
        if candidate.is_file():
            return candidate
    return None


def _count_lines(path: Path) -> int | None:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return None


def _evidence_artifact_sha(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    if not isinstance(source, dict):
        return None
    context = source.get("context")
    if not isinstance(context, dict):
        return None
    evidence = context.get("evidence")
    if not isinstance(evidence, dict):
        return None
    files = evidence.get("files")
    if isinstance(files, list) and files:
        first = files[0]
        if isinstance(first, dict) and first.get("sha256"):
            return str(first["sha256"])
    artifact = evidence.get("artifact")
    if isinstance(artifact, dict) and artifact.get("sha256"):
        return str(artifact["sha256"])
    return None


def _file_sha256(path: Path) -> str | None:
    import hashlib

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _ticket_likely_complete(project: Path, ticket: dict[str, Any]) -> bool:
    labels = _ticket_labels(ticket)
    lines = _target_source_lines(project, ticket)
    if lines is not None:
        if "god-module" in labels and lines < 250:
            return True
        if "cyclomatic" in labels and lines < 80:
            return True
    evidence_sha = _evidence_artifact_sha(ticket)
    if evidence_sha:
        code_file = _first_code_file(project, ticket)
        if code_file is not None:
            current_sha = _file_sha256(code_file)
            if current_sha and current_sha != evidence_sha:
                if lines is not None and lines < 250:
                    return True
    return False


def _ticket_sort_key(project: Path, ticket: dict[str, Any]) -> tuple[int, int, str]:
    priority_label = str(ticket.get("priority") or "normal").lower()
    priority = _PRIORITY_RANK.get(priority_label, 99)
    labels = _ticket_labels(ticket)
    deprioritize = 0
    lines = _target_source_lines(project, ticket)
    if lines is not None:
        if "god-module" in labels and lines < 250:
            deprioritize = 1
        if "cyclomatic" in labels and lines < 120:
            deprioritize = 1
    return (priority + deprioritize, lines or 99999, str(ticket.get("id") or ""))


def _count_skipped_complete(project: Path) -> int:
    count = 0
    for ticket in _current_sprint_tickets(project):
        ticket_id = str(ticket.get("id") or "").strip().upper()
        status = str(ticket.get("status") or "").lower()
        if ticket_id in _SKIP_TICKET_IDS:
            continue
        if status not in _OPEN_STATUSES:
            continue
        if _ticket_likely_complete(project, ticket):
            count += 1
    return count


def _open_refactor_tickets(project: Path) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for ticket in _current_sprint_tickets(project):
        ticket_id = str(ticket.get("id") or "").strip().upper()
        status = str(ticket.get("status") or "").lower()
        if ticket_id in _SKIP_TICKET_IDS:
            continue
        if status not in _OPEN_STATUSES:
            continue
        if _ticket_likely_complete(project, ticket):
            continue
        tickets.append(ticket)
    tickets.sort(key=lambda t: _ticket_sort_key(project, t))
    return tickets


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


def _format_command(template: str, *, project: Path, repo: Path, ticket: dict[str, Any] | None) -> str:
    ticket_id = str((ticket or {}).get("id") or "")
    return (
        template.replace("{project}", str(project.resolve()))
        .replace("{repo}", str(repo.resolve()))
        .replace("{ticket_id}", ticket_id)
    )


def _workflow_steps(
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
            commands.append(_format_command(str(entry["command"]), project=project, repo=repo, ticket=ticket))
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


def _queued_ticket_steps(
    project: Path, selected: dict[str, Any], phase: str,
) -> list[ExecutionStep]:
    repo = Path(resolve_ticket_repo(project, selected) or project)
    profile_id, profile = _select_profile(selected, phase)
    if profile is None:
        profiles_doc = _load_task_profiles()
        fallback_id = _fallback_profile_id(profiles_doc)
        profile = (profiles_doc.get("profiles") or {}).get(fallback_id)
        profile_id = fallback_id if isinstance(profile, dict) else None
    if isinstance(profile, dict):
        steps = _workflow_steps(
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
                hint=_ticket_name(selected),
            ),
        ]
    return steps


def _pr_steps(project: Path, pr: PendingPR) -> list[ExecutionStep]:
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


def _worktree_steps(project: Path, wt: PendingWorktree) -> list[ExecutionStep]:
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


class _PlanSignals(NamedTuple):
    """Signal payload plus the open refactor tickets it was computed from."""

    payload: dict[str, Any]
    open_tickets: list[dict[str, Any]]
    pending_prs: list[PendingPR]
    pending_worktrees: list[PendingWorktree]


class _PlanSelection(NamedTuple):
    """Chosen plan phase with the steps, ticket, PR, or worktree that represent it."""

    phase: str
    steps: list[ExecutionStep]
    selected: dict[str, Any] | None = None
    selected_pr: dict[str, Any] | None = None
    selected_worktree: dict[str, Any] | None = None
    summary: str = ""


def _pipeline_order(strategy: dict[str, Any]) -> list[Any]:
    pipeline = strategy.get("default_pipeline") if isinstance(strategy.get("default_pipeline"), dict) else {}
    order = pipeline.get("order") if isinstance(pipeline.get("order"), list) else []
    return order


def _collect_plan_signals(
    project: Path,
    *,
    task_strategy: str = DEFAULT_TASK_STRATEGY,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> _PlanSignals:
    open_tickets = _open_refactor_tickets(project)
    prs = pending_prs if pending_prs is not None else find_pending_prs(project)
    wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)
    payload: dict[str, Any] = {
        "planfile": sprint_ticket_status_summary(project),
        "open_refactor_tickets": len(open_tickets),
        "skipped_likely_complete": _count_skipped_complete(project),
        "task_strategy": task_strategy,
        "pending_prs_count": len(prs),
        "pending_worktrees_count": len(wts),
        "pending_prs": [p.to_dict() for p in prs],
        "pending_worktrees": [w.to_dict() for w in wts],
        "heuristics": build_strategy_heuristics(project),
    }
    try:
        from koru.work.llm_provenance import resolve_work_llm_context

        payload["llm"] = resolve_work_llm_context(project).to_dict()
    except Exception:
        pass
    return _PlanSignals(
        payload=payload,
        open_tickets=open_tickets,
        pending_prs=prs,
        pending_worktrees=wts,
    )


def _discovery_steps(project: Path, phase: str) -> list[ExecutionStep]:
    profile_id, profile = _select_profile(None, phase)
    if not isinstance(profile, dict):
        return []
    return _workflow_steps(
        profile,
        project=project,
        repo=project,
        ticket=None,
        profile_id=profile_id or phase,
        phase=phase,
    )


def _discovery_selection(project: Path, order: list[Any]) -> _PlanSelection:
    for phase_name in order:
        if phase_name in {"idle_scan", "whole_project_discovery"}:
            phase = str(phase_name)
            return _PlanSelection(
                phase=phase,
                steps=_discovery_steps(project, phase),
                selected=None,
                summary=f"phase={phase}",
            )
    return _PlanSelection(phase="idle", steps=[], selected=None, summary="phase=idle")


def _select_plan_work(
    project: Path,
    strategy: dict[str, Any],
    open_tickets: list[dict[str, Any]],
    *,
    task_strategy: str = DEFAULT_TASK_STRATEGY,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> _PlanSelection:
    order = STRATEGY_ORDER.get(task_strategy, STRATEGY_ORDER[DEFAULT_TASK_STRATEGY])

    prs = pending_prs if pending_prs is not None else find_pending_prs(project)
    wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)

    for target in order:
        if target == "pending_prs" and prs:
            pr = prs[0]
            steps = _pr_steps(project, pr)
            return _PlanSelection(
                phase="pending_pr",
                steps=steps,
                selected=None,
                selected_pr=pr.to_dict(),
                summary=f"phase=pending_pr pr=#{pr.number} title={pr.title}",
            )
        if target == "pending_worktrees" and wts:
            wt = wts[0]
            steps = _worktree_steps(project, wt)
            return _PlanSelection(
                phase="pending_worktree",
                steps=steps,
                selected=None,
                selected_worktree=wt.to_dict(),
                summary=f"phase=pending_worktree ticket={wt.ticket_id or 'unknown'} branch={wt.branch}",
            )
        if target == "issues":
            if open_tickets:
                phase = "planfile_queue"
                selected = open_tickets[0]
                return _PlanSelection(
                    phase=phase,
                    steps=_queued_ticket_steps(project, selected, phase),
                    selected=selected,
                    summary=f"phase={phase} ticket={selected.get('id')}",
                )
            return _discovery_selection(project, _pipeline_order(strategy))

    return _PlanSelection(phase="idle", steps=[], selected=None, summary="phase=idle")


def _plan_summary(selection: _PlanSelection) -> str:
    if selection.summary:
        return selection.summary
    summary = f"phase={selection.phase}"
    if selection.selected is not None:
        profile = selection.steps[0].profile_id if selection.steps else "n/a"
        summary += f" ticket={selection.selected.get('id')} profile={profile}"
    elif selection.selected_pr is not None:
        summary += f" pr=#{selection.selected_pr.get('number')}"
    elif selection.selected_worktree is not None:
        summary += f" worktree={selection.selected_worktree.get('ticket_id')}"
    return summary


def compile_execution_plan(
    project: Path,
    strategy_override: str | None = None,
    *,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> ExecutionPlan:
    project = project.resolve()
    strategy = load_autonomy_strategy(project) or {}
    active_strategy = resolve_task_strategy(project, explicit_strategy=strategy_override)
    signals = _collect_plan_signals(
        project,
        task_strategy=active_strategy,
        pending_prs=pending_prs,
        pending_worktrees=pending_worktrees,
    )
    selection = _select_plan_work(
        project,
        strategy,
        signals.open_tickets,
        task_strategy=active_strategy,
        pending_prs=signals.pending_prs,
        pending_worktrees=signals.pending_worktrees,
    )
    return ExecutionPlan(
        schema=_SCHEMA,
        project=str(project),
        strategy_id=active_strategy,
        phase=selection.phase,
        steps=selection.steps,
        signals=signals.payload,
        selected_ticket=selection.selected,
        selected_pr=selection.selected_pr,
        selected_worktree=selection.selected_worktree,
        summary=selection.summary or _plan_summary(selection),
    )


def run_auto_steps(plan: ExecutionPlan, *, dry_run: bool = False) -> list[dict[str, Any]]:
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


__all__ = [
    "ExecutionPlan",
    "ExecutionStep",
    "compile_execution_plan",
    "resolve_ticket_repo",
    "run_auto_steps",
]
