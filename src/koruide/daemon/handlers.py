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


from koru.env_flags import env_truthy as _env_truthy


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
    metadata = (
        daemon.daemon_metadata()
        if hasattr(daemon, "daemon_metadata")
        else {
            "pid": os.getpid(),
            "version": daemon_version,
            "socket": str(daemon.socket_path),
        }
    )
    info = {
        "socket": str(daemon.socket_path),
        "daemon_pid": os.getpid(),
        "daemon_version": daemon_version,
        "daemon": {
            "pid": os.getpid(),
            "version": daemon_version,
            "metadata_path": str(getattr(daemon, "metadata_path", "")),
            "git_sha": metadata.get("git_sha"),
            "python": metadata.get("python"),
            "python_executable": metadata.get("python_executable"),
            "started_at": metadata.get("started_at"),
            "uptime_seconds": metadata.get("uptime_seconds"),
            "project": metadata.get("project"),
        },
        "daemon_metadata": metadata,
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




# Plugin event handlers extracted to handlers_plugin_event.py (R6)
# Re-exported for backward compatibility
from koruide.daemon.handlers_plugin_event import (
    _PluginEventHandoff,
    _append_event,
    _check_handoff_cooldown,
    _event_path,
    _execute_handoff,
    _forward_handoff_to_plugin,
    _handle_plugin_event_basic,
    _plugin_event_should_handoff,
    _ack_plugin_event_without_handoff,
    handle_plugin_event,
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


def _console_log_payload(msg: Message) -> tuple[str, Any | None, str] | None:
    if not isinstance(msg.data, dict):
        return None
    message = msg.data.get("message")
    timestamp = msg.data.get("timestamp")
    if not isinstance(message, str) or not isinstance(timestamp, str):
        return None
    return message, msg.data.get("data"), timestamp


def _console_log_meta(client: _Client, msg: Message) -> tuple[str | None, str | None]:
    data = msg.data if isinstance(msg.data, dict) else {}
    entry_ide = data.get("ide")
    entry_version = data.get("version")
    ide = str(entry_ide or client.ide or "").strip() or None
    version = str(entry_version or client.version or "").strip() or None
    return ide, version


def _record_console_log(client: _Client, msg: Message) -> str | None:
    payload = _console_log_payload(msg)
    if payload is None:
        return None
    message, data, timestamp = payload
    ide, version = _console_log_meta(client, msg)
    add_console_log(message, data, timestamp, ide=ide, version=version)
    return message


def _live_dsl_log_line(message: str) -> str | None:
    prefix = "[DSL-LIVE]"
    if not message.startswith(prefix):
        return None
    return message[len(prefix):].strip()


def _log_live_dsl_console_line(daemon: Any, client: _Client, msg: Message, message: str) -> None:
    dsl_line = _live_dsl_log_line(message)
    if dsl_line is None:
        return
    data = msg.data if isinstance(msg.data, dict) else {}
    entry_ide = data.get("ide")
    ide_token = str(entry_ide or client.ide or "?").strip() or "?"
    daemon.log(f"[DSL] {dsl_line} via=plugin ide={ide_token}")


def handle_console_log(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle console log messages from the plugin for koru doctor."""
    message = _record_console_log(client, msg)
    if message is not None:
        # Surface plugin-emitted DSL lines in the daemon log immediately
        # (i.e. *before* the drive ack arrives). This is what makes the
        # DSL "live": the operator sees each ladder candidate the
        # plugin tries while the drive is still in flight, not only in
        # the post-ack summary. Plugins emit these via
        # ``sendConsoleLog("[DSL-LIVE] ...")`` from ``traceOperation``;
        # see ``docs/koru-drive-dsl.md``.
        _log_live_dsl_console_line(daemon, client, msg, message)
