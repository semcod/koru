"""``koru autopilot status`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate status query logic
into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from koru.autopilot.log_contract import emit_log

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def _print_status_json(info: dict) -> None:
    """Print status info as formatted JSON."""
    print(json.dumps(info, indent=2, sort_keys=True))


def _print_status_explain_summary(info: dict, socket_path: object) -> None:
    """Print a compact human summary for shell operators."""
    daemon = info.get("daemon") if isinstance(info.get("daemon"), dict) else {}
    plugins = _status_plugin_rows(info)
    plugin_labels = _status_plugin_labels(info)
    plugin_text = ", ".join(plugin_labels) if plugin_labels else "none"
    print("\n--- runtime ---", file=sys.stderr)
    print(
        "daemon: "
        f"pid={daemon.get('pid') or info.get('daemon_pid') or '-'} "
        f"version={daemon.get('version') or info.get('daemon_version') or '-'} "
        f"sha={daemon.get('git_sha') or '-'} "
        f"python={daemon.get('python_executable') or daemon.get('python') or '-'}",
        file=sys.stderr,
    )
    print(f"socket: {socket_path}", file=sys.stderr)
    print(f"plugins: {len(plugins)} ({plugin_text})", file=sys.stderr)


def _status_plugin_rows(info: dict) -> list[dict]:
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    return [row for row in plugins if isinstance(row, dict)]


def _status_plugin_labels(info: dict) -> list[str]:
    return [str(row.get("ide") or row.get("id") or "?") for row in _status_plugin_rows(info)]


def action_status(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_start_hint_fn: callable,
    normalize_ide_fn: callable,
    resolve_target_ide_fn: callable,
) -> int:
    """Execute ``koru autopilot status`` command.

    Args:
        args: Parsed command-line arguments
        client_fn: Factory for AutopilotClient
        daemon_start_hint_fn: Function to generate daemon start hint message
        normalize_ide_fn: Function to normalize IDE identifier
        resolve_target_ide_fn: Function to resolve target IDE

    Returns:
        Exit code (0 success, 1 error)
    """
    client: AutopilotClient = client_fn(args)
    emit_log(
        args,
        component="autopilot.status",
        level="info",
        action="request",
        result="started",
        ide=str(getattr(args, "ide", "auto")),
    )
    if not client.is_running():
        print(f"koru autopilot: daemon is NOT running on {client.socket_path}")
        print(f"hint: {daemon_start_hint_fn(args)}")
        if getattr(args, "explain", False):
            print(
                "explain: no daemon process answered on that socket. This is expected "
                "after Ctrl+C stopped `koru auto`; start `koru auto` again or run the "
                "hinted daemon command.",
                file=sys.stderr,
            )
        emit_log(
            args,
            component="autopilot.status",
            level="error",
            action="check_daemon",
            result="failed",
            rc=1,
            socket=str(getattr(client, "socket_path", "")),
        )
        return 1
    try:
        info = client.status()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot status: {exc}", file=sys.stderr)
        emit_log(
            args,
            component="autopilot.status",
            level="error",
            action="fetch_status",
            result="failed",
            rc=1,
            reason=str(exc),
        )
        return 1

    output_format = str(getattr(args, "format", "json") or "json")
    if output_format == "systemmap":
        from koru.ide_status_systemmap import format_autopilot_status_systemmap

        socket = str(getattr(client, "socket_path", "") or "")
        payload = format_autopilot_status_systemmap(info, socket_path=socket)
        print(json.dumps(payload, indent=2, sort_keys=True))
        plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
        if not plugins:
            instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
            hint = (
                f"hint: no IDE plugin on socket {socket}; "
                "systemmap has daemon/control surfaces only. "
                "Try KORU_AUTOPILOT_INSTANCE=cursor-main "
                "koru autopilot status --format systemmap "
                "or koru ide doctor --fix"
            )
            if instance:
                hint = (
                    f"hint: no IDE plugin on socket {socket} "
                    f"(KORU_AUTOPILOT_INSTANCE={instance!r}); "
                    f"run koru ide doctor --ide {_status_explain_target_ide(args, normalize_ide_fn)} --fix"
                )
            print(hint, file=sys.stderr)
        if args.explain and not payload.get("ok", True):
            print(f"systemmap export failed: {payload.get('error', '?')}", file=sys.stderr)
        emit_log(
            args,
            component="autopilot.status",
            level="info" if payload.get("ok", True) else "error",
            action="export_systemmap",
            result="ok" if payload.get("ok", True) else "failed",
            rc=0 if payload.get("ok", True) else 1,
            entry_count=len((payload.get("entries") or {})),
        )
        return 0 if payload.get("ok", True) else 1

    _print_status_json(info)
    if args.explain:
        _print_status_explain_summary(info, getattr(client, "socket_path", "-"))

    _maybe_print_empty_plugin_bridge_explain(args, info, client, normalize_ide_fn)
    plugins = info.get("plugins") if isinstance(info, dict) and isinstance(info.get("plugins"), list) else []
    emit_log(
        args,
        component="autopilot.status",
        level="info",
        action="request",
        result="ok",
        rc=0,
        socket=str(getattr(client, "socket_path", "")),
        plugin_count=len(plugins),
    )
    return 0


def _maybe_print_empty_plugin_bridge_explain(
    args: argparse.Namespace,
    info: dict,
    client: object,
    normalize_ide_fn: callable,
) -> None:
    plugins = info.get("plugins") if isinstance(info, dict) else []
    if not (args.explain and isinstance(plugins, list) and not plugins):
        return
    socket = getattr(client, "socket_path", None)
    if socket is None:
        return
    from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text

    ide = _status_explain_target_ide(args, normalize_ide_fn)
    bridge = evaluate_bridge(
        ide=ide,
        socket_path=socket,
        project=getattr(args, "project", Path.cwd()),
        plugins=plugins,
    )
    print("\n--- explain ---", file=sys.stderr)
    print(format_bridge_text(bridge, explain=True), file=sys.stderr)
    print(f"hint: koru ide doctor --ide {ide} --fix", file=sys.stderr)


def _status_explain_target_ide(args: argparse.Namespace, normalize_ide_fn: callable) -> str:
    from koruide.ide import canonical_autopilot_ide_id
    from koruide.plugin_installer import resolve_target_ide

    requested = normalize_ide_fn(getattr(args, "ide", "auto"))
    instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
    if requested and requested != "auto":
        return canonical_autopilot_ide_id(requested)
    if instance:
        return canonical_autopilot_ide_id(instance)
    return canonical_autopilot_ide_id(resolve_target_ide("auto") or "cursor")
