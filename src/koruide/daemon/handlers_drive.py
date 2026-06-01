"""Drive message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate drive-related
logic (plugin routing, OS injector, keyboard fallback) into a cohesive
module. The original module re-exports all symbols for backward
compatibility.
"""

from __future__ import annotations

import time
from typing import Any

from koru.control_commands import plugin_socket_command
from koru.integration_ledger import record_integration_action
from koru.observability_events import (
    emit_action,
    emit_decision,
    emit_intent,
    emit_phase,
)
from koruide.daemon.protocol import _Client
from koruide.command_catalog_store import command_picker_enabled
from koruide.command_picker import pick_command_order
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import normalize_ide_id, pick_target, resolve_drive_target
from koruide.injector import InjectorError
from koruide.protocol import Message, ack, chat_send, error


def _prefer_keyboard_drive() -> bool:
    """Check if keyboard drive is preferred over plugin."""
    from koruide.daemon.handlers import _env_truthy

    return _env_truthy("KORU_AUTOPILOT_PREFER_KEYBOARD") or _env_truthy(
        "KORU_AUTOPILOT_VISIBLE_TYPING",
    )


def handle_drive(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle a drive request from CLI client."""
    if client.role == "unknown":
        client.role = "cli"
    text = msg.data.get("text")
    if not isinstance(text, str) or not text:
        daemon._send(client, error(msg.id, "missing 'text'").encode())
        return
    raw_ide = msg.data.get("ide") if isinstance(msg.data.get("ide"), str) else None
    normalized_ide = normalize_ide_id(raw_ide)
    ide_pref = normalized_ide if normalized_ide not in (None, "auto") else None
    submit = bool(msg.data.get("submit", True))
    require_plugin = bool(msg.data.get("require_plugin", False))
    strategy_hint = msg.data.get("strategy_hint")
    if strategy_hint is not None and not isinstance(strategy_hint, str):
        strategy_hint = None
    daemon.log(
        "drive request: "
        f"ide={raw_ide or 'auto'}, chars={len(text)}, submit={submit}, "
        f"require_plugin={require_plugin}"
    )
    plugin = daemon._plugin_for(ide_pref)
    if plugin is not None:
        daemon.log(
            "drive: found plugin for "
            f"ide={plugin.ide} (version={plugin.version}, "
            f"protocol={plugin.protocol_version})"
        )
    else:
        daemon.log(f"drive: no plugin found for ide={ide_pref}")
    if plugin is not None and not _prefer_keyboard_drive():
        daemon.log(f"drive: routing via plugin (ide={plugin.ide})")
        _drive_via_plugin(
            daemon,
            client,
            msg,
            plugin,
            text,
            submit,
            require_plugin,
            strategy_hint=strategy_hint,
        )
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
    daemon.log("drive: routing via keyboard/os_injector fallback")
    _drive_via_keyboard(daemon, client, msg, ide_pref, text, submit)


def _check_and_block_plugin_version(
    daemon: Any,
    client: _Client,
    msg: Message,
    plugin: _Client,
    text: str,
    submit: bool,
) -> bool:
    """Check version info and policy block; returns True if blocked."""
    version_info = DriveOrchestrator.plugin_version_info(
        plugin_ide=plugin.ide,
        connected_version=plugin.version,
        connected_build_sha=plugin.build_sha,
        protocol_version=plugin.protocol_version,
        capabilities=plugin.capabilities,
    )
    daemon.log(f"drive_via_plugin: version_info={version_info}")
    if version_info.get("plugin_version_mismatch") or version_info.get("plugin_build_mismatch"):
        summary = DriveOrchestrator.plugin_ack_summary(version_info)
        daemon.log(f"drive plugin version drift: {summary}")
        daemon.audit.record(
            "plugin_version_mismatch",
            ide=plugin.ide,
            plugin_version=version_info.get("plugin_version"),
            expected_plugin_version=version_info.get("expected_plugin_version"),
            plugin_build_sha=version_info.get("plugin_build_sha"),
            expected_plugin_build_sha=version_info.get("expected_plugin_build_sha"),
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
            plugin_build_sha=version_info.get("plugin_build_sha"),
            expected_plugin_build_sha=version_info.get("expected_plugin_build_sha"),
        )
        return True
    return False


def _record_plugin_route_telemetry(
    daemon: Any,
    client: _Client,
    msg: Message,
    plugin: _Client,
    text: str,
    submit: bool,
    require_plugin: bool,
    corr: str,
) -> None:
    """Record routing decision, integration actions, and emit telemetry."""
    plugin.awaiting_plugin = (client, corr, submit, plugin.ide, text, require_plugin)
    daemon.log(
        "drive_via_plugin: route_decision "
        f"corr={corr} plugin_fd={plugin.sock.fileno()} cli_fd={client.sock.fileno()} "
        f"ide={plugin.ide} submit={submit} require_plugin={require_plugin} "
        "transport=plugin phases=focus_open,input_busy_probe,paste,submit",
    )
    emit_intent(
        daemon.project,
        corr=corr,
        goal="send_prompt",
        target="ide.chat",
        ide=plugin.ide,
        chars=len(text),
    )
    emit_decision(
        daemon.project,
        corr=corr,
        name="route_transport",
        chosen="plugin",
        because="plugin_connected",
        ide=plugin.ide,
        require_plugin=require_plugin,
        plugin_fd=plugin.sock.fileno(),
        cli_fd=client.sock.fileno(),
    )
    record_integration_action(
        project=daemon.project,
        action="drive.route",
        intent="deliver prompt to IDE chat and request submit",
        actor="autopilot-daemon",
        target=plugin.ide,
        transport="plugin-socket",
        phase="route",
        outcome="selected",
        evidence=(
            f"corr={corr}; plugin_fd={plugin.sock.fileno()}; cli_fd={client.sock.fileno()}; "
            f"submit={submit}; require_plugin={require_plugin}"
        ),
        next_step="send chat.send to plugin",
        data={
            "corr": corr,
            "plugin_fd": plugin.sock.fileno(),
            "cli_fd": client.sock.fileno(),
            "submit": submit,
            "require_plugin": require_plugin,
        },
    )
    emit_action(
        daemon.project,
        corr=corr,
        name="drive",
        chars=len(text),
        submit=submit,
        transport="plugin",
        ide=plugin.ide,
    )
    plugin_socket_command(
        daemon.project,
        corr=corr,
        message_type="chat.send",
        ide=plugin.ide,
        payload={
            "text": text,
            "text_len": len(text),
            "submit": submit,
            "require_plugin": require_plugin,
        },
        actor="autopilot-daemon",
        replayable=True,
    )


def _deliver_chat_via_plugin_socket(
    daemon: Any,
    plugin: _Client,
    text: str,
    submit: bool,
    corr: str,
    strategy_hint: str | None,
) -> None:
    """Deliver chat.send payload to plugin, logging and emitting confirmation telemetry."""
    command_order: dict[str, list[str]] | None = None
    if command_picker_enabled():
        catalog = (
            plugin.command_catalog
            or DriveOrchestrator.command_catalog_for(daemon._command_catalog_store, plugin.ide or "")
        )
        command_order = pick_command_order(
            ide=plugin.ide or "",
            plugin_version=plugin.version,
            catalog=catalog,
            telemetry=daemon._command_telemetry,
            recent_dsl=list(daemon._recent_dsl),
            strategy_hint=strategy_hint,
        )
        if command_order:
            daemon.log(
                "drive command_order: "
                + " ".join(f"{cap}={len(cmds)}" for cap, cmds in command_order.items()),
            )
    daemon._send(
        plugin,
        chat_send(
            text,
            submit=submit,
            id=corr,
            command_order=command_order,
            strategy_hint=strategy_hint,
        ).encode(),
    )
    daemon._last_chat_send_at = time.monotonic()
    preview = text.replace("\n", " ")[:100]
    daemon.log(
        f"drive → plugin/{plugin.ide}: wklejam do czatu ({len(text)} zn, "
        f"submit={submit}) «{preview}»",
    )
    for phase_name in ("focus_open", "input_busy_probe", "paste"):
        emit_phase(
            daemon.project,
            corr=corr,
            name=phase_name,
            status="attempted",
            ide=plugin.ide,
        )
    emit_phase(
        daemon.project,
        corr=corr,
        name="submit",
        status="awaiting_ack" if submit else "not_requested",
        ide=plugin.ide,
    )
    record_integration_action(
        project=daemon.project,
        action="chat.send",
        intent="paste prompt into current chat surface",
        actor="autopilot-daemon",
        target=plugin.ide,
        transport="plugin-socket",
        phase="paste+submit",
        outcome="requested",
        evidence=f"chars={len(text)}; submit={submit}; preview={preview}",
        next_step="await plugin ack with verification",
        data={"chars": len(text), "submit": submit, "corr": corr},
    )
    daemon.audit.record(
        "drive",
        ide=plugin.ide,
        backend="plugin",
        chars=len(text),
        submit=submit,
        ok=True,
    )


def _drive_via_plugin(
    daemon: Any,
    client: _Client,
    msg: Message,
    plugin: _Client,
    text: str,
    submit: bool,
    require_plugin: bool,
    *,
    strategy_hint: str | None = None,
) -> None:
    """Forward a drive request to a connected plugin for that IDE."""
    daemon.log(
        "drive_via_plugin: "
        f"ide={plugin.ide}, version={plugin.version}, build={getattr(plugin, 'build_sha', None) or '-'}, "
        f"protocol={plugin.protocol_version}, capabilities={plugin.capabilities}"
    )
    corr = msg.id or f"drive-{time.monotonic_ns():x}"

    if _check_and_block_plugin_version(daemon, client, msg, plugin, text, submit):
        return

    _record_plugin_route_telemetry(daemon, client, msg, plugin, text, submit, require_plugin, corr)
    _deliver_chat_via_plugin_socket(daemon, plugin, text, submit, corr, strategy_hint)


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
    target_id, profile_id, target, preview = _resolve_keyboard_drive_selection(
        daemon=daemon,
        ide_arg=ide_arg,
        ide_pref=ide_pref,
        text=text,
    )
    handled = _drive_via_os_injector_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id=target_id,
        profile_id=profile_id,
        text=text,
        submit=submit,
        preview=preview,
        target=target,
    )
    if handled:
        return

    _drive_via_keyboard_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        target_id=target_id,
        text=text,
        submit=submit,
        preview=preview,
        target=target,
    )


def _resolve_keyboard_drive_selection(
    *,
    daemon: Any,
    ide_arg: str,
    ide_pref: str | None,
    text: str,
) -> tuple[str, str, Any, str]:
    target_id, profile_id, selection = resolve_drive_target(
        ide_arg,
        None,
        project=daemon.project,
        _log=daemon.log,
    )
    daemon.log(
        "drive_via_keyboard: "
        f"resolved target_id={target_id}, profile_id={profile_id}, "
        f"selection={selection}"
    )
    if ide_arg == "auto":
        daemon.log(f"drive auto-selected {profile_id} ({selection})")
    preview = text.replace("\n", " ")[:100]
    target = pick_target(detect_running_ides(), prefer=ide_pref)
    return target_id, profile_id, target, preview


def _drive_via_os_injector_backend(
    *,
    daemon: Any,
    client: _Client,
    msg: Message,
    target_id: str,
    profile_id: str,
    text: str,
    submit: bool,
    preview: str,
    target: Any,
) -> bool:
    try:
        # Call via the AutopilotDaemon instance method (which proxies back
        # to ``_try_os_injector_drive`` here) so tests can
        # ``monkeypatch.setattr(daemon, "_try_os_injector_drive", fake)``.
        os_res = daemon._try_os_injector_drive(profile_id, text, submit)
    except InjectorError as exc:
        daemon.log(f"drive → os_injector/{profile_id} failed; trying keyboard fallback: {exc}")
        return False
    if os_res is None:
        return False
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
    return True


def _drive_via_keyboard_backend(
    *,
    daemon: Any,
    client: _Client,
    msg: Message,
    target_id: str,
    text: str,
    submit: bool,
    preview: str,
    target: Any,
) -> None:
    backend_name = daemon.injector.select_backend()
    daemon.log(
        f"drive → keyboard/{target_id}: {backend_name or 'no-backend'} "
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
