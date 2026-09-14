"""CLI adapter for autonomous and interactive Planfile ticket execution."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for directory in [current, *current.parents]:
        if (directory / ".planfile").exists() or (directory / "koru.yaml").exists():
            return directory
    return current


def _sync_github(project: Path, timeout: int = 60) -> bool:
    planfile_dir = project / ".planfile"
    if not planfile_dir.exists():
        return False
    has_github_config = (planfile_dir / "github.planfile.yaml").exists() or (
        planfile_dir / "integrations.planfile.yaml"
    ).exists()
    if not has_github_config:
        return False

    py = os.environ.get("PY") or sys.executable
    print("🔄 koru ticket: Synchronizing GitHub Issues with Planfile...", flush=True)
    try:
        res = subprocess.run(
            [py, "-m", "planfile.cli", "sync", "github", "--direction", "both"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0:
            print("✓ Planfile ↔ GitHub synchronization complete", flush=True)
            return True
        print(f"Planfile sync failed (exit {res.returncode})", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("GitHub sync timed out; ticket execution stopped", file=sys.stderr)
        return False
    except Exception:
        print("GitHub synchronization failed", file=sys.stderr)
        return False


def _autonomous_human_prompt(prompt: str, ticket_id: str) -> str | None:
    """Leave human approval pending; automatic mode cannot answer for an operator."""
    return None


def build_ticket_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru ticket",
        description="Planfile ticket commands and autonomous executor for Koru.",
    )
    sub = parser.add_subparsers(dest="action", required=False)

    auto_p = sub.add_parser(
        "auto",
        help="Select and execute a local actionable Planfile ticket.",
        description="Runs the existing local Planfile queue. Exact GitHub issue URLs use the profile executor.",
    )
    auto_p.add_argument("ticket_id", nargs="?", default=None, help="Local Planfile ticket ID.")
    auto_p.add_argument("--project", type=Path, default=None, help="Project directory (default: auto-detected).")
    auto_p.add_argument("--queue", "-q", dest="queue_name", default=None, help="Queue name (default: auto).")
    auto_p.add_argument("--sprint", "-s", default="current", help="Sprint name (default: current).")
    auto_p.add_argument(
        "--sync",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Explicitly synchronize the configured GitHub backlog before execution.",
    )
    auto_p.add_argument("--loop", action="store_true", help="Continuously execute tickets until queue is empty.")
    auto_p.add_argument("--dry-run", action="store_true", help="Preview selected ticket without applying changes.")
    auto_p.add_argument("--max-iterations", type=int, default=50, help="Max tickets in loop mode (default: 50).")
    auto_p.add_argument(
        "--interactive", action="store_true", help="Prompt for human input; automatic mode leaves approvals pending."
    )

    list_p = sub.add_parser("list", help="List open planfile tickets.")
    list_p.add_argument("--project", type=Path, default=None)
    list_p.add_argument("--status", default="open")

    return parser


def ticket_main(argv: list[str]) -> int:
    parser = build_ticket_parser()

    effective_argv = list(argv)
    if not effective_argv:
        effective_argv = ["auto"]
    elif effective_argv[0].startswith("-"):
        effective_argv = ["auto", *effective_argv]

    args = parser.parse_args(effective_argv)

    project = _find_project_root(args.project or Path.cwd())

    if args.action == "list":
        py = os.environ.get("PY") or sys.executable
        return subprocess.run(
            [py, "-m", "planfile.cli", "ticket", "list", "--status", args.status], cwd=project
        ).returncode

    if args.action == "auto":
        if args.ticket_id and ("/" in args.ticket_id or ":" in args.ticket_id):
            parser.error("Use an exact GitHub issue URL with koru ticket URL; queue mode accepts local IDs only")
        if args.dry_run and args.sync:
            parser.error("--dry-run cannot be combined with --sync")
        if args.sync and not _sync_github(project):
            return 2
        selected_ticket = args.ticket_id
        is_loop = args.loop

        from koru.queue import (
            default_human_prompt as _default_human_prompt,
        )
        from koru.queue import (
            run_api_request as _queue_run_api_request,
        )
        from koru.queue import (
            run_llm_request as _queue_run_llm_request,
        )
        from koru.queue import (
            run_process as _queue_run_process,
        )
        from koru.queue import (
            run_shell_command as _queue_run_shell_command,
        )
        from koru.queue_cli_helpers import (
            emit_queue_run_started,
            open_queue_run_log,
            run_queue_loop_mode,
            run_queue_single_mode,
        )

        queue_args = argparse.Namespace(
            no_log=getattr(args, "no_log", False),
            project=project,
            queue=True,
            queue_name=args.queue_name or os.environ.get("KORU_QUEUE_NAME") or "default",
            actor="koru-ticket-auto",
            dry_run=args.dry_run,
            interactive=args.interactive,
            loop=is_loop,
            max_iterations=args.max_iterations,
            ticket=selected_ticket,
            sprint=args.sprint,
        )

        prompt_runner = _default_human_prompt if args.interactive else _autonomous_human_prompt

        emit_queue_run_started(queue_args)
        run_log = open_queue_run_log(queue_args)
        runners = {
            "planfile_runner": _queue_run_process,
            "shell_runner": _queue_run_shell_command,
            "api_runner": _queue_run_api_request,
            "llm_runner": _queue_run_llm_request,
            "prompt_runner": prompt_runner,
        }

        if queue_args.loop:
            return run_queue_loop_mode(queue_args, run_log, **runners)
        return run_queue_single_mode(queue_args, run_log, **runners)

    return 0
