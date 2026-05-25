"""Typed autonomy events used by transparent decision traces."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any


def prompt_hash(prompt: str, *, length: int = 12) -> str:
    """Stable short hash for prompt correlation in logs and telemetry."""
    normalized = " ".join((prompt or "").split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:length]


def correlation_id(
    *,
    ticket_id: str,
    ide: str,
    prompt: str,
) -> str:
    """Build a readable event correlation id scoped to ticket + IDE + prompt."""
    ticket = ticket_id or "-"
    ide_id = ide or "-"
    digest = prompt_hash(prompt) or "no-prompt"
    return f"{ticket}:{ide_id}:{digest}"


@dataclass(frozen=True)
class AutonomyEvent:
    """Normalized event emitted into cycle telemetry and decision traces."""

    kind: str
    ts: float
    source: str
    ticket_id: str = "-"
    correlation_id: str = "-"
    environment_key: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _chat_kind(raw_type: str) -> str:
    raw = (raw_type or "").strip()
    if raw == "message.sent":
        return "chat.message_sent"
    if raw == "message.received":
        return "chat.message_received"
    return f"chat.{raw or 'unknown'}"


def _event_ts(event: dict[str, Any]) -> float:
    try:
        return float(event.get("ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _event_text(event: dict[str, Any]) -> str:
    return str(event.get("text") or event.get("summary") or "")


def _same_prompt(left: str, right: str) -> bool:
    left_norm = " ".join((left or "").split())
    right_norm = " ".join((right or "").split())
    if not left_norm or not right_norm:
        return False
    return left_norm == right_norm or left_norm in right_norm or right_norm in left_norm


def normalize_chat_events(
    events: list[dict[str, Any]],
    *,
    waiting_ticket: str,
    last_driven_ticket: str,
    last_driven_prompt: str,
    environment_key: str = "",
) -> list[AutonomyEvent]:
    """Normalize raw plugin chat events and attach ticket correlation when known."""
    return [
        _normalize_chat_event(
            event,
            waiting_ticket=waiting_ticket,
            last_driven_ticket=last_driven_ticket,
            last_driven_prompt=last_driven_prompt,
            environment_key=environment_key,
        )
        for event in events
    ]


def _normalize_chat_event(
    event: dict[str, Any],
    *,
    waiting_ticket: str,
    last_driven_ticket: str,
    last_driven_prompt: str,
    environment_key: str,
) -> AutonomyEvent:
    text = _event_text(event)
    ide = str(event.get("ide") or "")
    matched_last_prompt = _same_prompt(text, last_driven_prompt)
    ticket_id = _chat_event_ticket_id(
        matched_last_prompt=matched_last_prompt,
        last_driven_ticket=last_driven_ticket,
        waiting_ticket=waiting_ticket,
    )
    event_ts = _event_ts(event) or time.time()
    return AutonomyEvent(
        kind=_chat_kind(str(event.get("type") or "")),
        ts=event_ts,
        source="autopilot-plugin",
        ticket_id=ticket_id,
        correlation_id=correlation_id(
            ticket_id=ticket_id,
            ide=ide,
            prompt=text if text else last_driven_prompt,
        ),
        environment_key=environment_key,
        payload=_chat_event_payload(
            event,
            ide=ide,
            event_ts=event_ts,
            matched_last_prompt=matched_last_prompt,
            last_driven_ticket=last_driven_ticket,
            waiting_ticket=waiting_ticket,
        ),
    )


def _chat_event_ticket_id(
    *,
    matched_last_prompt: bool,
    last_driven_ticket: str,
    waiting_ticket: str,
) -> str:
    if matched_last_prompt and last_driven_ticket:
        return last_driven_ticket
    if waiting_ticket and waiting_ticket != "-":
        return waiting_ticket
    return "-"


def _chat_event_payload(
    event: dict[str, Any],
    *,
    ide: str,
    event_ts: float,
    matched_last_prompt: bool,
    last_driven_ticket: str,
    waiting_ticket: str,
) -> dict[str, Any]:
    return {
        "ide": ide,
        "chat": str(event.get("chat") or "default"),
        "raw_type": str(event.get("type") or ""),
        "age_seconds": max(0.0, time.time() - event_ts),
        "matches_last_driven_prompt": matched_last_prompt,
        "last_driven_ticket": last_driven_ticket or "-",
        "waiting_ticket": waiting_ticket or "-",
    }


__all__ = [
    "AutonomyEvent",
    "correlation_id",
    "normalize_chat_events",
    "prompt_hash",
]
