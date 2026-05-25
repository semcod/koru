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
    normalized: list[AutonomyEvent] = []
    for event in events:
        text = _event_text(event)
        ide = str(event.get("ide") or "")
        matched_last_prompt = _same_prompt(text, last_driven_prompt)
        ticket_id = last_driven_ticket if matched_last_prompt and last_driven_ticket else "-"
        if ticket_id == "-" and waiting_ticket and waiting_ticket != "-":
            ticket_id = waiting_ticket
        normalized.append(
            AutonomyEvent(
                kind=_chat_kind(str(event.get("type") or "")),
                ts=_event_ts(event) or time.time(),
                source="autopilot-plugin",
                ticket_id=ticket_id,
                correlation_id=correlation_id(
                    ticket_id=ticket_id,
                    ide=ide,
                    prompt=text if text else last_driven_prompt,
                ),
                environment_key=environment_key,
                payload={
                    "ide": ide,
                    "chat": str(event.get("chat") or "default"),
                    "raw_type": str(event.get("type") or ""),
                    "age_seconds": max(0.0, time.time() - (_event_ts(event) or time.time())),
                    "matches_last_driven_prompt": matched_last_prompt,
                    "last_driven_ticket": last_driven_ticket or "-",
                    "waiting_ticket": waiting_ticket or "-",
                },
            )
        )
    return normalized


__all__ = [
    "AutonomyEvent",
    "correlation_id",
    "normalize_chat_events",
    "prompt_hash",
]
