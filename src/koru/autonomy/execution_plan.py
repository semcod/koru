"""Compile a dynamic execution plan from koru.yaml strategy, signals, and task profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, NamedTuple

from koru.autonomy.execution_plan_profiles import (
    count_skipped_complete as _count_skipped_complete,
)
from koru.autonomy.execution_plan_profiles import (
    fallback_profile_id as _fallback_profile_id,
)
from koru.autonomy.execution_plan_profiles import (
    load_task_profiles as _load_task_profiles,
)
from koru.autonomy.execution_plan_profiles import (
    open_refactor_tickets as _open_refactor_tickets,
)
from koru.autonomy.execution_plan_profiles import (
    profile_matches as _profile_matches,
)
from koru.autonomy.execution_plan_profiles import (
    profile_order as _profile_order,
)
from koru.autonomy.execution_plan_profiles import (
    select_profile,
)
from koru.autonomy.execution_plan_profiles import (
    target_source_lines as _target_source_lines,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_labels as _ticket_labels,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_likely_complete as _ticket_likely_complete,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_matches_profile as _ticket_matches_profile,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_name as _ticket_name,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_signal as _ticket_signal,
)
from koru.autonomy.execution_plan_profiles import (
    ticket_sort_key as _ticket_sort_key,
)
from koru.autonomy.execution_plan_steps import (
    ExecutionStep,
    resolve_ticket_repo,
    run_auto_steps,
)
from koru.autonomy.execution_plan_steps import (
    discovery_steps as _discovery_steps,
)
from koru.autonomy.execution_plan_steps import (
    format_command as _format_command,
)
from koru.autonomy.execution_plan_steps import (
    pr_steps as _pr_steps,
)
from koru.autonomy.execution_plan_steps import (
    queued_ticket_steps as _queued_ticket_steps,
)
from koru.autonomy.execution_plan_steps import (
    workflow_steps as _workflow_steps,
)
from koru.autonomy.execution_plan_steps import (
    worktree_steps as _worktree_steps,
)
from koru.autonomy.ide_work import sprint_ticket_status_summary
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


def _select_profile(ticket: dict[str, Any] | None, phase: str) -> tuple[str | None, dict[str, Any] | None]:
    return select_profile(ticket, phase, profiles_doc=_load_task_profiles())


def _pipeline_order(strategy: dict[str, Any]) -> list[Any]:
    pipeline = strategy.get("default_pipeline") if isinstance(strategy.get("default_pipeline"), dict) else {}
    order = pipeline.get("order") if isinstance(pipeline.get("order"), list) else []
    return order


def _filter_unmerged_worktrees(wts: list[PendingWorktree]) -> list[PendingWorktree]:
    """Exclude worktrees that have already been merged into main."""
    return [w for w in wts if not w.is_merged]


def _collect_plan_signals(
    project: Path,
    *,
    task_strategy: str = DEFAULT_TASK_STRATEGY,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> _PlanSignals:
    open_tickets = _open_refactor_tickets(project)
    prs = pending_prs if pending_prs is not None else find_pending_prs(project)
    raw_wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)
    wts = _filter_unmerged_worktrees(raw_wts)
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
    raw_wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)
    wts = _filter_unmerged_worktrees(raw_wts)

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


__all__ = [
    "ExecutionPlan",
    "ExecutionStep",
    "compile_execution_plan",
    "resolve_ticket_repo",
    "run_auto_steps",
    "_count_skipped_complete",
    "_discovery_selection",
    "_discovery_steps",
    "_fallback_profile_id",
    "_format_command",
    "_load_task_profiles",
    "_open_refactor_tickets",
    "_pipeline_order",
    "_plan_summary",
    "_pr_steps",
    "_profile_matches",
    "_profile_order",
    "_queued_ticket_steps",
    "_select_plan_work",
    "_select_profile",
    "_target_source_lines",
    "_ticket_labels",
    "_ticket_likely_complete",
    "_ticket_matches_profile",
    "_ticket_name",
    "_ticket_signal",
    "_ticket_sort_key",
    "_workflow_steps",
    "_worktree_steps",
]
