"""Environment reporting for ``koru autonomous`` maintenance actions.

Owns the doctor/status/self-heal reporting responsibilities extracted from
the historical single-module facade: payload shaping, human-readable text
formatting, autopilot socket resolution and the action entry points used by
``koru.autonomous.autonomous_main``. The facade re-exports every public name
so existing ``koru.autonomous`` imports and monkeypatch targets keep working.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _socket_payload(socket: Any) -> dict[str, Any] | None:
    if socket is None:
        return None
    return {
        "path": str(socket.path),
        "exists": socket.exists,
        "listening": socket.listening,
        "stale": socket.stale,
        "healthy": socket.healthy,
    }


def _ide_presence_payload(ide: Any) -> dict[str, Any]:
    return {
        "ide": ide.ide,
        "installed": ide.installed,
        "binary_path": ide.binary_path,
        "mcp_config_path": str(ide.mcp_config_path) if ide.mcp_config_path else None,
        "mcp_has_koru": ide.mcp_has_koru,
    }


def _autonomous_report_payload(project: Path, report: Any, *, action: str) -> dict[str, Any]:
    return {
        "action": action,
        "project": str(project),
        "headless": report.headless,
        "installed_ides": report.installed_ides,
        "mcp_enabled_ides": report.mcp_enabled_ides,
        "ides": [_ide_presence_payload(ide) for ide in report.ides],
        "autopilot_socket": _socket_payload(report.autopilot_socket),
        "can_use_plugin_socket": report.can_use_plugin_socket,
        "can_use_mcp": report.can_use_mcp,
        "fixable_issues": list(report.fixable_issues),
        "notes": list(report.notes),
        "ready": bool(report.can_use_plugin_socket or report.can_use_mcp),
    }


def _format_autonomous_report_text(
    report: Any,
    *,
    action: str = "doctor",
) -> list[str]:
    installed = ", ".join(report.installed_ides) or "none"
    mcp_enabled = ", ".join(report.mcp_enabled_ides) or "none"
    socket = report.autopilot_socket
    if socket is None:
        socket_line = "autopilot socket: not configured"
    else:
        socket_line = (
            f"autopilot socket: {socket.path} exists={socket.exists} listening={socket.listening} stale={socket.stale}"
        )

    lines = [
        f"koru autonomous {action}",
        f"headless: {report.headless}",
        f"installed IDEs: {installed}",
        f"MCP enabled IDEs: {mcp_enabled}",
        socket_line,
        f"plugin socket usable: {report.can_use_plugin_socket}",
        f"MCP usable: {report.can_use_mcp}",
        f"ready: {bool(report.can_use_plugin_socket or report.can_use_mcp)}",
    ]
    for issue in report.fixable_issues:
        lines.append(f"fixable: {issue}")
    for note in report.notes:
        lines.append(f"note: {note}")
    return lines


def _resolve_autonomous_report_socket(explicit: Path | None, project: Path) -> Path:
    """Resolve autopilot socket for doctor/status/self-heal probes."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    from koru.autopilot.lane_context import resolve_client_socket_path

    return resolve_client_socket_path(
        argparse.Namespace(socket=None, ide="auto", project=project),
        project=project,
    )


def _print_autonomous_report(args: argparse.Namespace, *, action: str) -> int:
    from koru.autonomy.environment import probe_environment

    project = args.project.resolve()
    socket_path = _resolve_autonomous_report_socket(args.socket, project)
    report = probe_environment(project, autopilot_socket=socket_path)
    if args.format == "json":
        print(json.dumps(_autonomous_report_payload(project, report, action=action)))
        return 0
    for line in _format_autonomous_report_text(report, action=action):
        print(line)
    return 0


def _action_doctor(args: argparse.Namespace) -> int:
    return _print_autonomous_report(args, action="doctor")


def _action_status(args: argparse.Namespace) -> int:
    return _print_autonomous_report(args, action="status")


def _repair_payload(results: list[Any]) -> list[dict[str, str]]:
    return [
        {
            "action": result.action,
            "status": result.status,
            "detail": result.detail,
        }
        for result in results
    ]


def _action_self_heal(args: argparse.Namespace) -> int:
    from koru.autonomy.environment import probe_environment
    from koru.autonomy.heal import heal_environment, summarise

    project = args.project.resolve()
    socket_path = _resolve_autonomous_report_socket(args.socket, project)
    report = probe_environment(project, autopilot_socket=socket_path)
    results = heal_environment(report, dry_run=args.dry_run)
    failed = any(result.status == "failed" for result in results)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "action": "self-heal",
                    "project": str(project),
                    "dry_run": args.dry_run,
                    "summary": summarise(results),
                    "results": _repair_payload(results),
                    "ok": not failed,
                },
            ),
        )
        return 1 if failed else 0
    print(summarise(results))
    for result in results:
        detail = f": {result.detail}" if result.detail else ""
        print(f"{result.action}: {result.status}{detail}")
    return 1 if failed else 0
