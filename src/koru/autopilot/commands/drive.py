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


def _drive_text_from_args(args: argparse.Namespace) -> tuple[str | None, int]:
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file is not None:
        try:
            return Path(prompt_file).read_text(encoding="utf-8"), 0
        except OSError as exc:
            print(
                f"koru autopilot drive: cannot read --prompt-file {prompt_file}: {exc}",
                file=sys.stderr,
            )
            return None, 2
    text = str(args.prompt).strip() if args.prompt is not None else " ".join(args.text).strip()
    if text.strip():
        return text, 0
    print(
        "koru autopilot drive: missing text — pass words after `drive`, "
        "or use --prompt / -p '...'",
        file=sys.stderr,
    )
    return None, 2


def _drive_command_argv(args: argparse.Namespace, text: str) -> list[str]:
    """Build command argv for shell_command logging."""
    drive_argv = ["koru", "autopilot", "drive", "--ide", str(args.ide)]
    if not args.submit:
        drive_argv.append("--no-submit")
    if args.require_plugin:
        drive_argv.append("--require-plugin")
    if getattr(args, "direct", False):
        drive_argv.append("--direct")
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file is not None:
        drive_argv.extend(["--prompt-file", str(prompt_file)])
        return drive_argv
    if args.prompt is not None:
        drive_argv.extend(["--prompt", text])
    else:
        drive_argv.append(text)
    return drive_argv


def _record_drive_command(args: argparse.Namespace, text: str) -> Path:
    project = getattr(args, "project", None) or Path.cwd()
    shell_command(
        project,
        corr="cli-drive",
        argv=_drive_command_argv(args, text),
        cwd=str(project.resolve()),
        actor="operator",
        replayable=not args.dry_run,
    )
    return project


def _connect_drive_client(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_start_hint_fn: callable,
) -> tuple["AutopilotClient | None", int]:
    client: AutopilotClient = client_fn(args)
    if client.is_running():
        return client, 0
    print(
        "koru autopilot drive: daemon not running. "
        f"{daemon_start_hint_fn(args)}",
        file=sys.stderr,
    )
    return None, 2


def _drive_daemon(client: "AutopilotClient", args: argparse.Namespace, text: str) -> tuple[dict, int]:
    try:
        reply = client.drive(
            text,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return {}, 1
    return reply, -1


def _run_direct_fallback(
    args: argparse.Namespace,
    text: str,
    reply: dict,
    *,
    run_direct_drive_fn: callable,
) -> int:
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


def _finish_drive_reply(
    args: argparse.Namespace,
    text: str,
    reply: dict,
    *,
    run_direct_drive_fn: callable,
    should_fallback_fn: callable,
) -> int:
    if should_fallback_fn(args, reply):
        return _run_direct_fallback(
            args,
            text,
            reply,
            run_direct_drive_fn=run_direct_drive_fn,
        )
    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


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
    text, rc = _drive_text_from_args(args)
    if text is None:
        return rc
    _record_drive_command(args, text)

    if args.direct:
        rc, _payload = run_direct_drive_fn(args, text, emit_payload=True)
        return rc

    client, rc = _connect_drive_client(
        args,
        client_fn=client_fn,
        daemon_start_hint_fn=daemon_start_hint_fn,
    )
    if client is None:
        return rc

    if args.dry_run:
        print(f"[dry-run] would send {len(text)} chars to daemon ide={args.ide}")
        return 0

    reply, rc = _drive_daemon(client, args, text)
    if rc != -1:
        return rc
    return _finish_drive_reply(
        args,
        text,
        reply,
        run_direct_drive_fn=run_direct_drive_fn,
        should_fallback_fn=should_fallback_fn,
    )
