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


def _extract_hello_metadata(msg: Message) -> tuple[str | None, str | None, int | None, list[str]]:
    """Extract and validate hello message metadata."""
    raw_ide = msg.data.get("ide")
    ide = normalize_ide_id(raw_ide) if isinstance(raw_ide, str) else raw_ide
    version = msg.data.get("version")
    plugin_version = version if isinstance(version, str) else None
    protocol_raw = msg.data.get("protocolVersion")
    protocol_version = protocol_raw if isinstance(protocol_raw, int) else None
    capabilities_raw = msg.data.get("capabilities")
    capabilities = (
        [item for item in capabilities_raw if isinstance(item, str)]
        if isinstance(capabilities_raw, list)
        else []
    )
    return ide, plugin_version, protocol_version, capabilities


def _handle_plugin_version_check(
    daemon: Any,
    client: _Client,
    msg: Message,
    ide: str,
    plugin_version: str | None,
    protocol_version: int | None,
    capabilities: list[str],
) -> bool:
    """Check plugin version and return True if accepted, False if rejected."""
    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=ide,
        connected_version=plugin_version,
        protocol_version=protocol_version,
        capabilities=capabilities,
    )
    if DriveOrchestrator.should_block_plugin_version(version_info):
        message = DriveOrchestrator.plugin_version_block_message(version_info)
        daemon._send(client, error(msg.id, message).encode())
        # Route via instance method so tests calling
        # ``daemon._log_rejected_plugin_connection(...)`` directly observe
        # the same code path and shared rejection state.
        daemon._log_rejected_plugin_connection(
            ide=ide,
            plugin_version=plugin_version,
            expected_plugin_version=version_info.get("expected_plugin_version"),
            message=message,
        )
        daemon.audit.record(
            "plugin_rejected",
            ide=ide,
            version=plugin_version,
            expected_plugin_version=version_info.get("expected_plugin_version"),
            error=message,
        )
        daemon._drop(client)
        return False
    return True


def _configure_plugin_client(
    daemon: Any,
    client: _Client,
    ide: str,
    plugin_version: str | None,
    protocol_version: int | None,
    capabilities: list[str],
) -> None:
    """Configure client as a plugin with provided metadata."""
    client.role = "plugin"
    client.ide = ide
    client.version = plugin_version
    client.protocol_version = protocol_version
    client.capabilities = capabilities
    daemon._plugin_router.drop_stale_plugins(client, ide)


def _log_plugin_hello_accepted(
    daemon: Any,
    ide: str,
    plugin_version: str | None,
    protocol_version: int | None,
    capabilities: list[str],
    version_info: dict[str, Any],
    matching_cmds: Any,
) -> None:
    """Log successful plugin hello acceptance."""
    command_count = len(matching_cmds) if isinstance(matching_cmds, list) else "-"
    daemon.log(
        "plugin hello accepted: "
        f"ide={ide} version={plugin_version or '-'} "
        f"expected={version_info.get('expected_plugin_version') or '-'} "
        f"policy={version_info.get('plugin_version_policy') or 'warn'} "
        f"protocol={protocol_version or '-'} min_protocol={MIN_PLUGIN_PROTOCOL_VERSION} "
        f"capabilities={len(capabilities)} matching_commands={command_count}",
    )


def handle_hello(daemon: Any, client: _Client, msg: Message) -> None:
    ide, plugin_version, protocol_version, capabilities = _extract_hello_metadata(msg)
    if not isinstance(ide, str) or not ide:
        daemon._send(client, error(msg.id, "hello requires 'ide'").encode())
        return

    if not _handle_plugin_version_check(
        daemon, client, msg, ide, plugin_version, protocol_version, capabilities
    ):
        return

    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=ide,
        connected_version=plugin_version,
        protocol_version=protocol_version,
        capabilities=capabilities,
    )

    _configure_plugin_client(daemon, client, ide, plugin_version, protocol_version, capabilities)
    matching_cmds = msg.data.get("matchingCommands")
    _log_plugin_hello_accepted(
        daemon, ide, plugin_version, protocol_version, capabilities, version_info, matching_cmds
    )
    daemon._send(client, ack(msg.id or "", info={"role": "plugin"}).encode())
    daemon.audit.record(
        "plugin_connected",
        ide=ide,
        version=plugin_version,
    )


def _log_rejected_plugin_connection(
    daemon: Any,
    *,
    ide: str,
    plugin_version: str | None,
    expected_plugin_version: Any,
    message: str,
) -> None:
    expected = expected_plugin_version if isinstance(expected_plugin_version, str) else None
    key = (ide, plugin_version, expected)
    now = time.monotonic()
    last, suppressed = daemon._plugin_rejection_log_state.get(key, (0.0, 0))
    if last and now - last < _plugin_rejection_log_interval_seconds():
        daemon._plugin_rejection_log_state[key] = (last, suppressed + 1)
        return
    suffix = f" (suppressed {suppressed} repeated reconnects)" if suppressed else ""
    daemon.log(f"rejecting plugin connection: ide={ide} {message}{suffix}")
    if expected and plugin_version and plugin_version != expected:
        ide_label = _ide_reload_label(ide)
        daemon.log(
            f"  → installed VSIX is v{plugin_version} but daemon expects "
            f"v{expected}. The IDE is still running the older plugin. "
            f"Action: in {ide_label} run `Developer: Reload Window` then "
            "`koru: Connect autopilot daemon` from the command palette. "
            "If still mismatched after reload, rebuild and reinstall the "
            "VSIX from plugins/koru-autopilot-vscode/.",
        )
    elif expected and not plugin_version:
        daemon.log(
            f"  → plugin sent no version; daemon expects v{expected}. "
            "This usually means the VSIX is older than the policy gate. "
            "Action: reinstall the VSIX from plugins/koru-autopilot-vscode/ "
            "and reload the IDE window.",
        )
    daemon._plugin_rejection_log_state[key] = (now, 0)
    daemon._plugin_rejections.append(
        {
            "ide": ide,
            "version": plugin_version,
            "expected_version": expected,
            "message": message,
            "suppressed": suppressed,
            "at": time.time(),
        }
    )
    if len(daemon._plugin_rejections) > 20:
        del daemon._plugin_rejections[:-20]


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


def _plugin_ack_needs_os_fallback(
    plugin_ok: bool,
    info: dict[str, Any],
    submit_requested: bool,
    plugin_ide: str | None,
    require_plugin: bool,
) -> bool:
    return DriveOrchestrator.should_try_os_fallback(
        plugin_ok=plugin_ok,
        info=info,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        require_plugin=require_plugin,
    )


def _relay_os_fallback_ack(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    plugin_ide: str,
    original_text: str,
    submit_requested: bool,
    info: dict[str, Any],
) -> bool:
    try:
        # Same instance-method indirection as in ``_drive_via_keyboard`` so
        # the OS-fallback path remains monkey-patchable in tests.
        os_res = daemon._try_os_injector_drive(plugin_ide, original_text, submit_requested)
    except InjectorError as exc:
        info["os_fallback"] = "failed"
        info["os_fallback_error"] = str(exc)
        return False
    if os_res is None:
        return False
    relay = ack(
        corr,
        ok=True,
        info={
            "backend": os_res.get("backend", "os_injector"),
            "ok": True,
            "delivered": True,
            "opened": True,
            "submitted": bool(os_res.get("submitted", submit_requested)),
            "os_fallback": "used",
        },
    )
    daemon._send(cli_client, relay.encode())
    return True


def _cli_client_still_connected(daemon: Any, cli_client: _Client) -> bool:
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


def _relay_message_sent_ack(daemon: Any, client: _Client, msg: Message) -> bool:
    """Use ``message.sent`` event as fallback completion for pending ``drive``."""
    pending = client.awaiting_plugin
    if pending is None:
        return False
    cli_client, corr, submit_requested, plugin_ide, _original_text, _require_plugin = pending
    if DriveOrchestrator.strict_plugin_ack_required():
        daemon.log(
            "drive → plugin event observed before strict ack; "
            "waiting for full plugin ack"
        )
        return False
    client.awaiting_plugin = None
    info = DriveOrchestrator.build_message_sent_info(
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        event_data=msg.data,
    )
    info.update(
        DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin_ide,
            connected_version=client.version,
            protocol_version=client.protocol_version,
            capabilities=client.capabilities,
        ),
    )
    daemon.log(
        "drive → plugin event completion: "
        + DriveOrchestrator.plugin_ack_summary(info)
    )
    if not _cli_client_still_connected(daemon, cli_client):
        daemon.log(
            "drive → plugin event completion arrived after CLI client disconnected; "
            "treating as late ack"
        )
        return True
    if not daemon._send(cli_client, ack(corr, ok=True, info=info).encode()):
        daemon.log(
            "drive → plugin event completion arrived after CLI client disconnected; "
            "treating as late ack"
        )
    return True


def handle_ack(daemon: Any, client: _Client, msg: Message) -> None:
    pending = client.awaiting_plugin
    if pending is None:
        return
    cli_client, corr, submit_requested, plugin_ide, original_text, require_plugin = pending
    if msg.id != corr:
        return
    client.awaiting_plugin = None
    plugin_ok = bool(msg.data.get("ok", True))
    info = _annotated_plugin_ack_info(
        client,
        msg,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    plugin_ok = _strict_plugin_ack_ok(
        info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    fallback_ide = plugin_ide or "auto"
    if _relay_plugin_ack_os_fallback(
        daemon,
        cli_client,
        corr,
        fallback_ide,
        original_text,
        info=info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        require_plugin=require_plugin,
    ):
        return
    _send_plugin_ack_reply(
        daemon,
        cli_client,
        corr,
        fallback_ide,
        info=info,
        plugin_ok=plugin_ok,
    )


def _relay_plugin_ack_os_fallback(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    fallback_ide: str,
    original_text: str,
    *,
    info: dict[str, Any],
    plugin_ok: bool,
    submit_requested: bool,
    plugin_ide: str | None,
    require_plugin: bool,
) -> bool:
    if not _plugin_ack_needs_os_fallback(
        plugin_ok=plugin_ok,
        info=info,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        require_plugin=require_plugin,
    ):
        return False
    return _relay_os_fallback_ack(
        daemon,
        cli_client,
        corr,
        fallback_ide,
        original_text,
        submit_requested,
        info,
    )


def _send_plugin_ack_reply(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    fallback_ide: str,
    *,
    info: dict[str, Any],
    plugin_ok: bool,
) -> None:
    if info.get("delivered") is True and "backend" not in info:
        info["backend"] = "plugin"
    summary = DriveOrchestrator.plugin_ack_summary(info)
    daemon.log("drive → plugin ack: " + summary)
    route_summary = DriveOrchestrator.operation_trace_summary(info)
    if route_summary:
        daemon.log(f"drive → plugin operation trace: {route_summary}")
    # Koru Drive DSL — one human-readable line per integration step.
    # This is the *transparent* trace the operator asked for: each line
    # carries act + intent + route + ok + reason, so a failed drive
    # ("plugin wkleil ale nie wyslal") explains itself instead of just
    # logging a single opaque "winning_submit=composer.sendToAgent".
    dsl_lines = DriveOrchestrator.operation_trace_dsl(info)
    for dsl_line in dsl_lines:
        daemon.log(f"[DSL] {dsl_line}")
    final_dsl_line = DriveOrchestrator.drive_outcome_dsl(info)
    daemon.log(f"[DSL] {final_dsl_line}")
    # Persist the DSL on the ack info so the CLI/autonomous receives it
    # in the relay envelope and can echo it verbatim instead of having
    # to ship its own renderer.
    if dsl_lines:
        info["drive_dsl"] = dsl_lines
    info["drive_dsl_outcome"] = final_dsl_line
    _record_plugin_ack_integration(
        daemon,
        corr=corr,
        target_ide=fallback_ide,
        info=info,
        plugin_ok=plugin_ok,
        summary=summary,
        route_summary=route_summary,
    )
    if not _cli_client_still_connected(daemon, cli_client):
        daemon.log(
            "drive → plugin ack arrived after CLI client disconnected; "
            "treating as late ack"
        )
        return
    relay = ack(corr, ok=plugin_ok, info=_cap_ack_info_for_cli(info))
    if not daemon._send(cli_client, relay.encode()):
        daemon.log(
            "drive → plugin ack arrived after CLI client disconnected; "
            "treating as late ack"
        )


def _annotated_plugin_ack_info(
    client: _Client,
    msg: Message,
    *,
    plugin_ok: bool,
    submit_requested: bool,
    plugin_ide: str | None,
) -> dict[str, Any]:
    info = {k: v for k, v in msg.data.items() if k != "ok"}
    info = DriveOrchestrator.annotate_plugin_ack(
        info=info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    info.update(
        DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin_ide,
            connected_version=client.version,
            protocol_version=client.protocol_version,
            capabilities=client.capabilities,
        ),
    )
    return info


def _strict_plugin_ack_ok(
    info: dict[str, Any],
    *,
    plugin_ok: bool,
    submit_requested: bool,
    plugin_ide: str | None,
) -> bool:
    if not DriveOrchestrator.should_fail_strict_plugin_ack(
        info=info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    ):
        return plugin_ok
    info["message"] = (
        "strict plugin verification failed: expected full VS Code plugin "
        "ack with winning_focus_open / winning_paste / winning_submit"
    )
    return False


def _record_plugin_ack_integration(
    daemon: Any,
    *,
    corr: str,
    target_ide: str,
    info: dict[str, Any],
    plugin_ok: bool,
    summary: str,
    route_summary: str,
) -> None:
    record_integration_action(
        project=daemon.project,
        action="plugin.ack",
        intent="verify whether paste and submit actually completed",
        actor="autopilot-daemon",
        target=target_ide,
        transport="plugin-socket",
        phase=str(info.get("verification") or "ack"),
        outcome="ok" if plugin_ok else "failed",
        reason=str(info.get("submit_failure_reason") or info.get("reason") or ""),
        evidence=summary + (f"; route={route_summary}" if route_summary else ""),
        next_step=(
            "continue queue"
            if plugin_ok
            else "stop retry for non-confirmed submit; inspect integration ledger"
        ),
        data={"ack": info, "route_trace": route_summary},
    )
    verification = str(info.get("verification") or "ack")
    if plugin_ok:
        emit_verify(
            daemon.project,
            corr=corr,
            name="submit" if "submit" in verification else "drive",
            status=verification,
            ide=target_ide,
            delivered=info.get("delivered"),
            submitted=info.get("submitted"),
            backend=info.get("backend"),
        )
        return
    emit_failure(
        daemon.project,
        corr=corr,
        code=str(info.get("submit_failure_reason") or info.get("reason") or verification),
        message=str(info.get("message") or summary),
        ide=target_ide,
        verification=verification,
        delivered=info.get("delivered"),
        submitted=info.get("submitted"),
        route=route_summary,
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
