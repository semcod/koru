"""Compatibility shim: legacy import path for autopilot wire protocol.

Runtime code should gradually migrate to importing from :mod:`koruide.protocol`.
"""

from __future__ import annotations

from koruide.protocol import (
    ALL_TYPES,
    CLI_TO_DAEMON,
    DAEMON_TO_PLUGIN,
    MAX_LINE_BYTES,
    PLUGIN_TO_DAEMON,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    drive,
    error,
    hello,
    message_received,
    message_sent,
    session_ended,
    session_started,
    status_error,
)

__all__ = [
    "MAX_LINE_BYTES",
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
