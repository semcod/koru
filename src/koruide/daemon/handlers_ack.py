"""Ack message handlers for koruide daemon (R6).

Extracted from :mod:`koruide.daemon.handlers` to isolate plugin acknowledgment
handling logic (fallback detection, OS injector fallback, message.sent relay,
DSL trace generation) into a cohesive module.
"""

from __future__ import annotations

import json
import re
import shlex
import threading
from pathlib import Path
from typing import Any

from koruide.daemon.protocol import _Client, _daemon_package_version
from koruide.drive_policy import DrivePolicy as DriveOrchestrator
from koruide.ide import normalize_ide_id
from gillm.injection.errors import InjectorError
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


def _safe_replay_name(corr: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(corr or "drive")).strip(".-")
    return safe or "drive"


def _attach_drive_replay_commands(
    daemon: Any,
    info: dict[str, Any],
    *,
    corr: str,
    ide: str,
    original_text: str | None,
) -> None:
    """Persist enough context for a copy-paste replay/validation DSL line."""
    project_raw = getattr(daemon, "project", None)
    if project_raw is None:
        return
    project = Path(project_raw)
    if not original_text:
        return
    replay_dir = project / ".planfile" / ".koru" / "replay"
    prompt_path = replay_dir / f"{_safe_replay_name(corr)}.prompt"
    try:
        replay_dir.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(original_text, encoding="utf-8")
    except OSError as exc:
        info["replay_error"] = str(exc)
        return
    info["replay_artifact"] = str(prompt_path)
    info["replay_command"] = (
        f"KORU_AUTOPILOT_INSTANCE={shlex.quote(ide)} "
        f"koru autopilot drive --ide {shlex.quote(ide)} "
        f"--require-plugin --prompt-file {shlex.quote(str(prompt_path))}"
    )
    info["validate_command"] = (
        "koru autopilot trace "
        f"--project {shlex.quote(str(project))} --format drive-dsl --limit 30"
    )


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


def _strict_message_sent_completion_allowed(
    daemon: Any,
    client: _Client,
    plugin_ide: str | None,
) -> bool:
    if not DriveOrchestrator.strict_plugin_ack_required():
        return True
    pending_info = getattr(client, "awaiting_plugin_info", None)
    ide = str(plugin_ide or (pending_info or {}).get("ide") or "").lower()
    strict_deferred = (
        isinstance(pending_info, dict)
        and str(pending_info.get("verification") or "").lower() == "submit_unverified"
        and ide in {"vscodium", "cursor"}
    )
    if strict_deferred:
        if _pending_info_has_poisoned_late_message_sent(pending_info, ide):
            daemon.log(
                "drive → late message.sent ignored for poisoned submit_unverified "
                f"trace ide={ide}"
            )
            return False
        daemon.log(f"drive → strict ack accepted late message.sent fallback for {ide}")
        return True
    daemon.log(
        "drive → plugin event observed before strict ack; "
        "waiting for full plugin ack"
    )
    return False


def _pending_info_has_poisoned_late_message_sent(info: dict[str, Any], ide: str) -> bool:
    if ide != "vscodium":
        return False
    if str(info.get("attempted_submit") or info.get("winning_submit") or "") != (
        "workbench.action.chat.submit"
    ):
        return False
    trace = info.get("operation_trace")
    if not isinstance(trace, list):
        return False
    for step in trace:
        if not isinstance(step, dict) or step.get("op") != "submit_verify":
            continue
        detail = step.get("detail")
        detail = detail if isinstance(detail, dict) else {}
        if detail.get("observedLength") == -1:
            return True
        if detail.get("requireEmptyAfterSubmit") is not True:
            return True
    return False


def _clear_pending_plugin_drive(client: _Client) -> None:
    timer = getattr(client, "awaiting_plugin_timer", None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass
    client.awaiting_plugin_timer = None
    client.awaiting_plugin_info = None
    client.awaiting_plugin = None


def _message_sent_completion_info(
    client: _Client,
    msg: Message,
    *,
    submit_requested: bool,
    plugin_ide: str | None,
) -> dict[str, Any]:
    info = DriveOrchestrator.build_message_sent_info(
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
        event_data=msg.data,
    )
    info.update(
        DriveOrchestrator.drive_intent_evidence(
            info,
            plugin_ok=True,
            submit_requested=submit_requested,
            plugin_ide=plugin_ide,
        ),
    )
    info.update(
        DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin_ide,
            connected_version=client.version,
            connected_build_sha=client.build_sha if isinstance(client.build_sha, str) else None,
            protocol_version=client.protocol_version,
            capabilities=client.capabilities,
        ),
    )
    return info


def _send_message_sent_completion(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    info: dict[str, Any],
) -> None:
    from koruide.daemon.handlers import _cli_client_still_connected

    if not _cli_client_still_connected(daemon, cli_client):
        daemon.log(
            "drive → plugin event completion arrived after CLI client disconnected; "
            "treating as late ack"
        )
        return
    if not daemon._send(cli_client, ack(corr, ok=True, info=info).encode()):
        daemon.log(
            "drive → plugin event completion arrived after CLI client disconnected; "
            "treating as late ack"
        )


def _relay_message_sent_ack(daemon: Any, client: _Client, msg: Message) -> bool:
    """Use ``message.sent`` event as fallback completion for pending ``drive``."""
    pending = client.awaiting_plugin
    if pending is None:
        return False
    cli_client, corr, submit_requested, plugin_ide, _original_text, _require_plugin = pending
    if not _strict_message_sent_completion_allowed(daemon, client, plugin_ide):
        return False
    _clear_pending_plugin_drive(client)
    info = _message_sent_completion_info(
        client,
        msg,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    daemon.log(
        "drive → plugin event completion: "
        + DriveOrchestrator.plugin_ack_summary(info)
    )
    _send_message_sent_completion(daemon, cli_client, corr, info)
    return True


def _deferred_submit_unverified_grace_seconds() -> float:
    # Cursor/VSCodium may emit message.sent shortly after submit verification
    # reports submit_unverified. Keep a short grace window before final failure.
    return 2.0


def _defer_submit_unverified_reply(
    daemon: Any,
    client: _Client,
    cli_client: _Client,
    corr: str,
    fallback_ide: str,
    *,
    info: dict[str, Any],
    plugin_ok: bool,
    original_text: str | None,
) -> None:
    """Wait briefly for a late ``message.sent`` event before finalizing failure."""

    def _finalize() -> None:
        pending = client.awaiting_plugin
        if pending is None:
            return
        pending_cli, pending_corr, _submit_requested, _plugin_ide, _text, _require_plugin = pending
        if pending_cli is not cli_client or pending_corr != corr:
            return
        deferred_info = getattr(client, "awaiting_plugin_info", None)
        if not isinstance(deferred_info, dict):
            return
        client.awaiting_plugin = None
        client.awaiting_plugin_info = None
        client.awaiting_plugin_timer = None
        _send_plugin_ack_reply(
            daemon,
            cli_client,
            corr,
            fallback_ide,
            info=deferred_info,
            plugin_ok=plugin_ok,
            original_text=original_text,
        )

    client.awaiting_plugin_info = dict(info)
    timer = threading.Timer(_deferred_submit_unverified_grace_seconds(), _finalize)
    timer.daemon = True
    client.awaiting_plugin_timer = timer
    timer.start()
    daemon.log(
        "drive → deferring submit_unverified reply briefly; "
        "waiting for late message.sent event"
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


def _ensure_plugin_backend(info: dict[str, Any]) -> None:
    if info.get("delivered") is True and "backend" not in info:
        info["backend"] = "plugin"


def _log_plugin_ack_trace(
    daemon: Any,
    info: dict[str, Any],
    *,
    plugin_ok: bool,
) -> tuple[str, str, list[str], str, list[str]]:
    summary = DriveOrchestrator.plugin_ack_summary(info)
    daemon.log("drive → plugin ack: " + summary)
    route_summary = DriveOrchestrator.operation_trace_summary(info)
    if route_summary:
        daemon.log(f"drive → plugin operation trace: {route_summary}")

    dsl_lines = DriveOrchestrator.operation_trace_dsl(info)
    validation_dsl_lines = DriveOrchestrator.drive_validation_dsl(info)
    final_dsl_line = DriveOrchestrator.drive_outcome_dsl(info)
    operator_dsl_lines = DriveOrchestrator.drive_operator_dsl(info, plugin_ok=plugin_ok)
    for dsl_line in [*dsl_lines, *validation_dsl_lines, final_dsl_line, *operator_dsl_lines]:
        daemon.log(f"[DSL] {dsl_line}")
    return summary, route_summary, dsl_lines + validation_dsl_lines, final_dsl_line, operator_dsl_lines


def _persist_plugin_ack_dsl(
    daemon: Any,
    info: dict[str, Any],
    *,
    dsl_lines: list[str],
    final_dsl_line: str,
    operator_dsl_lines: list[str],
) -> None:
    daemon._recent_dsl.extend(dsl_lines)
    daemon._recent_dsl.append(final_dsl_line)
    daemon._recent_dsl.extend(operator_dsl_lines)
    if len(daemon._recent_dsl) > 50:
        daemon._recent_dsl = daemon._recent_dsl[-50:]
    _persist_recent_dsl(daemon)
    if dsl_lines:
        info["drive_dsl"] = dsl_lines
    info["drive_dsl_outcome"] = final_dsl_line
    info["drive_dsl_operator"] = operator_dsl_lines


def _record_plugin_ack_command_telemetry(
    daemon: Any,
    fallback_ide: str,
    info: dict[str, Any],
) -> None:
    daemon._command_telemetry.record_from_ack(
        ide=fallback_ide,
        plugin_version=info.get("plugin_version")
        if isinstance(info.get("plugin_version"), str)
        else None,
        info=info,
    )


def _relay_plugin_ack_to_cli(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    *,
    info: dict[str, Any],
    plugin_ok: bool,
) -> None:
    from koruide.daemon.handlers import _cli_client_still_connected, _cap_ack_info_for_cli

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


def _send_plugin_ack_reply(
    daemon: Any,
    cli_client: _Client,
    corr: str,
    fallback_ide: str,
    *,
    info: dict[str, Any],
    plugin_ok: bool,
    original_text: str | None = None,
) -> None:
    """Send final plugin ack reply to CLI client with DSL trace."""
    _attach_drive_replay_commands(
        daemon,
        info,
        corr=corr,
        ide=fallback_ide,
        original_text=original_text,
    )
    _ensure_plugin_backend(info)
    summary, route_summary, dsl_lines, final_dsl_line, operator_dsl_lines = _log_plugin_ack_trace(
        daemon,
        info,
        plugin_ok=plugin_ok,
    )
    _persist_plugin_ack_dsl(
        daemon,
        info,
        dsl_lines=dsl_lines,
        final_dsl_line=final_dsl_line,
        operator_dsl_lines=operator_dsl_lines,
    )
    _record_plugin_ack_command_telemetry(daemon, fallback_ide, info)
    _record_plugin_ack_integration(
        daemon,
        corr=corr,
        target_ide=fallback_ide,
        info=info,
        plugin_ok=plugin_ok,
        summary=summary,
        route_summary=route_summary,
    )
    daemon.audit.record(
        "drive",
        ide=fallback_ide,
        backend=info.get("backend", "plugin"),
        chars=len(original_text or ""),
        submit=bool(info.get("submitted")) or bool(info.get("attempted_submit")),
        ok=plugin_ok,
        verification=info.get("verification"),
        delivered=info.get("delivered"),
        submitted=info.get("submitted"),
        corr=corr,
    )
    _relay_plugin_ack_to_cli(
        daemon,
        cli_client,
        corr,
        info=info,
        plugin_ok=plugin_ok,
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
            connected_build_sha=client.build_sha if isinstance(client.build_sha, str) else None,
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
    raw_plugin_ok = bool(msg.data.get("ok", True))
    info = _annotated_plugin_ack_info(
        client,
        msg,
        plugin_ok=raw_plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    fallback_ide = plugin_ide or "auto"
    if DriveOrchestrator.should_defer_submit_unverified_for_message_sent(
        info=info,
        plugin_ok=raw_plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    ):
        _defer_submit_unverified_reply(
            daemon,
            client,
            cli_client,
            corr,
            fallback_ide,
            info=info,
            plugin_ok=False,
            original_text=original_text,
        )
        return
    plugin_ok = _strict_plugin_ack_ok(
        info,
        plugin_ok=raw_plugin_ok,
        submit_requested=submit_requested,
        plugin_ide=plugin_ide,
    )
    client.awaiting_plugin = None
    client.awaiting_plugin_info = None
    client.awaiting_plugin_timer = None
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
        original_text=original_text,
    )
