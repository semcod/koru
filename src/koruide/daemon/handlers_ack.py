"""Ack message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate plugin acknowledgment
handling logic (fallback detection, OS injector fallback, message.sent relay,
DSL trace generation) into a cohesive module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from koruide.daemon.protocol import _Client, _daemon_package_version
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import normalize_ide_id
from koruide.injector import InjectorError
from koruide.protocol import Message, ack, MIN_PLUGIN_PROTOCOL_VERSION
from koru.integration_ledger import record_integration_action
from koru.observability_events import emit_failure, emit_verify


def _persist_recent_dsl(daemon: Any) -> None:
    project = getattr(daemon, "project", None)
    if project is None:
        return
    path = project / ".planfile" / ".koru" / "dsl_recent.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"lines": list(daemon._recent_dsl)}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return


def _plugin_ack_needs_os_fallback(
    plugin_ok: bool,
    info: dict[str, Any],
    submit_requested: bool,
    plugin_ide: str | None,
    require_plugin: bool,
) -> bool:
    """Check if plugin ack needs OS fallback."""
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
    """Relay OS fallback ack after plugin failure."""
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
    from koruide.daemon.handlers import _cli_client_still_connected

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
    """Attempt OS fallback for failed plugin ack."""
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
    """Send final plugin ack reply to CLI client with DSL trace."""
    from koruide.daemon.handlers import _cli_client_still_connected, _cap_ack_info_for_cli

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
    daemon._recent_dsl.extend(dsl_lines)
    daemon._recent_dsl.append(final_dsl_line)
    if len(daemon._recent_dsl) > 50:
        daemon._recent_dsl = daemon._recent_dsl[-50:]
    _persist_recent_dsl(daemon)
    daemon._command_telemetry.record_from_ack(
        ide=fallback_ide,
        plugin_version=info.get("plugin_version")
        if isinstance(info.get("plugin_version"), str)
        else None,
        info=info,
    )
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
    """Build annotated plugin ack info with version metadata."""
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
    """Apply strict plugin ack verification if enabled."""
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
    """Record plugin ack integration event."""
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


def handle_ack(daemon: Any, client: _Client, msg: Message) -> None:
    """Handle plugin acknowledgment message."""
    from koruide.daemon.handlers import _cli_client_still_connected

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
