"""Signal collection and work selection for dynamic execution plans."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from koru.autonomy.execution_plan_profiles import (
    count_skipped_complete as _count_skipped_complete,
    load_task_profiles as _load_task_profiles,
    open_refactor_tickets as _open_refactor_tickets,
    select_profile as _select_profile_fn,
)
from koru.autonomy.execution_plan_steps import (
    ExecutionStep,
    discovery_steps as _discovery_steps,
    pr_steps as _pr_steps,
    queued_ticket_steps,
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
)
from koru.autonomy_strategy.heuristics import build_strategy_heuristics


class PlanSignals(NamedTuple):
    """Signal payload plus the open refactor tickets it was computed from."""

    payload: dict[str, Any]
    open_tickets: list[dict[str, Any]]
    pending_prs: list[PendingPR]
    pending_worktrees: list[PendingWorktree]


class PlanSelection(NamedTuple):
    """Chosen plan phase with the steps, ticket, PR, or worktree that represent it."""

    phase: str
    steps: list[ExecutionStep]
    selected: dict[str, Any] | None = None
    selected_pr: dict[str, Any] | None = None
    selected_worktree: dict[str, Any] | None = None
    summary: str = ""


def select_profile(ticket: dict[str, Any] | None, phase: str) -> tuple[str | None, dict[str, Any] | None]:
    return _select_profile_fn(ticket, phase, profiles_doc=_load_task_profiles())


def pipeline_order(strategy: dict[str, Any]) -> list[Any]:
    pipeline = strategy.get("default_pipeline") if isinstance(strategy.get("default_pipeline"), dict) else {}
    order = pipeline.get("order") if isinstance(pipeline.get("order"), list) else []
    return order


def filter_unmerged_worktrees(wts: list[PendingWorktree]) -> list[PendingWorktree]:
    """Exclude worktrees that have already been merged into main."""
    return [w for w in wts if not w.is_merged]


def collect_plan_signals(
    project: Path,
    *,
    task_strategy: str = DEFAULT_TASK_STRATEGY,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> PlanSignals:
    open_tickets = _open_refactor_tickets(project)
    prs = pending_prs if pending_prs is not None else find_pending_prs(project)
    raw_wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)
    wts = filter_unmerged_worktrees(raw_wts)
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
    return PlanSignals(
        payload=payload,
        open_tickets=open_tickets,
        pending_prs=prs,
        pending_worktrees=wts,
    )


def discovery_selection(project: Path, order: list[Any]) -> PlanSelection:
    for phase_name in order:
        if phase_name in {"idle_scan", "whole_project_discovery"}:
            phase = str(phase_name)
            return PlanSelection(
                phase=phase,
                steps=_discovery_steps(project, phase),
                selected=None,
                summary=f"phase={phase}",
            )
    return PlanSelection(phase="idle", steps=[], selected=None, summary="phase=idle")


def select_pending_pr(
    project: Path,
    prs: list[PendingPR],
) -> PlanSelection | None:
    """Return a selection for the highest-priority pending PR, if any."""
    if not prs:
        return None
    pr = prs[0]
    steps = _pr_steps(project, pr)
    return PlanSelection(
        phase="pending_pr",
        steps=steps,
        selected=None,
        selected_pr=pr.to_dict(),
        summary=f"phase=pending_pr pr=#{pr.number} title={pr.title}",
    )


def select_pending_worktree(
    project: Path,
    wts: list[PendingWorktree],
) -> PlanSelection | None:
    """Return a selection for the highest-priority pending worktree, if any."""
    if not wts:
        return None
    wt = wts[0]
    steps = _worktree_steps(project, wt)
    return PlanSelection(
        phase="pending_worktree",
        steps=steps,
        selected=None,
        selected_worktree=wt.to_dict(),
        summary=f"phase=pending_worktree ticket={wt.ticket_id or 'unknown'} branch={wt.branch}",
    )


def select_issue_or_discovery(
    project: Path,
    strategy: dict[str, Any],
    open_tickets: list[dict[str, Any]],
) -> PlanSelection | None:
    """Return a selection for the next open ticket or a discovery phase."""
    if open_tickets:
        phase = "planfile_queue"
        selected = open_tickets[0]
        steps = queued_ticket_steps(project, selected, phase)
        profile = steps[0].profile_id if steps else "n/a"
        return PlanSelection(
            phase=phase,
            steps=steps,
            selected=selected,
            summary=f"phase={phase} ticket={selected.get('id')} profile={profile}",
        )
    return discovery_selection(project, pipeline_order(strategy))


def select_plan_work(
    project: Path,
    strategy: dict[str, Any],
    open_tickets: list[dict[str, Any]],
    *,
    task_strategy: str = DEFAULT_TASK_STRATEGY,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> PlanSelection:
    order = STRATEGY_ORDER.get(task_strategy, STRATEGY_ORDER[DEFAULT_TASK_STRATEGY])

    prs = pending_prs if pending_prs is not None else find_pending_prs(project)
    raw_wts = pending_worktrees if pending_worktrees is not None else find_pending_worktrees(project)
    wts = filter_unmerged_worktrees(raw_wts)

    _selectors: dict[str, Any] = {
        "pending_prs": lambda: select_pending_pr(project, prs),
        "pending_worktrees": lambda: select_pending_worktree(project, wts),
        "issues": lambda: select_issue_or_discovery(project, strategy, open_tickets),
    }

    for target in order:
        selector = _selectors.get(target)
        if selector is not None:
            result = selector()
            if result is not None:
                return result

    return PlanSelection(phase="idle", steps=[], selected=None, summary="phase=idle")


def plan_summary(selection: PlanSelection) -> str:
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


__all__ = [
    "PlanSelection",
    "PlanSignals",
    "collect_plan_signals",
    "discovery_selection",
    "filter_unmerged_worktrees",
    "pipeline_order",
    "plan_summary",
    "queued_ticket_steps",
    "select_issue_or_discovery",
    "select_pending_pr",
    "select_pending_worktree",
    "select_plan_work",
    "select_profile",
]
