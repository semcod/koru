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

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def _print_status_json(info: dict) -> None:
    """Print status info as formatted JSON."""
    print(json.dumps(info, indent=2, sort_keys=True))


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
    if not client.is_running():
        print(f"koru autopilot: daemon is NOT running on {client.socket_path}")
        print(f"hint: {daemon_start_hint_fn(args)}")
        return 1
    try:
        info = client.status()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot status: {exc}", file=sys.stderr)
        return 1

    _print_status_json(info)

    plugins = info.get("plugins") if isinstance(info, dict) else []
    if args.explain and isinstance(plugins, list) and not plugins:
        from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text
        from koruide.plugin_installer import resolve_target_ide

        instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
        ide = normalize_ide_fn(instance) if instance else resolve_target_ide("auto")
        ide = ide or "cursor"
        socket = getattr(client, "socket_path", None)
        if socket is not None:
            bridge = evaluate_bridge(
                ide=ide,
                socket_path=socket,
                project=getattr(args, "project", Path.cwd()),
                plugins=plugins,
            )
            print("\n--- explain ---", file=sys.stderr)
            print(format_bridge_text(bridge, explain=True), file=sys.stderr)
            print(f"hint: koru ide doctor --ide {ide} --fix", file=sys.stderr)
    return 0
