"""``koru autopilot drive`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate drive logic
(daemon communication, fallback handling, direct injection) into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from koru.control_commands import shell_command

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def _drive_command_argv(args: argparse.Namespace, text: str) -> list[str]:
    """Build command argv for shell_command logging."""
    argv = ["koru", "autopilot", "drive", "--ide", str(args.ide)]
    if not args.submit:
        argv.append("--no-submit")
    if args.require_plugin:
        argv.append("--require-plugin")
    if getattr(args, "direct", False):
        argv.append("--direct")
    if args.prompt is not None:
        argv.extend(["--prompt", text])
    else:
        argv.append(text)
    return argv


def action_drive(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_start_hint_fn: callable,
    run_direct_drive_fn: callable,
    should_fallback_fn: callable,
) -> int:
    """Execute ``koru autopilot drive`` command.

    Args:
        args: Parsed command-line arguments
        client_fn: Factory for AutopilotClient (injected for testability)
        daemon_start_hint_fn: Function to generate daemon start hint message
        run_direct_drive_fn: Function to execute direct drive fallback
        should_fallback_fn: Function to check if fallback to direct drive is needed

    Returns:
        Exit code (0 success, 1 error, 2 usage error)
    """
    text = str(args.prompt).strip() if args.prompt is not None else " ".join(args.text).strip()
    if not text:
        print(
            "koru autopilot drive: missing text — pass words after `drive`, "
            "or use --prompt / -p '...'",
            file=sys.stderr,
        )
        return 2

    project = getattr(args, "project", None) or Path.cwd()
    shell_command(
        project,
        corr="cli-drive",
        argv=_drive_command_argv(args, text),
        cwd=str(project.resolve()),
        actor="operator",
        replayable=not args.dry_run,
    )

    if args.direct:
        rc, _payload = run_direct_drive_fn(args, text, emit_payload=True)
        return rc

    client: AutopilotClient = client_fn(args)
    if not client.is_running():
        print(
            "koru autopilot drive: daemon not running. "
            f"{daemon_start_hint_fn(args)}",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        print(f"[dry-run] would send {len(text)} chars to daemon ide={args.ide}")
        return 0

    try:
        reply = client.drive(
            text,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1

    if should_fallback_fn(args, reply):
        print(
            "koru autopilot drive: daemon could not open/focus chat input; "
            "falling back to local --direct injection",
            file=sys.stderr,
        )
        rc, direct_payload = run_direct_drive_fn(args, text, emit_payload=False)
        if direct_payload is None:
            print(json.dumps(reply, indent=2, sort_keys=True))
            return 1
        direct_payload = dict(direct_payload)
        direct_payload["daemon_fallback"] = {
            "ok": reply.get("ok"),
            "message": reply.get("message"),
            "opened": reply.get("opened"),
            "submitted": reply.get("submitted"),
        }
        print(json.dumps(direct_payload, indent=2, sort_keys=True))
        return rc

    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1
