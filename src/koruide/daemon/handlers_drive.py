"""Drive message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate drive-related
logic (plugin routing, OS injector, keyboard fallback) into a cohesive
module. The original module re-exports all symbols for backward
compatibility.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from gillm.injection.errors import InjectorError

from koru.control_commands import plugin_socket_command
from koru.integration_ledger import record_integration_action
from koru.observability_events import (
    emit_action,
    emit_decision,
    emit_intent,
    emit_phase,
)
from koruide.command_catalog_store import command_picker_enabled
from koruide.command_picker import pick_command_order
from koruide.daemon.protocol import _Client
from koruide.drive_policy import DrivePolicy as DriveOrchestrator
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import normalize_ide_id, pick_target, resolve_drive_target
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
    if _drive_via_imgl_backend(
        daemon=daemon,
        client=client,
        msg=msg,
        ide_pref=ide_pref,
        text=text,
        submit=submit,
    ):
        return
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


def _pending_corr_owner_alive(pending_corr: str) -> bool:
    """Return False when a ``cli-drive-<pid>-…`` owner process is gone."""
    prefix = "cli-drive-"
    if not pending_corr.startswith(prefix):
        return True
    tail = pending_corr[len(prefix) :]
    pid_text, _, _hex = tail.partition("-")
    if not pid_text.isdigit():
        return True
    pid = int(pid_text)
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _clear_stale_pending_plugin_drive(plugin: _Client) -> None:
    timer = getattr(plugin, "awaiting_plugin_timer", None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass
    plugin.awaiting_plugin_timer = None
    plugin.awaiting_plugin_info = None
    plugin.awaiting_plugin = None


def _active_pending_plugin_drive(
    daemon: Any,
    plugin: _Client,
) -> tuple[Any, str, bool, str | None, str, bool] | None:
    pending = plugin.awaiting_plugin
    if pending is None:
        return None
    pending_cli, pending_corr, _submit, _plugin_ide, _text, _require_plugin = pending
    try:
        from koruide.daemon.handlers import _cli_client_still_connected

        connected = _cli_client_still_connected(daemon, pending_cli)
    except Exception:
        connected = True
    owner_alive = _pending_corr_owner_alive(pending_corr)
    if connected and owner_alive:
        return pending
    _clear_stale_pending_plugin_drive(plugin)
    if not owner_alive:
        daemon.log(
            "drive_via_plugin: cleared pending drive after CLI owner process exited "
            f"(corr={pending_corr})"
        )
    else:
        daemon.log(
            "drive_via_plugin: cleared stale pending drive before routing a new request"
        )
    return None


def _reject_overlapping_plugin_drive(
    daemon: Any,
    client: _Client,
    msg: Message,
    plugin: _Client,
    text: str,
    submit: bool,
    corr: str,
    pending: tuple[Any, str, bool, str | None, str, bool],
) -> None:
    (
        _pending_cli,
        pending_corr,
        pending_submit,
        pending_ide,
        pending_text,
        _pending_require,
    ) = pending
    pending_label = pending_ide or plugin.ide or "auto"
    message = (
        "plugin drive already in progress "
        f"(ide={pending_label}, corr={pending_corr}, submit={pending_submit}); "
        "wait for the current ACK or cancel that CLI before retrying"
    )
    info = {
        "backend": "plugin",
        "ok": False,
        "delivered": False,
        "opened": False,
        "submitted": False,
        "verification": "drive_in_progress",
        "message": message,
        "pending_corr": pending_corr,
        "pending_ide": pending_label,
        "pending_submit": pending_submit,
        "pending_chars": len(pending_text or ""),
    }
    daemon._send(client, ack(corr, ok=False, info=info).encode())
    daemon.log(f"drive_via_plugin: blocked overlapping drive: {message}")
    daemon.audit.record(
        "drive",
        ide=plugin.ide,
        backend="plugin",
        chars=len(text),
        submit=submit,
        ok=False,
        verification="drive_in_progress",
        corr=corr,
        pending_corr=pending_corr,
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
            or DriveOrchestrator.command_catalog_for(
                daemon._command_catalog_store,
                plugin.ide or "",
            )
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
        "drive_requested",
        ide=plugin.ide,
        backend="plugin",
        chars=len(text),
        submit=submit,
        status="awaiting_ack",
        corr=corr,
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
        f"ide={plugin.ide}, version={plugin.version}, "
        f"build={getattr(plugin, 'build_sha', None) or '-'}, "
        f"protocol={plugin.protocol_version}, capabilities={plugin.capabilities}"
    )
    corr = msg.id or f"drive-{time.monotonic_ns():x}"
    pending = _active_pending_plugin_drive(daemon, plugin)
    if pending is not None:
        _reject_overlapping_plugin_drive(
            daemon,
            client,
            msg,
            plugin,
            text,
            submit,
            corr,
            pending,
        )
        return

    if _check_and_block_plugin_version(daemon, client, msg, plugin, text, submit):
        return

    _record_plugin_route_telemetry(daemon, client, msg, plugin, text, submit, require_plugin, corr)
    _deliver_chat_via_plugin_socket(daemon, plugin, text, submit, corr, strategy_hint)


def _load_injector_config(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _coords_collision(data: dict[str, Any], target_id: str, x: int, y: int) -> str | None:
    for ide_id, raw in data.items():
        if ide_id == target_id or not isinstance(raw, dict):
            continue
        if raw.get("chat_x") == x and raw.get("chat_y") == y:
            return ide_id
    return None


def _calibration_collision(target_id: str, project: Path | None) -> str | None:
    """Return another IDE id whose calibrated chat coords match ``target_id``.

    A stale/cross-contaminated profile (e.g. ``windsurf`` copied from
    ``cursor``) makes the OS injector click the wrong window, which opens a
    new chat window instead of typing into the open one. Detect it from the
    same ``ide-os-injector.json`` that ``try_load_profile`` would use.
    """
    from gillm.injection import os_injector as oi

    target = oi.try_load_profile(target_id, project=project)
    if target is None:
        return None
    for path in oi.iter_config_paths(project=project):
        data = _load_injector_config(path)
        if data is None or target_id not in data:
            continue
        # try_load_profile resolves the first config file containing the
        # target; only that file is authoritative for this drive.
        return _coords_collision(data, target_id, target.chat_x, target.chat_y)
    return None


def _try_os_injector_drive(
    daemon: Any, target_id: str, text: str, submit: bool
) -> dict[str, Any] | None:
    """Run :mod:`gillm.injection.drive_backend` when configured; ``None`` → keyboard."""
    from gillm.injection.drive_backend import try_os_injector_drive as _try_os

    from koruide.daemon.handlers import _env_truthy

    daemon.log(f"try_os_injector_drive: target_id={target_id}, chars={len(text)}, submit={submit}")
    if not _env_truthy("KORU_OS_INJECTOR_ALLOW_DUP_CALIBRATION"):
        collision = _calibration_collision(target_id, daemon.project)
        if collision is not None:
            msg = (
                f"OS injector calibration for '{target_id}' duplicates '{collision}' "
                f"chat coordinates (stale profile); refusing to avoid driving the wrong "
                f"window. Recalibrate: koru autopilot calibrate --ide {target_id}"
            )
            daemon.log(f"try_os_injector_drive: REFUSED — {msg}")
            raise InjectorError(msg)
    try:
        result = _try_os(
            target_id,
            text,
            submit,
            project=daemon.project,
            _log=daemon.log,
        )
    except InjectorError as exc:
        daemon.log(f"try_os_injector_drive: FAILED: {exc}")
        raise
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


def _drive_via_imgl_backend(
    *,
    daemon: Any,
    client: _Client,
    msg: Message,
    ide_pref: str | None,
    text: str,
    submit: bool,
) -> bool:
    """Vision-guided chat drive via imgl (OCR + click/type) before blind keyboard."""
    from koru.integrations.imgl_client import imgl_prefer_before_keyboard, send_chat

    target_id = (ide_pref or "auto").strip().lower()
    if not imgl_prefer_before_keyboard(target_id):
        return False
    preview = text.replace("\n", " ")[:100]
    daemon.log(
        f"drive → imgl/{target_id}: vision-guided chat "
        f"({len(text)} zn) «{preview}» submit={submit}"
    )
    try:
        result = send_chat(text, ide=target_id, submit=submit)
    except Exception as exc:
        daemon.log(f"drive → imgl/{target_id} failed: {exc}; falling back to keyboard")
        return False
    if not result.get("ok"):
        daemon.log(
            f"drive → imgl/{target_id} declined: "
            f"{result.get('message') or result.get('error') or 'unknown'}; "
            "falling back to keyboard"
        )
        return False
    info = {
        "backend": "imgl",
        "submitted": bool(result.get("submitted", submit)),
        "verification": "vision",
        "tool_id": target_id,
    }
    if result.get("type_step"):
        info["type_step"] = result["type_step"]
    if result.get("key_step"):
        info["key_step"] = result["key_step"]
    daemon._send(client, ack(msg.id or "", info=info).encode())
    daemon.log(f"drive → {target_id} via imgl ({len(text)} chars, submit={submit})")
    daemon.audit.record(
        "drive",
        ide=target_id,
        backend="imgl",
        chars=len(text),
        submit=submit,
        ok=True,
    )
    return True


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
    from gillm.injection.drive_backend import format_os_injector_ack

    daemon.log(
        f"drive → os_injector/{profile_id}: klik ({os_res.get('chat_x')}, "
        f"{os_res.get('chat_y')}) + {os_res.get('input_method', 'type')} "
        f"«{preview}»",
    )
    target_dict = target.to_dict() if target is not None else None
    info = format_os_injector_ack(os_res, submit=submit, target=target_dict)
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
    from gillm.injection.drive_backend import apply_keyboard_injection

    try:
        result = apply_keyboard_injection(
            daemon.injector,
            text,
            target_id=target_id,
            submit=submit,
        )
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
