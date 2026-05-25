"""Operator and pre-check helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from koru import autonomous_plugin_runtime as _plugin_runtime
from koru.autonomous_plugin_lifecycle import (
    PluginLifecycleHooks,
    setup_autopilot_plugin_lifecycle,
)
from koru import autonomous_plugin_wait as _plugin_wait

_VSCODE_FAMILY_PLUGIN_IDES = _plugin_runtime.VSCODE_FAMILY_PLUGIN_IDES


def run_mcp_provision(
    project: Path,
    stdio_format: str,
    *,
    stdio_info: Any,
) -> bool:
    """Run MCP workspace provision and return True if it ran."""
    mcp_provision_ran = False
    try:
        from koru.mcp_provision import ensure_koru_mcp_not_disabled

        for row in ensure_koru_mcp_not_disabled(project):
            mcp_provision_ran = True
            stdio_info(
                f"koru autonomous: {row['action']} -> {row['path']}",
                fmt=stdio_format,
            )
    except (OSError, TypeError, ValueError) as exc:
        stdio_info(
            f"koru autonomous: mcp workspace refresh skipped ({exc})",
            fmt=stdio_format,
        )
    return mcp_provision_ran


def _ensure_trusted_publisher_for_plugin(
    autopilot_ide: str,
    *,
    stdio_info: Any,
    emit_fmt: str,
) -> None:
    _plugin_runtime.ensure_trusted_publisher_for_plugin(
        autopilot_ide,
        stdio_info=stdio_info,
        emit_fmt=emit_fmt,
    )


def _extension_active_in_latest_session(autopilot_ide: str) -> bool | None:
    return _plugin_runtime.extension_active_in_latest_session(autopilot_ide)


def _live_plugin_version(client: Any, autopilot_ide: str) -> str | None:
    return _plugin_runtime.live_plugin_version(client, autopilot_ide)


def _detect_stale_extension_host(
    autopilot_ide: str,
    client: Any,
) -> tuple[bool, str | None, str | None]:
    return _plugin_runtime.detect_stale_extension_host(
        autopilot_ide,
        client,
        live_version=_live_plugin_version,
    )


def _plugin_status_reason(client: Any, autopilot_ide: str) -> str:
    return _plugin_runtime.plugin_status_reason(client, autopilot_ide)


def _plugin_reason_requires_reload(reason: str) -> bool:
    return _plugin_runtime.plugin_reason_requires_reload(reason)


def _plugin_blocker_line(reason: str, autopilot_ide: str) -> str:
    return _plugin_runtime.plugin_blocker_line(reason, autopilot_ide)


def _reload_retry_wait_seconds(base_wait_seconds: float) -> float:
    return _plugin_runtime.reload_retry_wait_seconds(base_wait_seconds)


def _report_unsupported_plugin_result(
    autopilot_ide: str,
    *,
    emit_fmt: str,
    stdio_info: Any,
) -> bool:
    return _plugin_runtime.report_unsupported_plugin_result(
        autopilot_ide,
        emit_fmt=emit_fmt,
        stdio_info=stdio_info,
    )


def _emit_reload_required_lines(
    autopilot_ide: str,
    *,
    emit_fmt: str,
    stdio_info: Any,
) -> None:
    _plugin_runtime.emit_reload_required_lines(
        autopilot_ide,
        emit_fmt=emit_fmt,
        stdio_info=stdio_info,
    )


def _prepare_plugin_wait(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    *,
    project: Path | None,
    stdio_info: Any,
) -> tuple[bool, Any | None]:
    return _plugin_wait.prepare_plugin_wait(
        args,
        autopilot_ide,
        plugin_install_status,
        project=project,
        stdio_info=stdio_info,
        ensure_trusted_publisher=_ensure_trusted_publisher_for_plugin,
        extension_active=_extension_active_in_latest_session,
        emit_reload_lines=_emit_reload_required_lines,
    )


def _force_reload_if_extension_host_stale(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> None:
    _plugin_wait.force_reload_if_extension_host_stale(
        args,
        autopilot_ide,
        wait_seconds,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=stdio_info,
        detect_stale_extension_host=_detect_stale_extension_host,
        live_plugin_version=_live_plugin_version,
    )


def _retry_plugin_wait_after_reload(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool | None:
    return _plugin_wait.retry_plugin_wait_after_reload(
        args,
        autopilot_ide,
        wait_seconds,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=stdio_info,
        reload_retry_wait=_reload_retry_wait_seconds,
    )


def _wait_for_plugin_connection(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    reload_after_install: Any | None,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool:
    return _plugin_wait.wait_for_plugin_connection(
        args,
        autopilot_ide,
        plugin_install_status,
        reload_after_install,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=stdio_info,
        plugin_status_reason=_plugin_status_reason,
        plugin_blocker_line=_plugin_blocker_line,
        plugin_reason_requires_reload=_plugin_reason_requires_reload,
        force_reload_if_stale=_force_reload_if_extension_host_stale,
        retry_after_reload=_retry_plugin_wait_after_reload,
        emit_reload_lines=_emit_reload_required_lines,
    )


def setup_autopilot_plugin(
    args: Any,
    autopilot_ide: str,
    socket_path: Path | None,
    client: Any | None,
    *,
    project: Path | None = None,
    install_plugin_for_ide: Any,
    format_plugin_install_result: Any,
    allow_keyboard_fallback: Any,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool | None:
    """Install and wait for autopilot plugin if enabled."""
    return setup_autopilot_plugin_lifecycle(
        args,
        autopilot_ide,
        socket_path,
        client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        hooks=PluginLifecycleHooks(
            install_plugin_for_ide=install_plugin_for_ide,
            format_plugin_install_result=format_plugin_install_result,
            allow_keyboard_fallback=allow_keyboard_fallback,
            report_unsupported=_report_unsupported_plugin_result,
            prepare_plugin_wait=_prepare_plugin_wait,
            wait_for_plugin_connection=_wait_for_plugin_connection,
            stdio_info=stdio_info,
        ),
    )


def run_operator_pipeline(
    args: Any,
    project: Path,
    startup_probe: Any,
    plugin_connected: bool | None,
    mcp_provision_ran: bool,
    correlation_id: str,
    *,
    format_hints: Any,
    run_pipeline: Any,
    stdio_info: Any,
) -> None:
    """Run operator pipeline if enabled."""
    for hint in format_hints(startup_probe, plugin_connected=plugin_connected):
        stdio_info(hint, fmt=args.emit_events)

    if args.operator_pipeline:
        run_pipeline(
            project=project,
            probe=startup_probe,
            plugin_connected=plugin_connected,
            stdio_format=args.emit_events,
            create_tickets=args.operator_tickets,
            ticket_queue=args.operator_ticket_queue,
            ticket_priority=args.operator_ticket_priority,
            mcp_already_bootstrapped=mcp_provision_ran,
            correlation_id=correlation_id,
        )


def unblock_queue_if_needed(
    project: Path,
    stdio_format: str,
    *,
    release_in_progress_tickets: Any,
    runner: Any,
    stdio_info: Any,
) -> None:
    """Release in-progress tickets if KORU_QUEUE_UNBLOCK is set."""
    if os.environ.get("KORU_QUEUE_UNBLOCK", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    released = release_in_progress_tickets(project, runner=runner)
    if released:
        stdio_info(
            f"koru autonomous: queue unblock - reopened {released} in_progress ticket(s)",
            fmt=stdio_format,
        )


__all__ = [
    "run_mcp_provision",
    "setup_autopilot_plugin",
    "run_operator_pipeline",
    "unblock_queue_if_needed",
]
