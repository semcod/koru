"""CLI adapter for autonomous and interactive Planfile ticket execution."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for directory in [current, *current.parents]:
        if directory in {Path("/tmp"), Path("/")}:
            continue
        if (directory / ".planfile").exists() or (directory / "koru.yaml").exists():
            return directory
    return current


def format_next_ticket(ticket: dict | None, fmt: str = "text") -> str:
    """Format the next runnable ticket for terminal or programmatic consumption."""
    if ticket is None:
        if fmt == "json":
            return json.dumps({"status": "idle", "ticket": None}, indent=2)
        if fmt == "brief":
            return "(no runnable ticket)"
        if fmt == "markdown":
            return "*No runnable ticket found in queue (queue is idle).*"
        return "ℹ️  No runnable ticket found in queue (queue is idle)."

    ticket_id = ticket.get("id") or "UNKNOWN"
    title = ticket.get("name") or ticket.get("title") or ""
    status = ticket.get("status") or "open"
    priority = ticket.get("priority") or "normal"
    executor = ticket.get("executor")
    executor_kind = executor.get("kind") if isinstance(executor, dict) else (executor or "human")
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}
    queue = execution.get("queue") or "default"
    labels = ", ".join(ticket.get("labels") or []) or "none"
    files = ", ".join(ticket.get("files") or []) or "none"
    description = (ticket.get("description") or "").strip()
    if len(description) > 300:
        description = description[:297] + "..."

    if fmt == "brief":
        return f"{ticket_id}: {title}" if title else ticket_id

    if fmt == "json":
        return json.dumps(ticket, indent=2)

    if fmt == "markdown":
        lines = [
            f"### Next Ticket: {ticket_id} — {title}",
            f"- **Status**: `{status}`",
            f"- **Priority**: `{priority}`",
            f"- **Executor**: `{executor_kind}`",
            f"- **Queue**: `{queue}`",
            f"- **Labels**: {labels}",
            f"- **Files**: `{files}`",
        ]
        if description:
            lines.extend(["", "#### Description", description])
        lines.extend([
            "",
            "#### Quick Actions",
            f"- Run: `koru ticket auto {ticket_id}`",
            f"- Agent brief: `koru --context --ticket {ticket_id}`",
            f"- Mark done: `planfile ticket done {ticket_id}`",
        ])
        return "\n".join(lines)

    # default: text format
    box_lines = [
        "Next runnable ticket in queue:",
        "┌─────────────────────────────────────────────────────────────",
        f"│ ID:          {ticket_id}",
        f"│ Title:       {title}",
        f"│ Priority:    {priority}",
        f"│ Status:      {status}",
        f"│ Executor:    {executor_kind}",
        f"│ Queue:       {queue}",
        f"│ Labels:      {labels}",
        f"│ Files:       {files}",
        "└─────────────────────────────────────────────────────────────",
    ]
    if description:
        box_lines.extend(["Description:", f"  {description}"])
    box_lines.extend([
        "",
        "Quick actions:",
        f"  • Run ticket:       koru ticket auto {ticket_id}",
        f"  • Agent brief:      koru --context --ticket {ticket_id}",
        f"  • Mark done:        planfile ticket done {ticket_id}",
    ])
    return "\n".join(box_lines)


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

    next_p = sub.add_parser(
        "next",
        help="Show the next runnable Planfile ticket for this project.",
        description="Inspects the Planfile queue and displays the next runnable ticket without modifying state.",
    )
    next_p.add_argument("--project", type=Path, default=None, help="Project directory (default: auto-detected).")
    next_p.add_argument("--queue", "-q", dest="queue_name", default=None, help="Queue name (default: auto).")
    next_p.add_argument("--sprint", "-s", default="current", help="Sprint name (default: current).")
    next_p.add_argument(
        "--format",
        choices=["text", "json", "markdown", "brief"],
        default="text",
        help="Output format (default: text).",
    )
    next_p.add_argument(
        "--brief",
        action="store_true",
        help="Shorthand for --format brief.",
    )

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

    if args.action == "next":
        fmt = "brief" if getattr(args, "brief", False) else getattr(args, "format", "text")
        from koru.queue.runner import _next_ticket_or_result
        from koru.queue import run_process as _queue_run_process

        queue_name = args.queue_name or os.environ.get("KORU_QUEUE_NAME") or "default"
        ticket, early_result = _next_ticket_or_result(
            project,
            _queue_run_process,
            queue_name=queue_name,
        )
        if early_result and early_result.status == "planfile_error":
            print(f"koru ticket next: error: {early_result.message}", file=sys.stderr)
            return early_result.exit_code or 1

        output = format_next_ticket(ticket, fmt=fmt)
        print(output)
        return 0

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
