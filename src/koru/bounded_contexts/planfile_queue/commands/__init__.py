"""Command objects for the planfile queue bounded context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.queue.human import default_human_prompt
from koru.queue.runners import run_api_request, run_llm_request, run_process, run_shell_command
from koru.queue.types import CommandResult


@dataclass(frozen=True)
class RunNextPlanfileTaskCommand:
    project: Path
    actor: str = "koru-shell"
    dry_run: bool = False
    queue_name: str | None = None
    interactive: bool = False
    planfile_runner: Callable[[list[str], Path], CommandResult] = run_process
    shell_runner: Callable[[str, Path], CommandResult] = run_shell_command
    api_runner: Callable[[dict[str, Any], Path], CommandResult] = run_api_request
    llm_runner: Callable[[dict[str, Any], Path], CommandResult] = run_llm_request
    prompt_runner: Callable[[str, str], str | None] = default_human_prompt


__all__ = ["RunNextPlanfileTaskCommand"]