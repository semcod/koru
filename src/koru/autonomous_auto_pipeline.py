"""Auto-pipeline logic for adaptive autonomous mode profiles.

When ``KORU_AUTO_PIPELINE=1`` is set, each autonomous cycle selects a
profile (rescue / stabilize / quality / architecture) based on queue
health and idle streaks.
"""

import argparse
from dataclasses import dataclass
from typing import Any

from koru.autonomous_cycle import DiagnosticResult
from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.queue import QueueLoopResult

_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})

AUTO_UP_DEFAULT_ARGS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("--scan-after-idle-queue", "--no-scan-after-idle-queue"), ("--scan-after-idle-queue",)),
)


@dataclass
class AutoPipelineState:
    seen_cycles: int = 0
    idle_cycles: int = 0
    last_queue_status: str = ""
    last_iterations: int = 0
    last_failed_count: int = 0
    last_waiting_count: int = 0
    last_diag_status: str = ""
    last_autopilot_status: str = ""


@dataclass(frozen=True)
class AutoPipelineProfile:
    name: str
    reason: str
    enable_scan: bool
    max_iterations: int
    include_semcod_artifacts: bool | None
    idle_diagnostics: str
    diagnostic_tickets: bool
    scan_after_idle_queue: bool
    scan_after_idle_min_interval: float
    enable_autopilot: bool
    autopilot_action: str


def _argv_has_option(argv: list[str], names: tuple[str, ...]) -> bool:
    for arg in argv:
        if arg in names:
            return True
        if any(arg.startswith(f"{name}=") for name in names):
            return True
    return False


def _expand_auto_up_defaults(argv: list[str]) -> list[str]:
    expanded = list(argv)
    provided = expanded[1:]
    defaults: list[str] = []
    for names, default_args in AUTO_UP_DEFAULT_ARGS:
        if not _argv_has_option(provided, names):
            defaults.extend(default_args)
    return [expanded[0], *defaults, *provided]


def _collect_argv_options(argv: list[str]) -> set[str]:
    return {arg.split("=", 1)[0] for arg in argv if arg.startswith("--")}


def _user_option(options: set[str], names: tuple[str, ...]) -> bool:
    return any(name in options for name in names)


def _auto_value(args: argparse.Namespace, names: tuple[str, ...], attr: str, value: Any) -> Any:
    if _user_option(getattr(args, "_auto_user_options", set()), names):
        return getattr(args, attr)
    return value


def _auto_pipeline_has_pressure(state: AutoPipelineState, max_iterations: int) -> tuple[bool, str]:
    if state.seen_cycles == 0:
        return True, "initial rescue pass"
    if state.last_failed_count:
        return True, "queue failures present"
    if state.last_waiting_count or state.last_queue_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
        return True, "queue waiting for input"
    if state.last_diag_status == "failed":
        return True, "diagnostics failed"
    if parse_autopilot_status(state.last_autopilot_status).failed:
        return True, "autopilot failed"
    if state.last_queue_status == "completed" and state.last_iterations >= max_iterations:
        return True, "queue backlog reached max-iterations"
    return False, ""


def _auto_pipeline_stage(state: AutoPipelineState, max_iterations: int) -> tuple[str, str]:
    has_pressure, reason = _auto_pipeline_has_pressure(state, max_iterations)
    if has_pressure:
        return "rescue", reason
    if state.idle_cycles >= 3:
        return "architecture", "queue stable for architecture checks"
    if state.idle_cycles >= 2:
        return "quality", "queue stable for quality checks"
    if state.idle_cycles >= 1:
        return "stabilize", "queue idle; run quick verification"
    return "stabilize", "queue moving"


def _select_auto_pipeline_profile(
    args: argparse.Namespace,
    state: AutoPipelineState,
    *,
    base_enable_scan: bool,
) -> AutoPipelineProfile:
    stage, reason = _auto_pipeline_stage(state, max(1, int(args.max_iterations)))
    if stage == "rescue":
        return AutoPipelineProfile(
            name=stage,
            reason=reason,
            enable_scan=bool(_auto_value(args, ("--ticket-sources",), "ticket_sources", False)),
            max_iterations=int(_auto_value(args, ("--max-iterations",), "max_iterations", 1)),
            include_semcod_artifacts=_auto_value(
                args,
                ("--semcod-artifacts", "--no-semcod-artifacts"),
                "semcod_artifacts",
                False,
            ),
            idle_diagnostics=str(
                _auto_value(args, ("--idle-diagnostics",), "idle_diagnostics", "off")
            ),
            diagnostic_tickets=bool(
                _auto_value(args, ("--diagnostic-tickets",), "diagnostic_tickets", False)
            ),
            scan_after_idle_queue=bool(
                _auto_value(
                    args,
                    ("--scan-after-idle-queue", "--no-scan-after-idle-queue"),
                    "scan_after_idle_queue",
                    False,
                )
            ),
            scan_after_idle_min_interval=float(args.scan_after_idle_min_interval),
            enable_autopilot=bool(
                _auto_value(args, ("--no-autopilot",), "enable_autopilot", False)
            ),
            autopilot_action=str(
                _auto_value(args, ("--autopilot-action",), "autopilot_action", "off")
            ),
        )
    if stage == "stabilize":
        return AutoPipelineProfile(
            name=stage,
            reason=reason,
            enable_scan=bool(_auto_value(args, ("--ticket-sources",), "ticket_sources", False)),
            max_iterations=int(_auto_value(args, ("--max-iterations",), "max_iterations", 1)),
            include_semcod_artifacts=_auto_value(
                args,
                ("--semcod-artifacts", "--no-semcod-artifacts"),
                "semcod_artifacts",
                False,
            ),
            idle_diagnostics=str(
                _auto_value(args, ("--idle-diagnostics",), "idle_diagnostics", "quick")
            ),
            diagnostic_tickets=bool(
                _auto_value(args, ("--diagnostic-tickets",), "diagnostic_tickets", True)
            ),
            scan_after_idle_queue=bool(
                _auto_value(
                    args,
                    ("--scan-after-idle-queue", "--no-scan-after-idle-queue"),
                    "scan_after_idle_queue",
                    True,
                )
            ),
            scan_after_idle_min_interval=float(args.scan_after_idle_min_interval or 60.0),
            enable_autopilot=bool(
                _auto_value(args, ("--no-autopilot",), "enable_autopilot", False)
            ),
            autopilot_action=str(
                _auto_value(args, ("--autopilot-action",), "autopilot_action", "off")
            ),
        )
    return AutoPipelineProfile(
        name=stage,
        reason=reason,
        enable_scan=bool(_auto_value(args, ("--ticket-sources",), "ticket_sources", True))
        or base_enable_scan,
        max_iterations=int(_auto_value(args, ("--max-iterations",), "max_iterations", 1)),
        include_semcod_artifacts=_auto_value(
            args,
            ("--semcod-artifacts", "--no-semcod-artifacts"),
            "semcod_artifacts",
            True,
        ),
        idle_diagnostics=str(
            _auto_value(
                args,
                ("--idle-diagnostics",),
                "idle_diagnostics",
                "deep" if stage == "architecture" else "full",
            )
        ),
        diagnostic_tickets=bool(
            _auto_value(args, ("--diagnostic-tickets",), "diagnostic_tickets", True)
        ),
        scan_after_idle_queue=bool(
            _auto_value(
                args,
                ("--scan-after-idle-queue", "--no-scan-after-idle-queue"),
                "scan_after_idle_queue",
                True,
            )
        ),
        scan_after_idle_min_interval=float(args.scan_after_idle_min_interval or 60.0),
        enable_autopilot=bool(_auto_value(args, ("--no-autopilot",), "enable_autopilot", False)),
        autopilot_action=str(_auto_value(args, ("--autopilot-action",), "autopilot_action", "off")),
    )


def _update_auto_pipeline_state(
    state: AutoPipelineState,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    autopilot_status: str,
) -> None:
    state.seen_cycles += 1
    state.last_queue_status = queue_result.last_status
    state.last_iterations = queue_result.iterations
    state.last_failed_count = len(queue_result.failed)
    state.last_waiting_count = len(queue_result.waiting)
    state.last_diag_status = diag_result.status
    state.last_autopilot_status = autopilot_status
    if queue_result.last_status == "idle" and diag_result.status != "failed":
        state.idle_cycles += 1
    else:
        state.idle_cycles = 0


__all__ = [
    "AUTO_UP_DEFAULT_ARGS",
    "AutoPipelineState",
    "AutoPipelineProfile",
    "_argv_has_option",
    "_expand_auto_up_defaults",
    "_collect_argv_options",
    "_user_option",
    "_auto_value",
    "_auto_pipeline_has_pressure",
    "_auto_pipeline_stage",
    "_select_auto_pipeline_profile",
    "_update_auto_pipeline_state",
]
