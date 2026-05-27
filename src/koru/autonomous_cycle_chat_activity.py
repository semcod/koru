from __future__ import annotations

import os
import time
from hashlib import sha1
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity_text import (
    compact_question_text as _compact_question_text,
    extract_needs_input_question as _extract_needs_input_question,
    latest_received_text as _latest_received_text,
    looks_like_autopilot_generated_prompt as _looks_like_autopilot_generated_prompt,
    looks_like_explicit_intake_text as _looks_like_explicit_intake_text,
    normalize_prompt_text as _normalize_prompt_text,
)
from koru.autonomous_cycle_chat_activity_config import (
    autopilot_escalation_cooldown_seconds as _autopilot_escalation_cooldown_seconds,
    autopilot_redrive_cooldown_seconds as _autopilot_redrive_cooldown_seconds,
    chat_intake_ticket_enabled as _chat_intake_ticket_enabled,
    llm_needs_input_heuristic_enabled as _llm_needs_input_heuristic_enabled,
    llm_needs_input_ticket_enabled as _llm_needs_input_ticket_enabled,
    llm_needs_input_ticket_priority as _llm_needs_input_ticket_priority,
    llm_needs_input_ticket_queue_name as _llm_needs_input_ticket_queue_name,
    llm_reflection_summary_max_age_seconds as _llm_reflection_summary_max_age_seconds,
)
from koru.autonomous_cycle_chat_activity_analyzer import (
    _CHAT_ACTIVITY_TYPES,
    _age_seconds_from_label,
    _chat_activity_cooldown_for_state,
    _determine_chat_activity_status,
    _event_is_self_drive_for_other_ticket,
    _event_matches_last_driven_prompt,
    _event_timestamp,
    _filter_chat_activity_events_for_waiting_ticket,
    _last_self_drive_event_age,
    _last_successful_drive_ack_age,
    _llx_chat_reflection_enabled,
    _recent_chat_activity_events,
    _recent_chat_history_fallback,
    _record_normalized_chat_activity_events,
    _state_events_to_chat_events,
    classify_chat_event,
    decide_intake_ticket,
    decide_redrive_cooldown,
    explain_skip,
)
from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.prompts import PromptDecision
from koru.autonomy.reflection_policy import decide_chat_reflection
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.tasks import create_nl_task


def _cycle_attr(name: str, fallback: Any) -> Any:
    from koru import autonomous_cycle as _cycle_mod

    return getattr(_cycle_mod, name, fallback)


from koru.autonomous_cycle_chat_activity_tickets import (
    _external_message_sent_text,
    _llm_needs_input_operator_payload,
    _llm_needs_input_summary,
    _llm_needs_input_waiting_ticket,
    _note_reused_llm_needs_input_operator_ticket,
    _recent_llm_reflection_summary,
    _upsert_chat_intake_operator_ticket,
    _upsert_llm_needs_input_operator_ticket,
    _waiting_ticket_has_chat_intake_label,
)


def _planning_chat_reflection_enabled() -> bool:
    raw = os.environ.get("KORU_PLANNING_LLM", "1").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def _chat_reflection_enabled() -> bool:
    return _llx_chat_reflection_enabled() or _planning_chat_reflection_enabled()


def _inject_reflection_summary_into_prompt(
    state: AutoloopState,
    queue_result: QueueLoopResult,
    decision: PromptDecision,
) -> PromptDecision:
    if queue_result.last_status != "waiting_input":
        return decision
    if decision.kind not in {"ticket_prompt", "fallback_prompt", "escalation_prompt"}:
        return decision
    summary = _recent_llm_reflection_summary(state)
    if not summary:
        return decision
    snippet = summary[:320]
    augmented = (
        decision.prompt.rstrip()
        + "\n\nRecent IDE chat context:\n"
        + f"- {snippet}\n"
        + "Use this context to continue from current progress. Do not restart from scratch."
    )
    return PromptDecision(
        prompt=augmented,
        kind=decision.kind,
        skip=decision.skip,
        skip_reason=decision.skip_reason,
    )


def _recent_message_sent_allows_redrive(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    last_type: str,
    age_label: str,
    waiting_ticket: str,
    report_progress: Any,
) -> bool:
    from koru.autonomous_cycle_skip_conditions import _waiting_ticket_has_label

    has_received = any(str(ev.get("type") or "") == "message.received" for ev in recent_events)
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if not (
        last_type == "message.sent"
        and not has_received
        and getattr(queue_result, "last_status", "") == "waiting_input"
        and last_kind != "escalation_prompt"
        and not _waiting_ticket_has_label(project, queue_result, "llm-ready")
    ):
        return False
    report_progress(
        "- autopilot redrive allowed (message.sent without "
        f"message.received age={age_label} ticket={waiting_ticket})",
    )
    return True


def _upsert_reflection_needs_input_ticket(
    *,
    reflection: Any,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    summary: str,
    reflection_events: list[Any],
    cycle_telemetry: dict[str, Any],
    report_progress: Any,
) -> None:
    """Upsert an operator ticket when reflection indicates needs_input and not done."""
    if not (reflection.needs_input and not reflection.done):
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=summary,
        reflection_events=reflection_events,
        report_progress=report_progress,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket


def _apply_llx_chat_reflection(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    waiting_ticket: str,
    ide: str | None,
    reflection_events: list[Any],
    report_progress: Any,
) -> tuple[bool, bool]:
    """Try llx first, then fall back to OpenRouter-native planning_llm.reflect_on_chat."""
    ticket_title = getattr(queue_result, "last_message", "") or ""
    raw_driven_prompt = getattr(state, "last_driven_prompt", "")
    driven_prompt = raw_driven_prompt if isinstance(raw_driven_prompt, str) else ""

    reflection = _reflect_with_llx(
        waiting_ticket=waiting_ticket,
        ticket_title=ticket_title,
        driven_prompt=driven_prompt,
        ide=ide,
        reflection_events=reflection_events,
    )
    if reflection is None:
        reflection = _reflect_with_openrouter(
            waiting_ticket=waiting_ticket,
            ticket_title=ticket_title,
            driven_prompt=driven_prompt,
            reflection_events=reflection_events,
        )
        if reflection is not None:
            report_progress("- llx reflect: using OpenRouter fallback")

    if reflection is None:
        return False, False

    return _record_llx_chat_reflection(
        reflection=reflection,
        project=project,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=cycle_telemetry,
        reflection_events=reflection_events,
        report_progress=report_progress,
    )


def _reflect_with_llx(
    *,
    waiting_ticket: str,
    ticket_title: str,
    driven_prompt: str,
    ide: str | None,
    reflection_events: list[Any],
) -> Any | None:
    try:
        from koru.llm_reflect import llm_reflect_enabled, reflect_on_chat as _llx_reflect
    except ImportError:
        return None
    if not llm_reflect_enabled():
        return None
    return _llx_reflect(
        ticket_id=waiting_ticket or "-",
        ticket_title=ticket_title,
        driven_prompt=driven_prompt or ticket_title,
        ide=ide or "",
        events=reflection_events or None,
    )


def _reflect_with_openrouter(
    *,
    waiting_ticket: str,
    ticket_title: str,
    driven_prompt: str,
    reflection_events: list[Any],
) -> Any | None:
    try:
        from koru.autonomy.planning_llm import reflect_on_chat as _or_reflect
    except ImportError:
        return None
    return _or_reflect(
        ticket_id=waiting_ticket or "-",
        ticket_title=ticket_title,
        driven_prompt=driven_prompt or ticket_title,
        chat_events=_reflection_chat_events_payload(reflection_events),
    )


def _reflection_chat_events_payload(reflection_events: list[Any]) -> list[dict[str, Any]]:
    return [_reflection_chat_event_payload(event) for event in (reflection_events or [])]


def _reflection_chat_event_payload(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return {
            "type": event.get("type"),
            "text": event.get("text"),
            "summary": event.get("summary"),
        }
    return {
        "type": getattr(event, "type", ""),
        "text": getattr(event, "text", ""),
        "summary": getattr(event, "summary", ""),
    }


def _record_llx_chat_reflection(
    *,
    reflection: Any,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    reflection_events: list[Any],
    report_progress: Any,
) -> tuple[bool, bool]:
    cycle_telemetry["autopilot_llx_reflection"] = {
        "done": reflection.done,
        "needs_input": reflection.needs_input,
        "summary": reflection.summary,
    }
    summary = (reflection.summary or "").strip()
    if summary:
        state.last_llm_reflection_summary = summary[:320]
        state.last_llm_reflection_ts = time.time()
    report_progress(
        "- llx reflect: "
        f"done={reflection.done} needs_input={reflection.needs_input} "
        f"summary={reflection.summary!r}",
    )
    _upsert_reflection_needs_input_ticket(
        reflection=reflection,
        project=project,
        queue_result=queue_result,
        state=state,
        summary=summary,
        reflection_events=reflection_events,
        cycle_telemetry=cycle_telemetry,
        report_progress=report_progress,
    )
    return True, bool(reflection.done)


def _apply_needs_input_heuristic(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    reflection_events: list[Any],
    report_progress: Any,
) -> None:
    if not _llm_needs_input_heuristic_enabled():
        return
    question = _extract_needs_input_question(reflection_events, "")
    if not question:
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=_latest_received_text(reflection_events) or question,
        reflection_events=reflection_events,
        report_progress=report_progress,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_needs_input_heuristic"] = True
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket
    report_progress(f"- needs_input heuristic: question={question!r}")


def _check_recent_drive_ack_skip(
    state: AutoloopState,
    cooldown: float,
    waiting_ticket: str,
    ide: str | None,
    cycle_telemetry: dict[str, Any],
    report_progress: Any,
) -> bool:
    drive_ack_age = _last_successful_drive_ack_age(
        state,
        waiting_ticket=waiting_ticket,
        ide=ide,
    )
    if drive_ack_age is not None and drive_ack_age <= cooldown:
        drive_ack_age_label = f"{drive_ack_age:.0f}s"
        cycle_telemetry["autopilot_skipped_chat_activity"] = True
        cycle_telemetry["autopilot_chat_activity_last_event"] = "drive.ack"
        report_progress(
            "- autopilot skipped (recent_drive_ack "
            f"last=drive.ack age={drive_ack_age_label} cooldown={cooldown:.0f}s "
            f"ticket={waiting_ticket}; not a daemon failure; "
            "waiting avoids pasting over an active IDE chat; "
            "tune with KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS)",
        )
        return True
    return False


def _check_chat_intake_skip(
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    cycle_telemetry: dict[str, Any],
    report_progress: Any,
) -> bool:
    intake_ticket = _upsert_chat_intake_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        recent_events=recent_events,
        cycle_telemetry=cycle_telemetry,
        report_progress=report_progress,
    )
    if decide_intake_ticket(intake_ticket):
        cycle_telemetry["autopilot_skipped_chat_intake"] = True
        return True
    return False


def _check_recent_self_drive_skip(
    state: AutoloopState,
    cooldown: float,
    waiting_ticket: str,
    recent_events: list[dict[str, Any]],
    cycle_telemetry: dict[str, Any],
    report_progress: Any,
) -> bool:
    has_received = any(str(ev.get("type") or "") == "message.received" for ev in recent_events)
    self_drive_age = _last_self_drive_event_age(state, recent_events)
    if (
        self_drive_age is not None
        and self_drive_age <= cooldown
        and not has_received
        and not _chat_reflection_enabled()
    ):
        self_drive_age_label = f"{self_drive_age:.0f}s"
        cycle_telemetry["autopilot_skipped_chat_activity"] = True
        cycle_telemetry["autopilot_chat_activity_last_event"] = "message.sent"
        report_progress(
            "- autopilot skipped (recent_self_drive "
            f"last=message.sent age={self_drive_age_label} cooldown={cooldown:.0f}s "
            f"ticket={waiting_ticket})",
        )
        return True
    return False


def _apply_chat_activity_skip_decision(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    waiting_ticket: str,
    ide: str | None,
    reflection_events: list[Any],
    last_type: str,
    age_label: str,
    cooldown: float,
    report_progress: Any,
) -> bool:
    decision = decide_redrive_cooldown(
        event_type=last_type,
        age_seconds=_age_seconds_from_label(age_label),
        cooldown_seconds=cooldown,
        waiting_ticket=waiting_ticket,
    )
    if not bool(decision["should_skip"]):
        return False

    cycle_telemetry["autopilot_skipped_chat_activity"] = True
    cycle_telemetry["autopilot_chat_activity_last_event"] = last_type
    cycle_telemetry["autopilot_skipped_chat_activity_because"] = explain_skip(decision)
    report_progress(f"- autopilot skipped ({explain_skip(decision)})")
    reflection_policy = decide_chat_reflection(
        enabled=_chat_reflection_enabled(),
        last_type=last_type,
        reflection_events=reflection_events,
    )
    cycle_telemetry["autopilot_llx_reflection_policy"] = reflection_policy.to_dict()
    if reflection_policy.should_reflect:
        reflection_resolved, reflection_done = _apply_llx_chat_reflection(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            waiting_ticket=waiting_ticket,
            ide=ide,
            reflection_events=reflection_events,
            report_progress=report_progress,
        )
    else:
        reflection_resolved, reflection_done = False, False
    if reflection_done:
        return True

    # Fallback for environments where llx/OpenRouter is unavailable.
    if not reflection_resolved:
        _apply_needs_input_heuristic(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            reflection_events=reflection_events,
            report_progress=report_progress,
        )
    return True


def _skip_due_to_recent_chat_activity(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    """Return True iff the loop should skip drive because the IDE chat is busy.

    Two signals (both optional, fail-closed → no skip):

    1. Plain cooldown: ``message.sent`` for the same ticket within
       :func:`_autopilot_redrive_cooldown_seconds`. This is the cheap path —
       no llx, no network — and covers the common case where koru just drove
       the prompt and the LLM is still streaming a response.
    2. Optional :mod:`koru.llm_reflect` (when enabled and llx
       is on PATH). Asks an OpenRouter-backed model to read the recent
       ``message.received`` events and decide ``{done, needs_input}``. If
         it returns ``needs_input=true`` we skip and upsert one operator ticket;
         if ``done=true`` we also skip redrive and let the queue state update
         naturally.
    """
    report_progress = _hp
    cooldown = _chat_activity_cooldown_for_state(state)
    if cooldown <= 0:
        return False

    ide = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip().lower() or None
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)

    if _check_recent_drive_ack_skip(
        state,
        cooldown,
        waiting_ticket,
        ide,
        cycle_telemetry,
        report_progress,
    ):
        return True

    recent_events = _recent_chat_activity_events(
        state,
        ide=ide,
        within_seconds=cooldown,
    )
    _record_normalized_chat_activity_events(
        state=state,
        cycle_telemetry=cycle_telemetry,
        recent_events=recent_events,
        waiting_ticket=waiting_ticket,
    )
    recent_events = _filter_chat_activity_events_for_waiting_ticket(
        state,
        recent_events,
        waiting_ticket,
    )
    reflection_events = _state_events_to_chat_events(recent_events)

    if _check_chat_intake_skip(
        project,
        queue_result,
        state,
        recent_events,
        cycle_telemetry,
        report_progress,
    ):
        return True

    if _check_recent_self_drive_skip(
        state,
        cooldown,
        waiting_ticket,
        recent_events,
        cycle_telemetry,
        report_progress,
    ):
        return True

    has_activity, last_type, age_label, reflection_events = _determine_chat_activity_status(
        state=state,
        ide=ide,
        cooldown=cooldown,
        recent_events=recent_events,
        reflection_events=reflection_events,
    )
    if not has_activity:
        return False

    if recent_events and _recent_message_sent_allows_redrive(
        project=project,
        queue_result=queue_result,
        state=state,
        recent_events=recent_events,
        last_type=last_type,
        age_label=age_label,
        waiting_ticket=waiting_ticket,
        report_progress=report_progress,
    ):
        return False

    return _apply_chat_activity_skip_decision(
        project=project,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=cycle_telemetry,
        waiting_ticket=waiting_ticket,
        ide=ide,
        reflection_events=reflection_events,
        last_type=last_type,
        age_label=age_label,
        cooldown=cooldown,
        report_progress=report_progress,
    )
