"""CLI adapter for autonomous and interactive Planfile ticket execution."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


def _is_project_root(path: Path) -> bool:
    return path.is_dir() and ((path / ".planfile").exists() or (path / "koru.yaml").exists())


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for directory in [current, *current.parents]:
        if (directory / ".planfile").exists() or (directory / "koru.yaml").exists():
            return directory
    return current


class _TicketView(NamedTuple):
    """Normalized ticket fields shared by the text/brief/markdown renderers."""

    ticket_id: str
    title: str
    status: str
    priority: str
    executor_kind: str
    queue: str
    labels: str
    files: str
    description: str


def _format_idle(fmt: str) -> str:
    if fmt == "json":
        return json.dumps({"status": "idle", "ticket": None}, indent=2)
    if fmt == "brief":
        return "(no runnable ticket)"
    if fmt == "markdown":
        return "*No runnable ticket found in queue (queue is idle).*"
    return "ℹ️  No runnable ticket found in queue (queue is idle)."


def _ticket_view(ticket: dict) -> _TicketView:
    executor = ticket.get("executor")
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}
    description = (ticket.get("description") or "").strip()
    if len(description) > 300:
        description = description[:297] + "..."
    return _TicketView(
        ticket_id=ticket.get("id") or "UNKNOWN",
        title=ticket.get("name") or ticket.get("title") or "",
        status=ticket.get("status") or "open",
        priority=ticket.get("priority") or "normal",
        executor_kind=(executor.get("kind") if isinstance(executor, dict) else (executor or "human")),
        queue=execution.get("queue") or "default",
        labels=", ".join(ticket.get("labels") or []) or "none",
        files=", ".join(ticket.get("files") or []) or "none",
        description=description,
    )


def _format_markdown_ticket(view: _TicketView) -> str:
    lines = [
        f"### Next Ticket: {view.ticket_id} — {view.title}",
        "",
        f"- **Status**: `{view.status}`",
        f"- **Priority**: `{view.priority}`",
        f"- **Executor**: `{view.executor_kind}`",
        f"- **Queue**: `{view.queue}`",
        f"- **Labels**: {view.labels}",
        f"- **Files**: {view.files}",
    ]
    if view.description:
        lines.extend(["", "#### Description", view.description])
    lines.extend(
        [
            "",
            "#### Quick Actions",
            f"- Run: `koru ticket auto {view.ticket_id}`",
            f"- Agent brief: `koru --context --ticket {view.ticket_id}`",
            f"- Mark done: `planfile ticket done {view.ticket_id}`",
        ]
    )
    return "\n".join(lines)


def _format_text_ticket(view: _TicketView) -> str:
    box_lines = [
        "Next runnable ticket in queue:",
        "┌─────────────────────────────────────────────────────────────",
        f"│ ID:          {view.ticket_id}",
        f"│ Title:       {view.title}",
        f"│ Priority:    {view.priority}",
        f"│ Status:      {view.status}",
        f"│ Executor:    {view.executor_kind}",
        f"│ Queue:       {view.queue}",
        f"│ Labels:      {view.labels}",
        f"│ Files:       {view.files}",
        "└─────────────────────────────────────────────────────────────",
    ]
    if view.description:
        box_lines.extend(["Description:", f"  {view.description}"])
    box_lines.extend(
        [
            "",
            "Quick actions:",
            f"  • Run ticket:       koru ticket auto {view.ticket_id}",
            f"  • Agent brief:      koru --context --ticket {view.ticket_id}",
            f"  • Mark done:        planfile ticket done {view.ticket_id}",
        ]
    )
    return "\n".join(box_lines)


def format_next_ticket(ticket: dict | None, fmt: str = "text") -> str:
    """Format the next runnable ticket for terminal or programmatic consumption."""
    if ticket is None:
        return _format_idle(fmt)
    if fmt == "json":
        return json.dumps(ticket, indent=2)
    view = _ticket_view(ticket)
    if fmt == "brief":
        return f"{view.ticket_id}: {view.title}" if view.title else view.ticket_id
    if fmt == "markdown":
        return _format_markdown_ticket(view)
    return _format_text_ticket(view)


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


def _add_auto_parser(sub: argparse._SubParsersAction) -> None:
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
    auto_p.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=1,
        help="Number of concurrent workers for disjoint tickets (default: 1).",
    )
    auto_p.add_argument("--loop", action="store_true", help="Continuously execute tickets until queue is empty.")
    auto_p.add_argument("--dry-run", action="store_true", help="Preview selected ticket without applying changes.")
    auto_p.add_argument("--max-iterations", type=int, default=50, help="Max tickets in loop mode (default: 50).")
    auto_p.add_argument(
        "--interactive", action="store_true", help="Prompt for human input; automatic mode leaves approvals pending."
    )


def _add_list_parser(sub: argparse._SubParsersAction) -> None:
    list_p = sub.add_parser("list", help="List open planfile tickets.")
    list_p.add_argument("--project", type=Path, default=None)
    list_p.add_argument("--status", default="open")


def _add_next_parser(sub: argparse._SubParsersAction) -> None:
    next_p = sub.add_parser(
        "next",
        help="Show the next runnable Planfile ticket for this project.",
        description="Inspects the Planfile queue and displays the next runnable ticket without modifying state.",
    )
    next_p.add_argument("--project", type=Path, default=None, help="Project directory (default: auto-detected).")
    next_p.add_argument("--queue", "-q", dest="queue_name", default=None, help="Queue name (default: auto).")
    next_p.add_argument("--sprint", "-s", default="current", help="Sprint name (default: current).")
    next_p.add_argument(
        "--count",
        "-c",
        type=int,
        default=1,
        help="Number of runnable tickets to fetch (default: 1).",
    )
    next_p.add_argument(
        "--disjoint-files",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only return tickets touching disjoint files (default: True).",
    )
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


def _add_waves_parser(sub: argparse._SubParsersAction) -> None:
    waves_p = sub.add_parser(
        "waves",
        help="Display parallel execution waves based on dependency toposort.",
        description="Calculates parallel waves where all tickets in a wave can run concurrently.",
    )
    waves_p.add_argument("--project", type=Path, default=None, help="Project directory (default: auto-detected).")
    waves_p.add_argument("--sprint", "-s", default="current", help="Sprint name (default: current).")
    waves_p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )


def build_ticket_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru ticket",
        description="Planfile ticket commands and autonomous executor for Koru.",
    )
    sub = parser.add_subparsers(dest="action", required=False)
    _add_auto_parser(sub)
    _add_list_parser(sub)
    _add_next_parser(sub)
    _add_waves_parser(sub)
    return parser


def _resolve_project(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Path:
    explicit = getattr(args, "project", None)
    if explicit is None:
        return _find_project_root(Path.cwd())
    project = explicit.resolve()
    if not _is_project_root(project):
        parser.error(f"--project is not a Koru project root (no .planfile or koru.yaml): {project}")
    return project


def _queue_name(args: argparse.Namespace) -> str:
    return args.queue_name or os.environ.get("KORU_QUEUE_NAME") or "default"


def _sprint_scoped_runner(sprint: str):
    from koru.queue import run_process as _queue_run_process

    def sprint_runner(command, cwd):
        # Scope the resolver's candidate list while preserving its native
        # readiness query across all sprints (archived dependencies matter).
        candidate_query = ["ticket", "list", "--status", "open", "--format", "json"]
        if list(command[-len(candidate_query) :]) == candidate_query:
            command = [*command, "--sprint", sprint]
        return _queue_run_process(command, cwd)

    return sprint_runner


def _ticket_list(args: argparse.Namespace, project: Path) -> int:
    py = os.environ.get("PY") or sys.executable
    return subprocess.run([py, "-m", "planfile.cli", "ticket", "list", "--status", args.status], cwd=project).returncode


def _load_execution_waves(project: Path, sprint: str) -> list:
    try:
        from planfile import Planfile

        pf = Planfile.auto_discover(project)
        if hasattr(pf, "execution_waves"):
            waves = pf.execution_waves(sprint=sprint)
            if waves:
                return waves
    except Exception:
        pass

    py = os.environ.get("PY") or sys.executable
    proc = subprocess.run(
        [py, "-m", "planfile.cli", "ticket", "list", "--status", "open", "--format", "json"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
        return [[str(t.get("id")) for t in data if isinstance(t, dict)]]
    except Exception:
        return []


def _ticket_waves(args: argparse.Namespace, project: Path) -> int:
    fmt = getattr(args, "format", "text")
    waves = _load_execution_waves(project, args.sprint)
    if fmt == "json":
        print(json.dumps(waves, indent=2))
    elif not waves:
        print("No open ticket waves found.")
    else:
        print(f"Parallel Execution Waves ({len(waves)} waves):")
        for idx, wave in enumerate(waves):
            print(f"  Wave {idx}: {', '.join(wave)}")
    return 0


def _report_next_error(exc_or_result) -> int | None:
    """Print a planfile/next-ticket error; return its exit code or None."""
    if isinstance(exc_or_result, (OSError, ValueError)):
        print(f"koru ticket next: error: {exc_or_result}", file=sys.stderr)
        return 1
    if exc_or_result is not None and exc_or_result.status == "planfile_error":
        print(f"koru ticket next: error: {exc_or_result.message}", file=sys.stderr)
        return exc_or_result.exit_code or 1
    return None


def _ticket_next(args: argparse.Namespace, project: Path) -> int:
    fmt = "brief" if getattr(args, "brief", False) else getattr(args, "format", "text")
    from koru.queue.runner import _next_ticket_or_result, _next_tickets_or_result

    queue_name = _queue_name(args)
    sprint_runner = _sprint_scoped_runner(args.sprint)

    count = getattr(args, "count", 1)
    if count > 1:
        try:
            tickets, early_result = _next_tickets_or_result(
                project,
                sprint_runner,
                count=count,
                queue_name=queue_name,
                disjoint_files=getattr(args, "disjoint_files", True),
            )
        except (OSError, ValueError) as exc:
            return _report_next_error(exc) or 1
        error_code = _report_next_error(early_result)
        if error_code is not None:
            return error_code
        if fmt == "json":
            print(json.dumps(tickets, indent=2, default=str))
        else:
            for t in tickets:
                print(format_next_ticket(t, fmt=fmt))
                print()
        return 0

    try:
        ticket, early_result = _next_ticket_or_result(
            project,
            sprint_runner,
            queue_name=queue_name,
        )
    except (OSError, ValueError) as exc:
        return _report_next_error(exc) or 1
    error_code = _report_next_error(early_result)
    if error_code is not None:
        return error_code

    print(format_next_ticket(ticket, fmt=fmt))
    return 0


def _auto_queue_runners(interactive: bool) -> dict:
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

    return {
        "planfile_runner": _queue_run_process,
        "shell_runner": _queue_run_shell_command,
        "api_runner": _queue_run_api_request,
        "llm_runner": _queue_run_llm_request,
        "prompt_runner": _default_human_prompt if interactive else _autonomous_human_prompt,
    }


def _ticket_auto(args: argparse.Namespace, project: Path, parser: argparse.ArgumentParser) -> int:
    if args.ticket_id and ("/" in args.ticket_id or ":" in args.ticket_id):
        parser.error("Use an exact GitHub issue URL with koru ticket URL; queue mode accepts local IDs only")
    if args.dry_run and args.sync:
        parser.error("--dry-run cannot be combined with --sync")
    if args.sync and not _sync_github(project):
        return 2

    from koru.queue_cli_helpers import (
        emit_queue_run_started,
        open_queue_run_log,
        run_queue_loop_mode,
        run_queue_single_mode,
    )

    concurrency = max(1, getattr(args, "concurrency", 1))
    queue_args = argparse.Namespace(
        no_log=getattr(args, "no_log", False),
        project=project,
        queue=True,
        queue_name=_queue_name(args),
        actor="koru-ticket-auto",
        dry_run=args.dry_run,
        interactive=args.interactive,
        loop=args.loop or (concurrency > 1),
        concurrency=concurrency,
        max_iterations=args.max_iterations,
        ticket=args.ticket_id,
        sprint=args.sprint,
    )

    emit_queue_run_started(queue_args)
    run_log = open_queue_run_log(queue_args)
    runners = _auto_queue_runners(args.interactive)

    if queue_args.loop:
        return run_queue_loop_mode(queue_args, run_log, **runners)
    return run_queue_single_mode(queue_args, run_log, **runners)


def ticket_main(argv: list[str]) -> int:
    parser = build_ticket_parser()

    effective_argv = list(argv)
    if not effective_argv:
        effective_argv = ["auto"]
    elif effective_argv[0].startswith("-"):
        effective_argv = ["auto", *effective_argv]

    args = parser.parse_args(effective_argv)
    project = _resolve_project(args, parser)

    handlers = {
        "list": _ticket_list,
        "waves": _ticket_waves,
        "next": _ticket_next,
    }
    if args.action == "auto":
        return _ticket_auto(args, project, parser)
    handler = handlers.get(args.action)
    if handler is not None:
        return handler(args, project)
    return 0
