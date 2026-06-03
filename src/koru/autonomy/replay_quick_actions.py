"""Legacy quick-action conversion for replay actions."""

from __future__ import annotations

from koru.autonomy.replay_builders import (
    autopilot_retry_drive,
    ide_connect_plugin,
    scan_force,
    ticket_input,
    ticket_open,
    trace_show_decisions,
    trace_show_interfaces,
    wup_show_health,
)
from koru.autonomy.replay_types import ReplayAction


def quick_action_to_replay(
    action_text: str,
    *,
    autopilot_ide: str = "",
    waiting_ticket: str = "",
    base_url: str = "http://127.0.0.1:8765",
) -> ReplayAction | None:
    """Convert a legacy ``[label] `cmd``` quick action to a ReplayAction."""
    label, body = _split_quick_action_text(action_text)
    label_lower = label.lower()
    action = _quick_static_action(label_lower, base_url=base_url, autopilot_ide=autopilot_ide)
    if action is not None:
        return action
    return _quick_ticket_action(
        label_lower,
        body,
        autopilot_ide=autopilot_ide,
        waiting_ticket=waiting_ticket,
        base_url=base_url,
    )


def _quick_static_action(
    label_lower: str,
    *,
    base_url: str,
    autopilot_ide: str,
) -> ReplayAction | None:
    if label_lower == "show decision trace":
        return trace_show_decisions(base_url)
    if label_lower == "show interfaces":
        return trace_show_interfaces(base_url)
    if label_lower == "reconnect plugin":
        ide = autopilot_ide or "auto"
        return ide_connect_plugin(ide)
    if label_lower in ("force fresh scan", "force scan"):
        return scan_force()
    if label_lower == "show wup track":
        return wup_show_health()
    return None


def _quick_ticket_action(
    label_lower: str,
    body: str,
    *,
    autopilot_ide: str,
    waiting_ticket: str,
    base_url: str,
) -> ReplayAction | None:
    if not waiting_ticket:
        return None
    if label_lower == "mark ticket input":
        return ticket_input(waiting_ticket)
    if label_lower == "open ticket":
        url = (
            body.split("#", 1)[0].strip()
            if body.startswith(("http://", "https://"))
            else base_url
        )
        return ticket_open(waiting_ticket, url)
    if label_lower == "retry submit" and waiting_ticket:
        return autopilot_retry_drive(autopilot_ide or "auto", waiting_ticket)
    return None


def _split_quick_action_text(text: str) -> tuple[str, str]:
    """Split ``[label] body`` into (label, body)."""
    text = text.strip()
    if text.startswith("[") and "]" in text:
        label, body = text[1:].split("]", 1)
        return label.strip(), body.strip()
    return "", text


__all__ = ["quick_action_to_replay"]
