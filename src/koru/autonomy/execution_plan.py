"""Compile a dynamic execution plan from koru.yaml strategy, signals, and task profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
from koru.autonomy.execution_plan_selection import (
    PlanSelection as _PlanSelection,
)
from koru.autonomy.execution_plan_selection import (
    PlanSignals as _PlanSignals,
)
from koru.autonomy.execution_plan_selection import (
    collect_plan_signals as _collect_plan_signals,
)
from koru.autonomy.execution_plan_selection import (
    discovery_selection as _discovery_selection,
)
from koru.autonomy.execution_plan_selection import (
    pipeline_order as _pipeline_order,
)
from koru.autonomy.execution_plan_selection import (
    plan_summary as _plan_summary,
)
from koru.autonomy.execution_plan_selection import (
    queued_ticket_steps as _queued_ticket_steps,
)
from koru.autonomy.execution_plan_selection import (
    select_issue_or_discovery as _select_issue_or_discovery,
)
from koru.autonomy.execution_plan_selection import (
    select_pending_pr as _select_pending_pr,
)
from koru.autonomy.execution_plan_selection import (
    select_pending_worktree as _select_pending_worktree,
)
from koru.autonomy.execution_plan_selection import (
    select_plan_work as _select_plan_work,
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
    workflow_steps as _workflow_steps,
)
from koru.autonomy.execution_plan_steps import (
    worktree_steps as _worktree_steps,
)
from koru.autonomy.task_strategies import (
    PendingPR,
    PendingWorktree,
    resolve_task_strategy,
)
from koru.autonomy_strategy import load_autonomy_strategy


def _select_profile(
    ticket: dict[str, Any] | None,
    phase: str,
) -> tuple[str | None, dict[str, Any] | None]:
    return select_profile(ticket, phase, profiles_doc=_load_task_profiles())


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


def _build_execution_plan(
    project: Path,
    active_strategy: str,
    signals: _PlanSignals,
    selection: _PlanSelection,
) -> ExecutionPlan:
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


def compile_execution_plan(
    project: Path,
    strategy_override: str | None = None,
    *,
    pending_prs: list[PendingPR] | None = None,
    pending_worktrees: list[PendingWorktree] | None = None,
) -> ExecutionPlan:
    resolved = project.resolve()
    strategy = load_autonomy_strategy(resolved) or {}
    active_strategy = resolve_task_strategy(resolved, explicit_strategy=strategy_override)
    signals = _collect_plan_signals(
        resolved,
        task_strategy=active_strategy,
        pending_prs=pending_prs,
        pending_worktrees=pending_worktrees,
    )
    selection = _select_plan_work(
        resolved,
        strategy,
        signals.open_tickets,
        task_strategy=active_strategy,
        pending_prs=signals.pending_prs,
        pending_worktrees=signals.pending_worktrees,
    )
    return _build_execution_plan(resolved, active_strategy, signals, selection)


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
    "_select_pending_pr",
    "_select_pending_worktree",
    "_select_issue_or_discovery",
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
