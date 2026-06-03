"""Backward-compatible facade for ``coru.repair`` (CQRS + event sourcing)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from coru.repair import (
    REPAIR_REGISTRY,
    RepairAttempt,
    RepairPlan,
    RepairProblem,
    RepairStepDef,
    collect_problems_from_manage_report,
    collect_problems_from_status,
    dedupe_problems,
    format_repair_lines,
    manual_vsix_unpack,
    plugin_build_aligned,
    run_repair_with_events,
)
from coru.repair.diagnostics import (
    collect_problems_from_console_logs,
    collect_problems_from_drive_result,
)

RunKoru = Callable[[Sequence[str]], int]
ReplayFn = Callable[[str, str, Sequence[str]], int]
StatusPayloadFn = Callable[[str, str], dict[str, Any] | None]
IdeReloadFn = Callable[[str, Path | None], RepairAttempt]
IdeConnectFn = Callable[[str], RepairAttempt]
StrictHandshakeFn = Callable[[], RepairAttempt]


def run_repair_pipeline(
    *,
    ide: str,
    instance: str,
    repo_root: Path | None,
    problems: Sequence[RepairProblem],
    run_koru: RunKoru,
    replay: ReplayFn,
    fetch_status: StatusPayloadFn,
    ensure_daemon: Callable[[], int] | None = None,
    ide_reload: IdeReloadFn | None = None,
    ide_connect: IdeConnectFn | None = None,
    strict_handshake: StrictHandshakeFn | None = None,
    max_rounds: int = 3,
    trigger: str = "repair_registry",
) -> RepairPlan:
    return run_repair_with_events(
        project_root=repo_root,
        ide=ide,
        instance=instance,
        problems=problems,
        trigger=trigger,
        run_koru=run_koru,
        replay=replay,
        fetch_status=fetch_status,
        ensure_daemon=ensure_daemon,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
        strict_handshake=strict_handshake,
        max_rounds=max_rounds,
    )


__all__ = [
    "RepairAttempt",
    "RepairPlan",
    "RepairProblem",
    "RepairStepDef",
    "REPAIR_REGISTRY",
    "collect_problems_from_console_logs",
    "collect_problems_from_drive_result",
    "collect_problems_from_manage_report",
    "collect_problems_from_status",
    "dedupe_problems",
    "format_repair_lines",
    "manual_vsix_unpack",
    "plugin_build_aligned",
    "run_repair_pipeline",
]
