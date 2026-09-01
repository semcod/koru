"""Resolve LLM/provider context for Koru work and operator surfaces."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from koru.autonomy.configuration.config_cli_config import _openrouter_model_from_strategy
from koru.autonomy.planning_llm_budget import DEFAULT_MODEL as PLANNING_DEFAULT_MODEL
from koru.autonomy.planning_llm_runtime import model_name as planning_model_name
from koru.autonomy_strategy import load_autonomy_strategy
from koru.env_flags import parse_boolish
from koru.notifications.desktop import notify_desktop


@dataclass(frozen=True)
class WorkLlmContext:
    """Resolved LLM routing for the current Koru work session."""

    project: str
    project_url: str
    planning_enabled: bool
    planning_provider: str
    planning_model: str
    planning_route: str
    queue_default_model: str
    tillm_provider: str
    tillm_model: str
    work_uses_llm: bool
    work_llm_mode: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def notification_body(self, *, commit_sha: str | None = None, ticket_id: str | None = None) -> str:
        lines = [
            self.project_url or self.project,
            f"planning: {self.planning_provider}/{self.planning_model}",
            f"work lane: {self.work_llm_mode}",
        ]
        if self.tillm_provider or self.tillm_model:
            lines.append(f"tillm: {self.tillm_provider or 'default'}/{self.tillm_model or 'inherit'}")
        if ticket_id:
            lines.append(f"ticket: {ticket_id}")
        if commit_sha:
            lines.append(f"commit: {commit_sha[:12]}")
        if self.notes:
            lines.extend(self.notes[:2])
        return "\n".join(lines)


def _git_remote_url(project: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(project), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    url = (proc.stdout or "").strip()
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@"):
        # git@github.com:org/repo -> https://github.com/org/repo
        host_path = url.split(":", 1)
        if len(host_path) == 2:
            return f"https://{host_path[0].removeprefix('git@')}/{host_path[1]}"
    return url


def _planning_provider_from_strategy(strategy: dict[str, Any]) -> str:
    planning = strategy.get("planning_assistant")
    if not isinstance(planning, dict):
        return "subllm"
    order = planning.get("provider_order")
    if isinstance(order, list):
        for item in order:
            token = str(item or "").strip()
            if token:
                return token
    if isinstance(planning.get("subllm_cursor"), dict):
        return "subllm_cursor"
    if isinstance(planning.get("openrouter"), dict):
        return "openrouter"
    if isinstance(planning.get("ide_llm"), dict):
        return "ide_llm"
    return "subllm"


def _planning_route_from_strategy(strategy: dict[str, Any]) -> str:
    planning = strategy.get("planning_assistant")
    if not isinstance(planning, dict):
        return "planning-assistant"
    subllm = planning.get("subllm_cursor")
    if isinstance(subllm, dict) and subllm.get("function"):
        return str(subllm["function"])
    return "planning-assistant"


def resolve_work_llm_context(project: Path) -> WorkLlmContext:
    """Best-effort LLM provenance from strategy, env and built-in defaults."""
    project = project.resolve()
    strategy = load_autonomy_strategy(project) or {}
    planning = strategy.get("planning_assistant")
    planning_enabled = True
    if isinstance(planning, dict):
        planning_enabled = parse_boolish(planning.get("enabled"), default=True)

    strategy_model = _openrouter_model_from_strategy(strategy)
    model = (
        os.environ.get("KORU_PLANNING_LLM_MODEL", "").strip()
        or strategy_model
        or planning_model_name()
        or PLANNING_DEFAULT_MODEL
    )
    provider = _planning_provider_from_strategy(strategy)
    if os.environ.get("OPENROUTER_API_KEY", "").strip():
        if provider in {"", "subllm", "subllm_cursor"} and not os.environ.get("ZAI_API_KEY", "").strip():
            provider = "openrouter"
    elif os.environ.get("ZAI_API_KEY", "").strip():
        provider = "z.ai"

    tillm_provider = os.environ.get("TILLM_PROVIDER", "").strip()
    tillm_model = os.environ.get("KORU_TILLM_MODEL", "").strip() or os.environ.get("LLM_MODEL", "").strip()

    from koru.queue.runners import _DEFAULT_LLM_MODEL

    notes = (
        "koru work next is registry-driven; ide_work steps delegate to the IDE lane",
        "planning LLM is used by autonomous/reflection routes, not planfile git commits",
    )
    return WorkLlmContext(
        project=str(project),
        project_url=_git_remote_url(project),
        planning_enabled=planning_enabled,
        planning_provider=provider,
        planning_model=model,
        planning_route=_planning_route_from_strategy(strategy),
        queue_default_model=_DEFAULT_LLM_MODEL,
        tillm_provider=tillm_provider,
        tillm_model=tillm_model,
        work_uses_llm=False,
        work_llm_mode="task_profiles+ide_work",
        notes=notes,
    )


def notify_work_commit(
    project: Path,
    *,
    ticket_id: str,
    commit_sha: str | None,
    message: str,
) -> bool:
    """Desktop popup after a Koru planfile/work commit."""
    ctx = resolve_work_llm_context(project)
    title = f"Koru commit — {ticket_id}"
    body = ctx.notification_body(commit_sha=commit_sha, ticket_id=ticket_id)
    if message.strip():
        body = f"{message.strip()}\n{body}"
    return notify_desktop(title=title, body=body)
