"""Compile a dynamic execution plan from koru.yaml strategy, signals, and task profiles."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from koru.autonomy.ide_work import _current_sprint_tickets, sprint_ticket_status_summary
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
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.selected_ticket is not None:
            payload["selected_ticket"] = _ticket_summary(self.selected_ticket, Path(self.project))
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


def _profile_matches(profile: dict[str, Any], *, ticket: dict[str, Any] | None, phase: str) -> bool:
    match = profile.get("match")
    if not isinstance(match, dict):
        return False
    if match.get("phase"):
        return str(match["phase"]) == phase
    if ticket is None:
        return False
    labels = _ticket_labels(ticket)
    labels_any = match.get("labels_any") or []
    if labels_any and not labels.intersection({str(x).lower() for x in labels_any}):
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


def _select_profile(ticket: dict[str, Any] | None, phase: str) -> tuple[str | None, dict[str, Any] | None]:
    profiles = _load_task_profiles().get("profiles") or {}
    if not isinstance(profiles, dict):
        return None, None
    profile_order = ("cc_hotspot_refactor", "god_module_split")
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


def _ticket_likely_complete(project: Path, ticket: dict[str, Any]) -> bool:
    """Skip planfile tickets whose target file no longer matches scan evidence."""
    labels = _ticket_labels(ticket)
    lines = _target_source_lines(project, ticket)
    if lines is None:
        return False
    if "god-module" in labels and lines < 250:
        return True
    if "cyclomatic" in labels and lines < 120:
        return True
    if "large-module" in labels and lines < 400:
        return True
    return False


def _ticket_sort_key(project: Path, ticket: dict[str, Any]) -> tuple[int, int, str]:
    priority = _PRIORITY_RANK.get(str(ticket.get("priority") or "normal"), 2)
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


def compile_execution_plan(project: Path) -> ExecutionPlan:
    project = project.resolve()
    strategy = load_autonomy_strategy(project) or {}
    strategy_id = str(strategy.get("id") or "unknown")
    pipeline = strategy.get("default_pipeline") if isinstance(strategy.get("default_pipeline"), dict) else {}
    order = pipeline.get("order") if isinstance(pipeline.get("order"), list) else []
    heuristics = build_strategy_heuristics(project)
    open_tickets = _open_refactor_tickets(project)
    signals: dict[str, Any] = {
        "planfile": sprint_ticket_status_summary(project),
        "open_refactor_tickets": len(open_tickets),
        "skipped_likely_complete": _count_skipped_complete(project),
        "heuristics": heuristics,
    }

    steps: list[ExecutionStep] = []
    selected: dict[str, Any] | None = None
    phase = "idle"

    if open_tickets:
        phase = "planfile_queue"
        selected = open_tickets[0]
        repo = Path(resolve_ticket_repo(project, selected) or project)
        profile_id, profile = _select_profile(selected, phase)
        if profile is None:
            profile_id, profile = "god_module_split", (_load_task_profiles().get("profiles") or {}).get(
                "god_module_split",
            )
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
    else:
        for phase_name in order:
            if phase_name in {"idle_scan", "whole_project_discovery"}:
                phase = str(phase_name)
                profile_id, profile = _select_profile(None, phase)
                if isinstance(profile, dict):
                    steps = _workflow_steps(
                        profile,
                        project=project,
                        repo=project,
                        ticket=None,
                        profile_id=profile_id or phase,
                        phase=phase,
                    )
                break

    summary = f"phase={phase}"
    if selected is not None:
        summary += f" ticket={selected.get('id')} profile={steps[0].profile_id if steps else 'n/a'}"
    return ExecutionPlan(
        schema=_SCHEMA,
        project=str(project),
        strategy_id=strategy_id,
        phase=phase,
        steps=steps,
        signals=signals,
        selected_ticket=selected,
        summary=summary,
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
