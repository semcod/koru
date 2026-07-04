"""Idle warnings, mission snapshots, and operator next-step logging."""

from __future__ import annotations

from typing import Any

from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_by_from_autopilot_status,
    _is_plugin_blocker,
    _safe_dashboard_action_urls,
)


def _should_warn_idle_no_ticket(
    *,
    queue_status: str,
    waiting_ticket: str,
    autopilot_status: str,
) -> bool:
    if waiting_ticket and waiting_ticket != "-":
        return False
    status = (autopilot_status or "").strip().lower()
    queue = (queue_status or "").strip().lower()
    return queue == "idle" or "idle_no_ticket" in status


def _idle_no_ticket_warning(project: Any | None) -> tuple[str, str, dict[str, Any]]:
    urls = _safe_dashboard_action_urls(project)
    message = "autonomia nie wykonuje zadania: brak otwartych ticketów w planfile"
    hint = (
        "plan: szczegół→ogół — najpierw planfile queue, potem idle scan/code2llm; "
        "workflow standaryzowany: gdy po scan/code2llm brak pracy, system "
        "auto-tworzy/reuzywa ticket discovery dla IDE LLM; "
        "jezeli nadal brak ruchu, zlec IDE LLM pytanie: "
        "'Co jeszcze zostalo do wykonania? zrob z tego nastepne tickety do planfile.' "
        "i zamien odpowiedz na tickety; "
        "goal/costs są advisory; metrun/prefact/pfix czytane z artefaktów przez koru scan. "
        f"Napisz ticket w Web GUI: {urls['create_project_ticket']} ; "
        f"lista ticketów: {urls['tickets']}"
    )
    data = {
        "blocked_by": "idle_no_ticket",
        "create_ticket_url": urls["create_project_ticket"],
        "tickets_url": urls["tickets"],
    }
    return message, hint, data


def _emit_idle_no_ticket_warning(
    *,
    args: Any,
    project: Any | None,
    queue_status: str,
    waiting_ticket: str,
    autopilot_status: str,
) -> None:
    if not _should_warn_idle_no_ticket(
        queue_status=queue_status,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
    ):
        return
    from koru.activity_log import activity_warn

    message, hint, data = _idle_no_ticket_warning(project)
    activity_warn(message, hint=hint, fmt=args.emit_events, data=data)


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in "".join(ch.lower() if ch.isalnum() else "-" for ch in value).split("-")
        if part
    )[:48]


def _current_mission_lines(
    *,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
) -> list[str]:
    """Compact mission snapshot for the operator shell.

    Gives one stable place to see the current ticket, blocker, and next
    expected movement without reading the whole cycle transcript.
    """
    queue_status = str(getattr(queue_result, "last_status", "") or "unknown")
    if not waiting_ticket or waiting_ticket == "-":
        return []
    blocker = _blocked_by_from_autopilot_status(autopilot_status) or "none"
    line_1 = (
        "koru autonomous: current mission "
        f"ticket={waiting_ticket} queue={queue_status} blocker={blocker}"
    )
    if _is_plugin_blocker(blocker):
        line_2 = (
            "koru autonomous: current mission next="
            "reload/reconnect plugin, then rerun queue for the same ticket"
        )
    elif blocker == "chat_activity":
        line_2 = (
            "koru autonomous: current mission next="
            f"wait {effective_sleep:g}s for chat cooldown, then reconsider redrive "
            "(tune: KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS)"
        )
    elif queue_status == "waiting_input":
        line_2 = (
            "koru autonomous: current mission next="
            "operator or IDE work must move the ticket out of waiting_input"
        )
    else:
        line_2 = (
            "koru autonomous: current mission next="
            "recheck queue state and continue the same ticket"
        )
    return [line_1, line_2]


def _log_operator_next_steps(
    *,
    args: Any,
    project: Any | None,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    loop_state: Any,
    stop_reason: str | None,
    stdio_info: Any,
    autopilot_ide: str = "",
) -> None:
    # Late-bind every helper through the runner facade so tests patching
    # ``autonomous_loop_runner._current_mission_lines`` / ``_operator_next_steps``
    # / ``_quick_action_lines`` / ``_emit_quick_action_line`` still take effect.
    from koru.autonomy.operator import operator_loop_runner as _runner_mod

    for line in _runner_mod._current_mission_lines(
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
    ):
        stdio_info(line, fmt=args.emit_events)
    for line in _runner_mod._operator_next_steps(
        args=args,
        project=project,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        stagnation_streak=int(getattr(loop_state, "stagnation_streak", 0) or 0),
        stop_reason=stop_reason,
    ):
        stdio_info(f"koru autonomous: next {line}", fmt=args.emit_events)
    quick_action_lines = _runner_mod._quick_action_lines(
        project=project,
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
    )
    _runner_mod._record_quick_action_control_commands(
        project=project,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        quick_actions=quick_action_lines,
    )
    for action in quick_action_lines:
        _runner_mod._emit_quick_action_line(args=args, action=action, stdio_info=stdio_info)
