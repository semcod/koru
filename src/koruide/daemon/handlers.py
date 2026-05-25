from __future__ import annotations

import functools
import json
import os
import select
import socket
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.control_commands import plugin_socket_command
from koru.integration_ledger import record_integration_action
from koru.observability_events import (
    emit_action,
    emit_decision,
    emit_failure,
    emit_intent,
    emit_phase,
    emit_verify,
)
from koruide.daemon.protocol import (
    _Client,
    _daemon_package_version,
    _PluginEventHandoff,
)
from koruide.daemon.storage import (
    add_console_log,
    get_console_logs,
    start_new_log_session,
)
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import normalize_ide_id, pick_target, resolve_drive_target
from koruide.injector import InjectorError
from koruide.protocol import (
    MIN_PLUGIN_PROTOCOL_VERSION,
    Message,
    ack,
    chat_send,
    error,
)

_STATUS_CONSOLE_LOGS_LIMIT = 80

# STARTER-242: plugin ack ``info`` must fit one NDJSON line for the CLI client.
_MAX_RELAY_ACK_INFO_BYTES = 48 * 1024


def _cap_ack_info_for_cli(info: dict[str, Any]) -> dict[str, Any]:
    """Drop heavy optional ack fields before relaying to the CLI socket."""
    if not info:
        return info
    try:
        size = len(json.dumps(info, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
        return info
    if size <= _MAX_RELAY_ACK_INFO_BYTES:
        return info
    trimmed = dict(info)
    for key in ("diagnostics", "submit_attempts", "operation_trace"):
        trimmed.pop(key, None)
    try:
        size = len(json.dumps(trimmed, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
        trimmed["payload_trimmed"] = True
        return trimmed
    if size <= _MAX_RELAY_ACK_INFO_BYTES:
        trimmed["payload_trimmed"] = True
        return trimmed
    trimmed["payload_trimmed"] = True
    trimmed["operation_trace_dropped"] = True
    return trimmed


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


from koruide.daemon.handlers_drive import (
    _drive_via_keyboard,
    _drive_via_keyboard_backend,
    _drive_via_os_injector_backend,
    _drive_via_plugin,
    _prefer_keyboard_drive,
    _resolve_keyboard_drive_selection,
    _try_os_injector_drive,
    handle_drive,
)


def _plugin_rejection_log_interval_seconds() -> float:
    raw = os.environ.get("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", "").strip()
    if not raw:
        return 300.0
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 300.0


def _ide_reload_label(ide: str) -> str:
    labels = {
        "cursor": "Cursor",
        "vscode": "VS Code",
        "vscodium": "VSCodium",
        "windsurf": "Windsurf",
    }
    return labels.get(normalize_ide_id(ide) or ide, ide or "the IDE")


@functools.lru_cache(maxsize=1)
def _load_context_module() -> tuple[Callable[..., dict[str, Any]], Callable[[dict[str, Any]], str]]:
    """Import ``koru.context`` exactly once (R4)."""
    from koru.context import build_context, render_markdown_handoff

    return build_context, render_markdown_handoff


def _default_handoff(project: Path) -> Callable[[dict[str, Any]], str]:
    """Build the canonical koru brief for ``project`` on demand."""

    def _build(_event: dict[str, Any]) -> str:
        build_context, render_markdown_handoff = _load_context_module()
        try:
            ctx = build_context(project=project)
        except Exception as exc:  # pragma: no cover — defensive
            return f"koru autopilot: failed to build brief: {exc}"
        return render_markdown_handoff(ctx)

    return _build




# Hello handlers extracted to handlers_hello.py (R6)
# Re-exported for backward compatibility
from koruide.daemon.handlers_hello import (
    _configure_plugin_client,
    _extract_hello_metadata,
    _handle_plugin_version_check,
    _log_plugin_hello_accepted,
    _log_rejected_plugin_connection,
    handle_hello,
)



def handle_status(daemon: Any, client: _Client, msg: Message) -> None:
    if client.role == "unknown":
        client.role = "cli"
    plugins = [row.to_dict() for row in daemon._plugin_router.status_rows()]
    daemon_version = _daemon_package_version()
    info = {
        "socket": str(daemon.socket_path),
        "daemon_pid": os.getpid(),
        "daemon_version": daemon_version,
        "daemon": {
            "pid": os.getpid(),
            "version": daemon_version,
        },
        "plugins": plugins,
        "rejected_plugins": list(daemon._plugin_rejections),
        "console_logs": get_console_logs(limit=_STATUS_CONSOLE_LOGS_LIMIT),
        "backends": [b.to_dict() for b in daemon.injector.probe()],
        "selected_backend": daemon.injector.select_backend(),
        "ides": [i.to_dict() for i in detect_running_ides()],
    }
    daemon._send(client, ack(msg.id or "", info=info).encode())


def _cli_client_still_connected(daemon: Any, cli_client: _Client) -> bool:
    """Check if CLI client socket is still connected."""
    import select
    import socket

    fd = cli_client.sock.fileno()
    if fd < 0:
        return False
    if getattr(daemon, "_clients", {}).get(fd) is not cli_client:
        return False
    try:
        readable, _, _ = select.select([cli_client.sock], [], [], 0)
    except (OSError, ValueError):
        return False
    if not readable:
        return True
    flags = getattr(socket, "MSG_PEEK", 0) | getattr(socket, "MSG_DONTWAIT", 0)
    try:
        return bool(cli_client.sock.recv(1, flags))
    except BlockingIOError:
        return True
    except OSError:
        return False






# Ack handlers extracted to handlers_ack.py (R6)
# Re-exported for backward compatibility
from koruide.daemon.handlers_ack import (
    _annotated_plugin_ack_info,
    _plugin_ack_needs_os_fallback,
    _record_plugin_ack_integration,
    _relay_message_sent_ack,
    _relay_os_fallback_ack,
    _relay_plugin_ack_os_fallback,
    _send_plugin_ack_reply,
    _strict_plugin_ack_ok,
    handle_ack,
)


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
    return msg.type == "session.ended" and daemon.handoff is not None


def _ack_plugin_event_without_handoff(
    daemon: Any,
    client: _Client,
    msg: Message,
    ack_info: dict[str, Any],
) -> None:
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


def handle_shutdown(daemon: Any, client: _Client, msg: Message) -> None:
    if client.role == "unknown":
        client.role = "cli"
    daemon._send(client, ack(msg.id or "shutdown", info={"stopping": True}).encode())
    daemon.log(
        "shutdown requested via socket "
        f"role={client.role} ide={client.ide or '-'} "
        f"version={client.version or '-'} addr={client.addr}"
    )
    daemon.audit.record("shutdown", source="socket")
    daemon.stop()


def handle_ping(daemon: Any, client: _Client, msg: Message) -> None:
    if client.role == "unknown":
        client.role = "cli"
    else:
        daemon.log(f"ping from {client.addr} role={client.role}")
    daemon._send(client, ack(msg.id or "ping", info={"pong": True}).encode())


def handle_console_log(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle console log messages from the plugin for koru doctor."""
    message = msg.data.get("message") if isinstance(msg.data, dict) else None
    data = msg.data.get("data") if isinstance(msg.data, dict) else None
    timestamp = msg.data.get("timestamp") if isinstance(msg.data, dict) else None
    if isinstance(message, str) and isinstance(timestamp, str):
        entry_ide = msg.data.get("ide") if isinstance(msg.data, dict) else None
        entry_version = msg.data.get("version") if isinstance(msg.data, dict) else None
        add_console_log(
            message,
            data,
            timestamp,
            ide=str(entry_ide or client.ide or "").strip() or None,
            version=str(entry_version or client.version or "").strip() or None,
        )
        # Surface plugin-emitted DSL lines in the daemon log immediately
        # (i.e. *before* the drive ack arrives). This is what makes the
        # DSL "live": the operator sees each ladder candidate the
        # plugin tries while the drive is still in flight, not only in
        # the post-ack summary. Plugins emit these via
        # ``sendConsoleLog("[DSL-LIVE] ...")`` from ``traceOperation``;
        # see ``docs/koru-drive-dsl.md``.
        if message.startswith("[DSL-LIVE]"):
            ide_token = str(entry_ide or client.ide or "?").strip() or "?"
            daemon.log(f"[DSL] {message[len('[DSL-LIVE] '):]} via=plugin ide={ide_token}")
