from __future__ import annotations

import functools
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import pick_target, resolve_drive_target
from koruide.injector import InjectorError
from koruide.protocol import (
    MIN_PLUGIN_PROTOCOL_VERSION,
    Message,
    ack,
    chat_send,
    error,
)
from koruide.daemon.protocol import (
    _Client,
    _PluginEventHandoff,
    _daemon_package_version,
)
from koruide.daemon.storage import (
    add_console_log,
    get_console_logs,
    start_new_log_session,
)

_STATUS_CONSOLE_LOGS_LIMIT = 80


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _prefer_keyboard_drive() -> bool:
    return _env_truthy("KORU_AUTOPILOT_PREFER_KEYBOARD") or _env_truthy(
        "KORU_AUTOPILOT_VISIBLE_TYPING",
    )


def _plugin_rejection_log_interval_seconds() -> float:
    raw = os.environ.get("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", "").strip()
    if not raw:
        return 300.0
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 300.0


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


def handle_drive(daemon: Any, client: _Client, msg: Message) -> None:
    text = msg.data.get("text")
    if not isinstance(text, str) or not text:
        daemon._send(client, error(msg.id, "missing 'text'").encode())
        return
    raw_ide = msg.data.get("ide") if isinstance(msg.data.get("ide"), str) else None
    ide_pref = raw_ide if raw_ide not in (None, "auto") else None
    submit = bool(msg.data.get("submit", True))
    require_plugin = bool(msg.data.get("require_plugin", False))
    daemon.log(f"drive request: ide={raw_ide or 'auto'}, chars={len(text)}, submit={submit}, require_plugin={require_plugin}")
    plugin = daemon._plugin_for(ide_pref)
    if plugin is not None:
        daemon.log(f"drive: found plugin for ide={plugin.ide} (version={plugin.version}, protocol={plugin.protocol_version})")
    else:
        daemon.log(f"drive: no plugin found for ide={ide_pref}")
    if plugin is not None and not _prefer_keyboard_drive():
        daemon.log(f"drive: routing via plugin (ide={plugin.ide})")
        _drive_via_plugin(daemon, client, msg, plugin, text, submit, require_plugin)
        return
    if require_plugin:
        label = ide_pref or "auto"
        message = DriveOrchestrator.plugin_required_message(ide_pref)
        daemon._send(client, error(msg.id, message).encode())
        daemon.log(f"drive blocked: {message}")
        daemon.audit.record(
            "drive",
            ide=label,
            backend="plugin_required",
            chars=len(text),
            submit=submit,
            ok=False,
            error=message,
        )
        return
    daemon.log(f"drive: routing via keyboard/os_injector fallback")
    _drive_via_keyboard(daemon, client, msg, ide_pref, text, submit)


def _drive_via_plugin(
    daemon: Any,
    client: _Client,
    msg: Message,
    plugin: _Client,
    text: str,
    submit: bool,
    require_plugin: bool,
) -> None:
    """Forward a drive request to a connected plugin for that IDE."""
    daemon.log(f"drive_via_plugin: ide={plugin.ide}, version={plugin.version}, protocol={plugin.protocol_version}, capabilities={plugin.capabilities}")
    corr = msg.id or f"drive-{time.monotonic_ns():x}"
    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=plugin.ide,
        connected_version=plugin.version,
        protocol_version=plugin.protocol_version,
        capabilities=plugin.capabilities,
    )
    daemon.log(f"drive_via_plugin: version_info={version_info}")
    if version_info.get("plugin_version_mismatch"):
        summary = DriveOrchestrator.plugin_ack_summary(version_info)
        daemon.log(f"drive plugin version drift: {summary}")
        daemon.audit.record(
            "plugin_version_mismatch",
            ide=plugin.ide,
            plugin_version=version_info.get("plugin_version"),
            expected_plugin_version=version_info.get("expected_plugin_version"),
            policy=version_info.get("plugin_version_policy"),
        )
    if DriveOrchestrator.should_block_plugin_version(version_info):
        message = DriveOrchestrator.plugin_version_block_message(version_info)
        daemon._send(client, error(msg.id, message).encode())
        daemon.log(f"drive blocked: {message}")
        daemon.audit.record(
            "drive",
            ide=plugin.ide,
            backend="plugin",
            chars=len(text),
            submit=submit,
            ok=False,
            error=message,
            plugin_version=version_info.get("plugin_version"),
            expected_plugin_version=version_info.get("expected_plugin_version"),
        )
        return
    plugin.awaiting_plugin = (client, corr, submit, plugin.ide, text, require_plugin)
    daemon._send(plugin, chat_send(text, submit=submit, id=corr).encode())
    daemon._last_chat_send_at = time.monotonic()
    preview = text.replace("\n", " ")[:100]
    daemon.log(
        f"drive → plugin/{plugin.ide}: wklejam do czatu ({len(text)} zn, "
        f"submit={submit}) «{preview}»",
    )
    daemon.audit.record(
        "drive",
        ide=plugin.ide,
        backend="plugin",
        chars=len(text),
        submit=submit,
        ok=True,
    )


def _try_os_injector_drive(
    daemon: Any, target_id: str, text: str, submit: bool
) -> dict[str, Any] | None:
    """Run :mod:`os_injector` when configured; ``None`` means use keyboard."""
    daemon.log(f"try_os_injector_drive: target_id={target_id}, chars={len(text)}, submit={submit}")
    from koruide import os_injector as oi

    try:
        result = oi.try_drive_with_profile(
            tool_id=target_id,
            text=text,
            submit=submit,
            project=daemon.project,
            cli_dry_run=False,
            _log=daemon.log,
        )
        if result:
            daemon.log(
                f"try_os_injector_drive: SUCCESS backend={result.get('backend')}, "
                f"chat_coords=({result.get('chat_x')}, {result.get('chat_y')}), "
                f"input_method={result.get('input_method')}"
            )
        else:
            daemon.log(
                f"try_os_injector_drive: no profile for '{target_id}' — "
                f"uruchom: koru autopilot calibrate --ide {target_id}"
            )
        return result
    except oi.OsInjectorError as exc:
        daemon.log(f"try_os_injector_drive: FAILED: {exc}")
        raise InjectorError(str(exc)) from exc


def _drive_via_keyboard(
    daemon: Any,
    client: _Client,
    msg: Message,
    ide_pref: str | None,
    text: str,
    submit: bool,
) -> None:
    """Fallback: OS injector profile (X11) or :class:`Injector` keyboard sim."""
    ide_arg = ide_pref if ide_pref else "auto"
    daemon.log(f"drive_via_keyboard: ide_arg={ide_arg}, chars={len(text)}, submit={submit}")
    target_id, profile_id, selection = resolve_drive_target(
        ide_arg,
        None,
        project=daemon.project,
        _log=daemon.log,
    )
    daemon.log(f"drive_via_keyboard: resolved target_id={target_id}, profile_id={profile_id}, selection={selection}")
    if ide_arg == "auto":
        daemon.log(f"drive auto-selected {profile_id} ({selection})")
    preview = text.replace("\n", " ")[:100]
    target = pick_target(detect_running_ides(), prefer=ide_pref)
    try:
        # Call via the AutopilotDaemon instance method (which proxies back
        # to ``_try_os_injector_drive`` here) so tests can
        # ``monkeypatch.setattr(daemon, "_try_os_injector_drive", fake)``.
        os_res = daemon._try_os_injector_drive(profile_id, text, submit)
    except InjectorError as exc:
        os_res = None
        daemon.log(f"drive → os_injector/{profile_id} failed; trying keyboard fallback: {exc}")
    if os_res is not None:
        daemon.log(
            f"drive → os_injector/{profile_id}: klik ({os_res.get('chat_x')}, "
            f"{os_res.get('chat_y')}) + {os_res.get('input_method', 'type')} "
            f"«{preview}»",
        )
        info: dict[str, Any] = {
            "backend": str(os_res.get("backend", "os_injector")),
            "submitted": bool(os_res.get("submitted", submit)),
        }
        if os_res.get("dry_run"):
            info["dry_run"] = True
        tid = os_res.get("tool_id")
        if isinstance(tid, str):
            info["tool_id"] = tid
        if target is not None:
            info["ide"] = target.to_dict()
        daemon._send(client, ack(msg.id or "", info=info).encode())
        daemon.log(
            f"drive → {target_id} via {info['backend']}"
            f" ({len(text)} chars, submit={submit})",
        )
        daemon.audit.record(
            "drive",
            ide=target_id,
            backend=str(info["backend"]),
            chars=len(text),
            submit=submit,
            ok=True,
        )
        return

    backend = daemon.injector.select_backend()
    daemon.log(
        f"drive → keyboard/{target_id}: {backend or 'no-backend'} "
        f"({len(text)} zn) «{preview}»",
    )
    try:
        result = daemon.injector.type_text(text, ide=target_id, submit=submit)
    except InjectorError as exc:
        daemon._send(client, error(msg.id, str(exc)).encode())
        daemon.log(f"drive failed: {exc}")
        daemon.audit.record(
            "drive",
            ide=target_id,
            backend="keyboard",
            chars=len(text),
            submit=submit,
            ok=False,
            error=str(exc),
        )
        return
    info = {"backend": result.backend, "submitted": result.submitted}
    if target is not None:
        info["ide"] = target.to_dict()
    daemon._send(client, ack(msg.id or "", info=info).encode())
    daemon.log(f"drive → {target_id} via {result.backend} ({len(text)} chars, submit={submit})")
    daemon.audit.record(
        "drive",
        ide=target_id,
        backend=result.backend,
        chars=len(text),
        submit=submit,
        ok=True,
    )


def _extract_hello_metadata(msg: Message) -> tuple[str | None, str | None, int | None, list[str]]:
    """Extract and validate hello message metadata."""
    ide = msg.data.get("ide")
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
    daemon.log(f"status request from {client.addr} role={client.role}")
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
    daemon._send(cli_client, ack(corr, ok=True, info=info).encode())
    return True


def handle_ack(daemon: Any, client: _Client, msg: Message) -> None:
    pending = client.awaiting_plugin
    if pending is None:
        return
    cli_client, corr, submit_requested, plugin_ide, original_text, require_plugin = pending
    if msg.id != corr:
        return
    client.awaiting_plugin = None
    info = {k: v for k, v in msg.data.items() if k != "ok"}
    plugin_ok = bool(msg.data.get("ok", True))
    info = DriveOrchestrator.annotate_plugin_ack(
        info=info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
    )
    info.update(
        DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin_ide,
            connected_version=client.version,
            protocol_version=client.protocol_version,
            capabilities=client.capabilities,
        ),
    )
    if DriveOrchestrator.should_fail_strict_plugin_ack(
        info=info,
        plugin_ok=plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    ):
        plugin_ok = False
        info["message"] = (
            "strict plugin verification failed: expected full VS Code plugin "
            "ack with winning_focus_open / winning_paste / winning_submit"
        )
    if _plugin_ack_needs_os_fallback(
        plugin_ok=plugin_ok,
        info=info,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        require_plugin=require_plugin,
    ) and _relay_os_fallback_ack(
        daemon,
        cli_client,
        corr,
        plugin_ide,
        original_text,
        submit_requested,
        info,
    ):
        return
    if info.get("delivered") is True and "backend" not in info:
        info["backend"] = "plugin"
    daemon.log("drive → plugin ack: " + DriveOrchestrator.plugin_ack_summary(info))
    relay = ack(corr, ok=plugin_ok, info=info)
    daemon._send(cli_client, relay.encode())


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
    daemon.log(f"ping from {client.addr} role={client.role}")
    if client.role == "unknown":
        client.role = "cli"
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
