"""Typed policy-engine adapter for autonomous autopilot skip decisions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import DiagnosticResult
from koru.autonomous_cycle_skip_conditions import _check_autopilot_skip_conditions
from koru.autonomy.policy_decision import AutopilotPolicyDecision
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


@dataclass(frozen=True)
class AutopilotPolicyContext:
    project: Path
    queue_result: QueueLoopResult
    state: AutoloopState
    autopilot_action: str
    autopilot_on_idle_only: bool
    autopilot_skip_on_diagnostics_fail: bool
    autopilot_skip_drive_idle_streak: int
    autopilot_skip_statuses: str
    diag_result: DiagnosticResult
    topology_integration: bool
    cycle_telemetry: dict[str, Any]
    human_log: Callable[..., Any]


def decide_autopilot_policy(
    context: AutopilotPolicyContext,
    *,
    check_skip_conditions: Callable[..., tuple[bool, str]] | None = None,
) -> AutopilotPolicyDecision:
    """Return a typed decision while preserving the existing skip policy."""
    check_fn = check_skip_conditions or _check_autopilot_skip_conditions
    should_skip, status = check_fn(
        context.project,
        context.queue_result,
        context.state,
        context.autopilot_action,
        context.autopilot_on_idle_only,
        context.autopilot_skip_on_diagnostics_fail,
        context.autopilot_skip_drive_idle_streak,
        context.autopilot_skip_statuses,
        context.diag_result,
        context.topology_integration,
        context.cycle_telemetry,
        context.human_log,
    )
    if not should_skip:
        return AutopilotPolicyDecision.proceed()
    return AutopilotPolicyDecision(
        should_skip=True,
        reason_code=_reason_code_from_status(status),
        status=status or "skipped(unknown)",
    )


def _reason_code_from_status(status: str) -> str:
    text = str(status or "").strip()
    lower = text.lower()
    if lower.startswith("skipped(") and text.endswith(")"):
        return text[text.find("(") + 1 : -1] or "unknown"
    return text or "unknown"


__all__ = ["AutopilotPolicyContext", "decide_autopilot_policy"]
