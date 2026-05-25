"""Plugin event message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate plugin event
handling logic (session events, handoff orchestration, NDJSON event logging)
into a cohesive module.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koruide.daemon.protocol import _Client
from koruide.protocol import Message, ack, chat_send
from koruide.daemon.storage import start_new_log_session


@dataclass(frozen=True)
class _PluginEventHandoff:
    """Result of basic plugin event handling when handoff is required."""

    ack_info: dict[str, Any]
    chat: str
    reason: str


def _event_path() -> Path:
    """Path to the NDJSON event file shared with autonomous."""
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "koru-autopilot-events.ndjson"


def _append_event(client: _Client, msg: Message) -> None:
    """Persist plugin event to the shared NDJSON file."""
    try:
        path = _event_path()
        payload = {
            "ts": time.time(),
            "type": msg.type,
            "ide": client.ide,
        }
        payload.update(msg.data)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, separators=(",", ":")) + "\n")
    except OSError:
        pass


def _plugin_event_should_handoff(daemon: Any, msg: Message) -> bool:
    """Check if plugin event should trigger handoff."""
    return msg.type == "session.ended" and daemon.handoff is not None


def _ack_plugin_event_without_handoff(
    daemon: Any,
    client: _Client,
    msg: Message,
    ack_info: dict[str, Any],
) -> None:
    """Ack plugin event without handoff and relay message.sent if needed."""
    from koruide.daemon.handlers_ack import _relay_message_sent_ack

    daemon._send(client, ack(msg.id or "session-event", info=ack_info).encode())
    if msg.type == "message.sent":
        _relay_message_sent_ack(daemon, client, msg)


def _handle_plugin_event_basic(
    daemon: Any,
    client: _Client,
    msg: Message,
) -> _PluginEventHandoff | None:
    """Handle basic plugin event logging and acknowledgment."""
    chat = msg.data.get("chat") or "default"
    reason = msg.data.get("reason") or ""
    daemon.log(f"event {msg.type} ide={client.ide} chat={chat} reason={reason!r}")
    _append_event(client, msg)
    daemon.audit.record(
        "plugin_event",
        type=msg.type,
        ide=client.ide,
        **msg.data,
    )
    ack_info: dict[str, Any] = {"event": msg.type}
    if not _plugin_event_should_handoff(daemon, msg):
        _ack_plugin_event_without_handoff(daemon, client, msg, ack_info)
        return None
    return _PluginEventHandoff(ack_info=ack_info, chat=chat, reason=reason)


def _check_handoff_cooldown(daemon: Any, ack_info: dict[str, Any]) -> bool:
    """Check if handoff cooldown period has passed."""
    elapsed = time.monotonic() - daemon._last_chat_send_at
    if elapsed < daemon.handoff_cooldown:
        ack_info["handoff"] = "skipped"
        ack_info["reason"] = f"cooldown ({elapsed:.2f}s < {daemon.handoff_cooldown:.2f}s)"
        return False
    return True


def _execute_handoff(
    daemon: Any,
    client: _Client,
    msg: Message,
    chat: str,
    reason: str,
    ack_info: dict[str, Any],
) -> str | None:
    """Execute handoff and return text if successful."""
    try:
        text = daemon.handoff({"chat": chat, "reason": reason, "ide": client.ide})
    except Exception as exc:
        ack_info["handoff"] = "error"
        ack_info["reason"] = str(exc)
        daemon._send(client, ack(msg.id or "session-event", info=ack_info).encode())
        daemon.log(f"handoff failed: {exc}")
        return None
    if not text:
        ack_info["handoff"] = "skipped"
        ack_info["reason"] = "handoff returned empty text"
        daemon._send(client, ack(msg.id or "session-event", info=ack_info).encode())
        return None
    return text


def _forward_handoff_to_plugin(
    daemon: Any,
    client: _Client,
    msg: Message,
    text: str,
    chat: str,
    reason: str,
    ack_info: dict[str, Any],
) -> None:
    """Forward handoff text to plugin and log."""
    corr = f"handoff-{time.monotonic_ns():x}"
    forwarded = chat_send(text, submit=True, id=corr).encode()
    daemon._send(client, forwarded)
    daemon._last_chat_send_at = time.monotonic()
    ack_info["handoff"] = "sent"
    ack_info["chars"] = len(text)
    daemon._send(client, ack(msg.id or "session-event", info=ack_info).encode())
    daemon.log(f"handoff → plugin/{client.ide} ({len(text)} chars)")
    daemon.audit.record(
        "handoff",
        ide=client.ide,
        chat=chat,
        reason=reason or None,
        chars=len(text),
        ok=True,
    )


def handle_plugin_event(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle plugin event message (session.started, session.ended, message.sent, etc.)."""
    if msg.type == "session.started":
        start_new_log_session(
            session_id=msg.data.get("session_id"),
            name=msg.data.get("session_name") or msg.data.get("reason")
        )
    handoff = _handle_plugin_event_basic(daemon, client, msg)
    if handoff is None:
        return

    if not _check_handoff_cooldown(daemon, handoff.ack_info):
        daemon._send(client, ack(msg.id or "session-event", info=handoff.ack_info).encode())
        return

    text = _execute_handoff(
        daemon,
        client,
        msg,
        handoff.chat,
        handoff.reason,
        handoff.ack_info,
    )
    if text is None:
        return

    _forward_handoff_to_plugin(
        daemon,
        client,
        msg,
        text,
        handoff.chat,
        handoff.reason,
        handoff.ack_info,
    )
