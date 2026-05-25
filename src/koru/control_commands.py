"""Replayable control-command DSL helpers.

Control commands describe *requested side effects* across Koru's control
surfaces: HTTP APIs, shell CLI, IDE/plugin sockets, and desktop GUI input.
They are intentionally separate from outcome events so a trace can answer:

1. what command was requested,
2. through which documented interface,
3. whether it can be replayed,
4. which later event verified or failed it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.observability_dsl import KoruObsEvent, parse_observability_dsl
from koru.observability_events import record_obs_event

CONTROL_COMMAND_DSL_VERSION = "koru.control.v1"


def control_command(
    *,
    corr: str,
    surface: str,
    interface_id: str,
    transport: str,
    operation: str,
    args: dict[str, Any] | None = None,
    component: str = "control",
    actor: str | None = None,
    target: str | None = None,
    replayable: bool = True,
    authority: str | None = None,
    verification: str | None = None,
) -> KoruObsEvent:
    """Build a formal, replayable control command event."""
    data: dict[str, Any] = {
        "command_version": CONTROL_COMMAND_DSL_VERSION,
        "surface": surface,
        "interface_id": interface_id,
        "transport": transport,
        "operation": operation,
        "args": args or {},
        "replayable": replayable,
    }
    if target:
        data["target"] = target
    if authority:
        data["authority"] = authority
    if verification:
        data["verification"] = verification
    return KoruObsEvent(
        corr=corr,
        component=component,
        kind="control.command",
        actor=actor,
        data=data,
    )


def emit_control_command(project: Path | None, command: KoruObsEvent) -> KoruObsEvent:
    record_obs_event(project, command)
    return command


def api_command(
    project: Path | None,
    *,
    corr: str,
    method: str,
    path: str,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    actor: str | None = "koru",
    interface_id: str = "dashboard_rest",
) -> KoruObsEvent:
    return emit_control_command(
        project,
        control_command(
            corr=corr,
            surface="api",
            interface_id=interface_id,
            transport="http_json",
            operation=f"{method.upper()} {path}",
            args={
                "query": query or {},
                "body": body or {},
                "headers": _scrub_headers(headers or {}),
            },
            actor=actor,
            authority="medium",
            verification="http_status",
        ),
    )


def shell_command(
    project: Path | None,
    *,
    corr: str,
    argv: list[str],
    cwd: str | None = None,
    actor: str | None = "operator",
    replayable: bool = True,
) -> KoruObsEvent:
    return emit_control_command(
        project,
        control_command(
            corr=corr,
            surface="shell_cli",
            interface_id="subprocess_local_tools",
            transport="subprocess",
            operation=argv[0] if argv else "",
            args={"argv": argv, "cwd": cwd or str((project or Path.cwd()).resolve())},
            actor=actor,
            replayable=replayable,
            authority="high",
            verification="exit_code_and_output",
        ),
    )


def plugin_socket_command(
    project: Path | None,
    *,
    corr: str,
    message_type: str,
    ide: str,
    payload: dict[str, Any] | None = None,
    actor: str | None = "autopilot-daemon",
    replayable: bool = True,
) -> KoruObsEvent:
    return emit_control_command(
        project,
        control_command(
            corr=corr,
            surface="ide_chat",
            interface_id="plugin_socket_vscode_family",
            transport="unix_socket_ndjson",
            operation=message_type,
            args=payload or {},
            actor=actor,
            target=ide,
            replayable=replayable,
            authority="high",
            verification="strict_ack",
        ),
    )


def desktop_gui_command(
    project: Path | None,
    *,
    corr: str,
    operation: str,
    backend: str,
    target: str = "focused_window",
    payload: dict[str, Any] | None = None,
    actor: str | None = "koru",
    replayable: bool = False,
) -> KoruObsEvent:
    return emit_control_command(
        project,
        control_command(
            corr=corr,
            surface="desktop_gui",
            interface_id=_desktop_interface_id(backend),
            transport=backend,
            operation=operation,
            args=payload or {},
            actor=actor,
            target=target,
            replayable=replayable,
            authority="low",
            verification="host_probe",
        ),
    )


def _desktop_interface_id(backend: str) -> str:
    key = backend.strip().lower()
    if "command_palette" in key or "command-palette" in key:
        return "ide_command_palette"
    if "xdotool" in key or "x11" in key:
        return "os_injector_xdotool"
    if "ydotool" in key or "uinput" in key:
        return "os_injector_ydotool"
    return "os_injector_wtype"


def parse_control_command_dsl(text: str) -> KoruObsEvent:
    event = parse_observability_dsl(text)
    _require_control_command(event)
    return event


def control_command_replay_plan(event: KoruObsEvent) -> dict[str, Any]:
    """Return a structured, non-executing replay plan for a control command."""
    _require_control_command(event)
    data = event.data
    args = dict(data.get("args") or {})
    surface = str(data.get("surface") or "")
    operation = str(data.get("operation") or "")
    plan: dict[str, Any] = {
        "corr": event.corr,
        "surface": surface,
        "interface_id": data.get("interface_id"),
        "transport": data.get("transport"),
        "operation": operation,
        "replayable": bool(data.get("replayable", False)),
    }
    if surface == "shell_cli":
        plan.update({"argv": list(args.get("argv") or []), "cwd": args.get("cwd")})
    elif surface == "api":
        method, path = _split_http_operation(operation)
        plan.update(
            {
                "method": method,
                "path": path,
                "query": dict(args.get("query") or {}),
                "body": dict(args.get("body") or {}),
                "headers": dict(args.get("headers") or {}),
            }
        )
    elif surface == "ide_chat":
        plan.update(
            {
                "message_type": operation,
                "ide": data.get("target"),
                "payload": args,
            }
        )
    elif surface == "desktop_gui":
        plan.update(
            {
                "backend": data.get("transport"),
                "target": data.get("target"),
                "payload": args,
            }
        )
    return plan


def _require_control_command(event: KoruObsEvent) -> None:
    if event.kind != "control.command":
        raise ValueError(f"expected control.command event, got {event.kind!r}")
    data = event.data
    required = ("surface", "interface_id", "transport", "operation", "args")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"control.command missing required fields: {', '.join(missing)}")


def _split_http_operation(operation: str) -> tuple[str, str]:
    if " " not in operation:
        return operation.upper(), ""
    method, path = operation.split(" ", 1)
    return method.upper(), path


def _scrub_headers(headers: dict[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in headers.items():
        lowered = str(key).lower()
        if any(token in lowered for token in ("authorization", "cookie", "token", "secret", "key")):
            scrubbed[str(key)] = "<redacted>"
        else:
            scrubbed[str(key)] = str(value)
    return scrubbed


__all__ = [
    "CONTROL_COMMAND_DSL_VERSION",
    "api_command",
    "control_command",
    "control_command_replay_plan",
    "desktop_gui_command",
    "emit_control_command",
    "parse_control_command_dsl",
    "plugin_socket_command",
    "shell_command",
]
