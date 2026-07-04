"""Operator next-step narration for ``koru autonomous`` cycles."""

from __future__ import annotations

from typing import Any

from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_by_from_autopilot_status,
    _is_plugin_blocker,
)


def _handle_stop_reason_waiting_input(ticket: str, **kwargs: Any) -> list[str]:
    return [
        f"1/3 stop now; queue is waiting for operator input on {ticket}",
        f"2/3 operator should mark {ticket} done/input/fail through planfile",
        "3/3 next koru auto run will resume from the updated queue state",
    ]


def _handle_stop_reason_max_cycles(args: Any, status: str, ticket: str, **kwargs: Any) -> list[str]:
    return [
        f"1/3 stop now; reached max-cycles={getattr(args, 'max_cycles', '?')}",
        f"2/3 preserve checkpoint with queue={status or 'unknown'} waiting={ticket}",
        "3/3 next koru auto run will continue from the saved checkpoint",
    ]


def _handle_status_waiting_input(
    sleep_text: str,
    ticket: str,
    autopilot_status: str,
    max_iterations: int,
    **kwargs: Any,
) -> list[str]:
    if "chat_activity" in autopilot_status:
        first = (
            f"1/3 wait {sleep_text}; chat cooldown is active for {ticket}, "
            "so Koru will not paste over the IDE chat; this is not a daemon failure"
        )
    elif _is_plugin_blocker(_blocked_by_from_autopilot_status(autopilot_status)):
        first = (
            f"1/3 wait {sleep_text}; keep queue on {ticket} while the IDE "
            "plugin reconnects"
        )
    else:
        first = f"1/3 wait {sleep_text}; keep current waiting ticket {ticket} scoped"
    return [
        first,
        f"2/3 rerun planfile queue (max {max_iterations}) and check whether {ticket} moved",
        (
            "3/3 if queue becomes idle, run scan/discovery; if still waiting, "
            "use chat events/reflection before any redrive"
        ),
    ]


def _handle_status_idle(args: Any, project: Any, sleep_text: str, **kwargs: Any) -> list[str]:
    # Late-bind through the runner facade so tests patching
    # ``autonomous_loop_runner._dashboard_action_urls`` still take effect.
    from koru.autonomy.operator import operator_loop_runner as _runner_mod

    urls = _runner_mod._dashboard_action_urls(project) if project is not None else {
        "dashboard": "http://127.0.0.1:8765/",
        "create_project_ticket": "http://127.0.0.1:8765/llm/prompt/create-ticket-for-project",
        "create_project_ticket_action": "http://127.0.0.1:8765/llm/action/create-ticket-for-project",
        "tickets": "http://127.0.0.1:8765/?tab=tickets",
    }
    discovery = (
        "scan/code2llm discovery if freshness and rate limits allow"
        if getattr(args, "scan_after_idle_queue", False)
        else "idle scan is disabled unless explicitly requested"
    )
    return [
        (
            f"1/3 wait {sleep_text}; queue is idle — all planfile tickets "
            "are 'done' or canceled. autopilot drive is suppressed so the "
            "user's chat input isn't clobbered with stale prompts"
        ),
        (
            "2/3 strategy detail→general: planfile ticket queue first; "
            f"when empty, {discovery}; then code2llm whole-project discovery "
            "can create new focused tickets"
        ),
        (
            "3/3 quick links: create discovery ticket "
            f"{urls['create_project_ticket_action']} ; tickets {urls['tickets']} ; "
            "force fresh scan command remains: "
            "`rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto`"
        ),
    ]


def _handle_status_completed_or_failed(
    status: str,
    sleep_text: str,
    max_iterations: int,
    **kwargs: Any,
) -> list[str]:
    return [
        f"1/3 wait {sleep_text}; queue just reported {status}",
        f"2/3 rerun planfile queue (max {max_iterations}) to pick the next ticket",
        "3/3 if no ticket remains, switch to idle scan/discovery strategy",
    ]


def _handle_default_steps(
    sleep_text: str,
    stagnation_streak: int,
    status: str,
    **kwargs: Any,
) -> list[str]:
    return [
        f"1/3 wait {sleep_text}; preserve current loop state (streak={stagnation_streak})",
        f"2/3 rerun queue/status checks for status={status or 'unknown'}",
        "3/3 choose scan, ticket drive, or operator input based on the next queue result",
    ]


class AutonomyNextStepNarrator:
    """Build exactly three operator-facing next-step lines per cycle."""

    def __init__(
        self,
        *,
        args: Any,
        project: Any | None,
        waiting_ticket: str,
    ) -> None:
        self.args = args
        self.project = project
        self.waiting_ticket = waiting_ticket if waiting_ticket and waiting_ticket != "-" else "none"

    def narrate(
        self,
        *,
        queue_status: str,
        autopilot_status: str,
        sleep_seconds: float,
        stagnation_streak: int,
        stop_reason: str | None,
    ) -> list[str]:
        sleep_text = f"{sleep_seconds:g}s"
        max_iterations = int(getattr(self.args, "max_iterations", 50) or 50)

        kwargs = {
            "args": self.args,
            "project": self.project,
            "waiting_ticket": self.waiting_ticket,
            "autopilot_status": autopilot_status,
            "effective_sleep": sleep_seconds,
            "stagnation_streak": stagnation_streak,
            "stop_reason": stop_reason,
            "status": queue_status,
            "max_iterations": max_iterations,
            "ticket": self.waiting_ticket,
            "sleep_text": sleep_text,
        }

        if stop_reason == "waiting_input":
            return _handle_stop_reason_waiting_input(**kwargs)
        if stop_reason == "max_cycles":
            return _handle_stop_reason_max_cycles(**kwargs)
        if queue_status == "waiting_input":
            return _handle_status_waiting_input(**kwargs)
        if queue_status == "idle":
            return _handle_status_idle(**kwargs)
        if queue_status in {"completed", "failed"}:
            return _handle_status_completed_or_failed(**kwargs)

        return _handle_default_steps(**kwargs)


def _operator_next_steps(
    *,
    args: Any,
    project: Any | None = None,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    stagnation_streak: int,
    stop_reason: str | None = None,
) -> list[str]:
    """Human-readable plan for the next outer-loop moves."""
    # Late-bind the narrator through the runner facade so tests patching
    # ``autonomous_loop_runner.AutonomyNextStepNarrator`` still take effect.
    from koru.autonomy.operator import operator_loop_runner as _runner_mod

    narrator = _runner_mod.AutonomyNextStepNarrator(
        args=args,
        project=project,
        waiting_ticket=waiting_ticket,
    )
    return narrator.narrate(
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        autopilot_status=autopilot_status,
        sleep_seconds=effective_sleep,
        stagnation_streak=stagnation_streak,
        stop_reason=stop_reason,
    )
