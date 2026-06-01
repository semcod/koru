from __future__ import annotations

import time
from typing import Any

from koru.autonomous_cycle_chat_activity_config import (
    autopilot_escalation_cooldown_seconds as _autopilot_escalation_cooldown_seconds,
    autopilot_redrive_cooldown_seconds as _autopilot_redrive_cooldown_seconds,
)
from koru.autonomous_cycle_chat_activity_text import (
    normalize_prompt_text as _normalize_prompt_text,
)
from koru.autonomy.events import normalize_chat_events
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult

_CHAT_ACTIVITY_TYPES = ("message.sent", "message.received")


def _event_timestamp(payload: dict[str, Any], *, default: float = 0.0) -> float:
    try:
        return float(payload.get("ts") or default)
    except (TypeError, ValueError):
        return default


def _recent_chat_activity_events(
    state: AutoloopState,
    *,
    ide: str | None,
    within_seconds: float,
) -> list[dict[str, Any]]:
    now = time.time()
    recent: list[dict[str, Any]] = []
    raw_events = getattr(state, "autopilot_events", None)
    if not isinstance(raw_events, list):
        return []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        ev_type = str(raw.get("type") or "")
        if ev_type not in _CHAT_ACTIVITY_TYPES:
            continue
        if ide and str(raw.get("ide") or "") != ide:
            continue
        ts = _event_timestamp(raw, default=0.0)
        if ts <= 0:
            continue
        if (now - ts) > within_seconds:
            continue
        recent.append(raw)
    return recent[-20:]


def _state_events_to_chat_events(recent_events: list[dict[str, Any]]) -> list[Any]:
    try:
        from koruide.chat_history import ChatEvent
    except ImportError:
        return []
    converted: list[Any] = []
    for event in recent_events:
        converted.append(
            ChatEvent(
                ts=_event_timestamp(event, default=time.time()),
                type=str(event.get("type") or ""),
                ide=str(event.get("ide") or ""),
                chat=str(event.get("chat") or "default"),
                text=str(event.get("text") or ""),
                summary=str(event.get("summary") or ""),
                length=int(event.get("length") or 0),
                reason=str(event.get("reason") or ""),
            ),
        )
    return converted


def _chat_activity_cooldown_for_state(state: AutoloopState) -> float:
    cooldown = _autopilot_redrive_cooldown_seconds()
    if cooldown <= 0:
        return cooldown
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if last_kind == "escalation_prompt":
        return _autopilot_escalation_cooldown_seconds(cooldown)
    return cooldown


def _last_successful_drive_ack_age(
    state: AutoloopState,
    *,
    waiting_ticket: str,
    ide: str | None,
) -> float | None:
    try:
        last_sent_ts = float(getattr(state, "last_message_sent_ts", 0.0) or 0.0)
    except (TypeError, ValueError):
        last_sent_ts = 0.0
    raw_last_sent_ide = getattr(state, "last_message_sent_ide", "")
    last_sent_ide = raw_last_sent_ide if isinstance(raw_last_sent_ide, str) else ""
    if ide and last_sent_ide and last_sent_ide != ide:
        return None
    last_driven_ticket = str(getattr(state, "last_driven_ticket_id", "") or "")
    if waiting_ticket == "-" or last_driven_ticket != waiting_ticket or last_sent_ts <= 0:
        return None
    return max(0.0, time.time() - last_sent_ts)


def _event_matches_last_driven_prompt(
    state: AutoloopState,
    event: dict[str, Any],
) -> bool:
    if str(event.get("type") or "") != "message.sent":
        return False
    event_text = _normalize_prompt_text(str(event.get("text") or ""))
    last_driven = _normalize_prompt_text(str(getattr(state, "last_driven_prompt", "") or ""))
    if not event_text or not last_driven:
        return False
    return event_text == last_driven or event_text in last_driven or last_driven in event_text


def _last_self_drive_event_age(
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
) -> float | None:
    for event in reversed(recent_events):
        if not _event_matches_last_driven_prompt(state, event):
            continue
        return max(0.0, time.time() - _event_timestamp(event, default=0.0))
    return None


def _event_is_self_drive_for_other_ticket(
    state: AutoloopState,
    event: dict[str, Any],
    waiting_ticket: str,
) -> bool:
    if not _event_matches_last_driven_prompt(state, event):
        return False
    last_driven_ticket = str(getattr(state, "last_driven_ticket_id", "") or "")
    return bool(
        waiting_ticket
        and waiting_ticket != "-"
        and last_driven_ticket
        and last_driven_ticket != waiting_ticket
    )


def _filter_chat_activity_events_for_waiting_ticket(
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    waiting_ticket: str,
) -> list[dict[str, Any]]:
    return [
        event
        for event in recent_events
        if not _event_is_self_drive_for_other_ticket(state, event, waiting_ticket)
    ]


def _record_normalized_chat_activity_events(
    *,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    recent_events: list[dict[str, Any]],
    waiting_ticket: str,
    environment_key: str = "",
) -> None:
    if not recent_events:
        return
    normalized = normalize_chat_events(
        recent_events,
        waiting_ticket=waiting_ticket,
        last_driven_ticket=str(getattr(state, "last_driven_ticket_id", "") or ""),
        last_driven_prompt=str(getattr(state, "last_driven_prompt", "") or ""),
        environment_key=environment_key,
    )
    cycle_telemetry["autopilot_chat_activity_events"] = [
        event.to_dict() for event in normalized[-10:]
    ]


def _llx_chat_reflection_enabled() -> bool:
    try:
        from koru.llm_reflect import llm_reflect_enabled
    except ImportError:
        return False
    return bool(llm_reflect_enabled())


def _recent_chat_history_fallback(
    *,
    ide: str | None,
    cooldown: float,
    reflection_events: list[Any],
) -> tuple[str, str, list[Any]] | None:
    try:
        from koruide.chat_history import has_recent_activity, last_event, read_events
    except ImportError:
        return None
    if not has_recent_activity(
        ide=ide,
        within_seconds=cooldown,
        types=_CHAT_ACTIVITY_TYPES,
    ):
        return None
    last = last_event(ide=ide, types=_CHAT_ACTIVITY_TYPES)
    age_label = f"{last.age_seconds:.0f}s" if last is not None else "?"
    last_type = last.type if last is not None else "?"
    if not reflection_events:
        reflection_events = read_events(
            ide=ide,
            max_age_seconds=cooldown,
            types=_CHAT_ACTIVITY_TYPES,
            limit=20,
        )
    return last_type, age_label, reflection_events


def _determine_chat_activity_status(
    state: AutoloopState,
    ide: str | None,
    cooldown: float,
    recent_events: list[dict[str, Any]],
    reflection_events: list[Any],
) -> tuple[bool, str, str, list[Any]]:
    return classify_chat_event(
        state=state,
        ide=ide,
        cooldown=cooldown,
        recent_events=recent_events,
        reflection_events=reflection_events,
    )


def classify_chat_event(
    *,
    state: AutoloopState,
    ide: str | None,
    cooldown: float,
    recent_events: list[dict[str, Any]],
    reflection_events: list[Any],
) -> tuple[bool, str, str, list[Any]]:
    """Return ``(has_activity, event_type, age_label, reflection_events)``."""
    if recent_events:
        last_payload = recent_events[-1]
        last_type = str(last_payload.get("type") or "?")
        age_seconds = max(0.0, time.time() - _event_timestamp(last_payload, default=0.0))
        age_label = f"{age_seconds:.0f}s"
        return True, last_type, age_label, reflection_events

    fallback = _recent_chat_history_fallback(
        ide=ide,
        cooldown=cooldown,
        reflection_events=reflection_events,
    )
    if fallback is None:
        return False, "", "", []
    last_type, age_label, reflection_events = fallback
    return True, last_type, age_label, reflection_events


def decide_intake_ticket(intake_ticket: str | None) -> bool:
    """Pure decision: skip redrive when a chat intake ticket was upserted."""
    return bool(intake_ticket)


def decide_redrive_cooldown(
    *,
    event_type: str,
    age_seconds: float,
    cooldown_seconds: float,
    waiting_ticket: str,
) -> dict[str, str | bool]:
    """Pure cooldown decision used by chat-activity skip paths."""
    event = str(event_type or "?")
    event_age_seconds = max(0.0, float(age_seconds))
    cooldown = max(0.0, float(cooldown_seconds))
    should_skip = bool(event and event_age_seconds <= cooldown)
    because = (
        f"recent_chat_activity last={event} age={event_age_seconds:.0f}s cooldown={cooldown:.0f}s "
        f"ticket={waiting_ticket}"
    )
    return {
        "should_skip": should_skip,
        "event_type": event,
        "because": because,
        "age": f"{event_age_seconds:.0f}s",
    }


def explain_skip(decision: dict[str, str | bool]) -> str:
    """Render a human-readable skip explanation from a pure decision payload."""
    return str(decision.get("because") or "")


def _age_seconds_from_label(age_label: str) -> float:
    if age_label.endswith("s"):
        try:
            return float(age_label[:-1])
        except ValueError:
            return 0.0
    return 0.0
