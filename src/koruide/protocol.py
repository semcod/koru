"""Wire protocol for the `koruide` control socket.

Each message is one NDJSON envelope with a mandatory ``type`` and an
optional correlation ``id``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

MAX_LINE_BYTES = 1024 * 1024  # 1 MiB
PLUGIN_PROTOCOL_VERSION = 2
MIN_PLUGIN_PROTOCOL_VERSION = 1

PLUGIN_TO_DAEMON = frozenset(
    {
        "hello",
        "session.started",
        "session.ended",
        "message.sent",
        "message.received",
        "chat.opened",
        "status.error",
        "console_log",
        "ack",
        "error",
    },
)

DAEMON_TO_PLUGIN = frozenset(
    {
        "chat.send",
        "ping",
        "shutdown",
        "ack",
        "error",
    },
)

CLI_TO_DAEMON = frozenset(
    {
        "drive",
        "status",
        "shutdown",
        "ping",
    },
)

ALL_TYPES = PLUGIN_TO_DAEMON | DAEMON_TO_PLUGIN | CLI_TO_DAEMON

_FIELD_SCHEMA: dict[str, frozenset[str] | None] = {
    "hello": frozenset(
        {
            "ide",
            "version",
            "buildSha",
            "pid",
            "matchingCommands",
            "commandCatalog",
            "protocolVersion",
            "capabilities",
            "workspaceName",
            "workspaceFolders",
        }
    ),
    "session.started": frozenset({"chat"}),
    "session.ended": frozenset({"chat", "reason"}),
    "message.sent": frozenset({"chat", "text", "length"}),
    "message.received": frozenset({"chat", "text", "summary"}),
    "chat.opened": frozenset({"chat", "ok", "reason", "command", "message", "operation_trace"}),
    "status.error": frozenset({"message", "severity", "source"}),
    "console_log": frozenset({"message", "data", "timestamp", "ide", "version"}),
    "chat.send": frozenset({"text", "submit", "command_order", "strategy_hint"}),
    "drive": frozenset({"text", "submit", "ide", "require_plugin", "strategy_hint"}),
    "ping": frozenset(),
    "shutdown": frozenset(),
    "status": frozenset(),
    "ack": None,
    "error": None,
}


def _filter_extras(msg_type: str, obj: dict[str, Any]) -> dict[str, Any]:
    allowed = _FIELD_SCHEMA.get(msg_type, frozenset())
    if allowed is None:
        return {k: v for k, v in obj.items() if k not in ("type", "id")}
    return {k: v for k, v in obj.items() if k in allowed}


class ProtocolError(ValueError):
    """Raised when a line cannot be decoded into a valid message."""


@dataclass(frozen=True)
class Message:
    type: str
    id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type}
        if self.id is not None:
            payload["id"] = self.id
        for k, v in self.data.items():
            if k in ("type", "id"):
                continue
            payload[k] = v
        return payload

    def encode(self) -> bytes:
        return (json.dumps(self.to_dict(), separators=(",", ":")) + "\n").encode("utf-8")


def decode(line: bytes | str) -> Message:
    if isinstance(line, bytes):
        if len(line) > MAX_LINE_BYTES:
            raise ProtocolError(f"line too large: {len(line)} > {MAX_LINE_BYTES}")
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError(f"non-utf-8 line: {exc}") from exc
    else:
        text = line
    text = text.strip()
    if not text:
        raise ProtocolError("empty line")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid json: {exc}") from exc
    if not isinstance(obj, dict):
        raise ProtocolError("top-level value must be a JSON object")
    msg_type = obj.get("type")
    if not isinstance(msg_type, str) or not msg_type:
        raise ProtocolError("missing 'type' string field")
    if msg_type not in ALL_TYPES:
        raise ProtocolError(f"unknown message type: {msg_type!r}")
    msg_id = obj.get("id")
    if msg_id is not None and not isinstance(msg_id, str):
        raise ProtocolError("'id' must be a string when present")
    extras = _filter_extras(msg_type, obj)
    return Message(type=msg_type, id=msg_id, data=extras)


def hello(
    *,
    ide: str,
    version: str,
    pid: int,
    id: str | None = None,
    protocol_version: int | None = None,
    capabilities: list[str] | None = None,
    workspace_name: str | None = None,
    workspace_folders: list[str] | None = None,
    build_sha: str | None = None,
) -> Message:
    data: dict[str, Any] = {"ide": ide, "version": version, "pid": pid}
    if build_sha is not None:
        data["buildSha"] = build_sha
    if protocol_version is not None:
        data["protocolVersion"] = protocol_version
    if capabilities is not None:
        data["capabilities"] = capabilities
    if workspace_name is not None:
        data["workspaceName"] = workspace_name
    if workspace_folders is not None:
        data["workspaceFolders"] = workspace_folders
    return Message(type="hello", id=id, data=data)


def chat_send(
    text: str,
    *,
    submit: bool = True,
    id: str | None = None,
    command_order: dict[str, list[str]] | None = None,
    strategy_hint: str | None = None,
) -> Message:
    data: dict[str, Any] = {"text": text, "submit": submit}
    if command_order:
        data["command_order"] = command_order
    if strategy_hint:
        data["strategy_hint"] = strategy_hint
    return Message(type="chat.send", id=id, data=data)


def drive(
    text: str,
    *,
    submit: bool = True,
    ide: str = "auto",
    require_plugin: bool = False,
    strategy_hint: str | None = None,
    id: str | None = None,
) -> Message:
    data: dict[str, Any] = {
        "text": text,
        "submit": submit,
        "ide": ide,
        "require_plugin": require_plugin,
    }
    if strategy_hint:
        data["strategy_hint"] = strategy_hint
    return Message(type="drive", id=id, data=data)


def ack(reply_to: str, *, ok: bool = True, info: dict[str, Any] | None = None) -> Message:
    data: dict[str, Any] = {"ok": ok}
    if info:
        data.update(info)
    return Message(type="ack", id=reply_to, data=data)


def error(reply_to: str | None, message: str) -> Message:
    return Message(type="error", id=reply_to, data={"ok": False, "message": message})


def session_started(*, chat: str = "default", id: str | None = None) -> Message:
    return Message(type="session.started", id=id, data={"chat": chat})


def session_ended(*, chat: str = "default", reason: str = "", id: str | None = None) -> Message:
    return Message(type="session.ended", id=id, data={"chat": chat, "reason": reason})


def message_sent(
    *,
    chat: str = "default",
    text: str = "",
    length: int = 0,
    id: str | None = None,
) -> Message:
    return Message(
        type="message.sent",
        id=id,
        data={"chat": chat, "text": text, "length": length},
    )


def message_received(
    *,
    chat: str = "default",
    text: str = "",
    summary: str = "",
    id: str | None = None,
) -> Message:
    return Message(
        type="message.received",
        id=id,
        data={"chat": chat, "text": text, "summary": summary},
    )


def status_error(
    *,
    message: str = "",
    severity: str = "error",
    source: str = "",
    id: str | None = None,
) -> Message:
    return Message(
        type="status.error",
        id=id,
        data={"message": message, "severity": severity, "source": source},
    )


__all__ = [
    "MAX_LINE_BYTES",
    "PLUGIN_PROTOCOL_VERSION",
    "MIN_PLUGIN_PROTOCOL_VERSION",
    "PLUGIN_TO_DAEMON",
    "DAEMON_TO_PLUGIN",
    "CLI_TO_DAEMON",
    "ALL_TYPES",
    "ProtocolError",
    "Message",
    "decode",
    "hello",
    "chat_send",
    "drive",
    "ack",
    "error",
    "session_started",
    "session_ended",
    "message_sent",
    "message_received",
    "status_error",
]
