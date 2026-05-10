"""Command-line entrypoint for koru."""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import sys
from pathlib import Path

from .agents import (
    detect_agent_options,
    launch_agent,
    save_agent_prompt,
    select_agent,
)
from .bootstrap import import_flat_pipeline
from .context import build_context, render_markdown_handoff
from .doctor import render_text as render_doctor_text, run_diagnostics
from .events import emit_management_event
from .init import init_project
from .loop import discover_repositories, run_closed_loop
from .planfile_queue import run_next_planfile_task, run_planfile_queue_loop
from .run_log import open_run_log_eagerly
from .tasks import create_nl_task
from .watch import watch_planfile_events


def _command_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("Command cannot be empty")
    return stripped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run closed-loop automation on semcod repositories."
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace root.")
    parser.add_argument(
        "--include",
        default="semcod/*",
        help="Glob (relative to workspace) selecting repositories.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum retries for repositories that fail.",
    )
    parser.add_argument(
        "--command",
        type=_command_value,
        help="Command to execute in each repository, e.g. 'python -m pytest -q'.",
    )
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Run one task from the local planfile queue instead of repository loop mode.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for --queue mode.",
    )
    parser.add_argument(
        "--actor",
        default="koru-shell",
        help="Actor name used when claiming planfile queue tickets.",
    )
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Only execute tickets from this planfile execution queue.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the selected planfile queue task without executing it.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "When the next ticket is a 'human' executor, prompt for the answer "
            "on stdin (multi-line, Ctrl-D submits, Ctrl-C cancels). On submit, "
            "the ticket is claimed/started/completed with the answer recorded "
            "in --note and --result-json."
        ),
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help=(
            "Drain the planfile queue: keep fetching and running the next "
            "ticket until the queue is idle, a ticket needs human input we "
            "cannot satisfy, or --max-iterations is reached. Combine with "
            "--interactive to also handle human tickets in the same run."
        ),
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Safety cap on the number of tickets --loop will process (default 100).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch planfile WebSocket events.",
    )
    parser.add_argument(
        "--ws-url",
        default="ws://localhost:8000/ws",
        help="Planfile WebSocket URL for --watch mode.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Stop --watch after this many events, useful for smoke tests.",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Import a flat-format pipeline YAML into .planfile/ for queue-mode execution.",
    )
    parser.add_argument(
        "--from",
        dest="from_file",
        type=Path,
        default=None,
        help="Source flat-pipeline YAML for --bootstrap (e.g. examples/bootstrap.planfile.yaml).",
    )
    parser.add_argument(
        "--sprint",
        default="current",
        help="Target sprint name when --bootstrap writes .planfile/sprints/<sprint>.yaml.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing sprint file during --bootstrap.",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help=(
            "Initialise a koru-managed project in --project: import a "
            "flat pipeline (or generate a 2-ticket starter scaffold), "
            "write .planfile/.koru/policy.yaml stub, and add "
            ".planfile/.koru/ to .gitignore. Pass --from <yaml> to "
            "import an existing pipeline; --force to re-init."
        ),
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help=(
            "Run diagnostic checks against --project (planfile config, "
            "sprints, policy.yaml, .gitignore, planfile binary, CI "
            "command). Exits 1 if any check fails; warnings alone "
            "exit 0. Use --format json for machine-readable output."
        ),
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help=(
            "Emit a self-service brief (ticket + policy + constraints + "
            "command vocabulary) for an LLM agent. The brief is the only "
            "thing an autonomous agent should need to act safely."
        ),
    )
    parser.add_argument(
        "--ticket",
        default=None,
        help="Target a specific ticket id (e.g. PLF-074) for --context. "
             "Default is the next runnable ticket from the queue.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "markdown"],
        default="json",
        help="Output format for --context (default: json).",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable the per-run JSONL log under .planfile/.koru/runs/. "
             "Has no effect outside --queue mode.",
    )
    return parser


def _build_task_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru task",
        description="Create a planfile ticket from a natural-language sentence.",
    )
    parser.add_argument("text", nargs="+", help="Natural-language task description.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--sprint", default="current", help="Target planfile sprint.")
    parser.add_argument("--queue-name", default=None, help="Execution queue for the new ticket.")
    parser.add_argument("--priority", default="normal", help="Ticket priority.")
    return parser


def _build_agent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru agent",
        description="Print or launch the best available LLM/IDE handoff for this project.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument("--ticket", default=None, help="Render prompt for a specific ticket id.")
    parser.add_argument("--agent", dest="agent_id", default=None, help="Agent id to select.")
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch the selected agent if it has a CLI.",
    )
    parser.add_argument("--list", action="store_true", help="List detected agents and exit.")
    return parser


def _task_main(argv: list[str]) -> int:
    args = _build_task_parser().parse_args(argv)
    try:
        created = create_nl_task(
            args.project,
            " ".join(args.text),
            sprint=args.sprint,
            queue_name=args.queue_name,
            priority=args.priority,
        )
    except ValueError as exc:
        print(f"koru task: {exc}")
        return 2
    print(f"koru task: ✓ created {created.ticket_id} in {created.path}")
    print(f"  name:  {created.name}")
    print(f"  queue: {args.queue_name or 'default'}")
    print("Next: run `koru` to get the LLM prompt, or `koru --queue` to execute one task.")
    emit_management_event(
        tool="koru.task",
        action="created",
        status="completed",
        message=created.name,
        queue=args.queue_name,
        details={
            "ticket_id": created.ticket_id,
            "project": str(args.project),
            "sprint": args.sprint,
            "priority": args.priority,
        },
    )
    return 0


def _agent_main(argv: list[str]) -> int:
    args = _build_agent_parser().parse_args(argv)
    project = args.project.resolve()
    agents = detect_agent_options(project)

    if args.list:
        for agent in agents:
            marker = "✓" if agent.available else "·"
            launch = "launchable" if agent.launchable else "manual"
            print(f"{marker} {agent.id:<14} {launch:<10} {agent.reason}")
        return 0

    ctx = build_context(
        project=project,
        ticket_id=args.ticket,
        queue_name=args.queue_name,
    )
    prompt = render_markdown_handoff(ctx)
    if not args.launch:
        save_path = save_agent_prompt(project, prompt)
        print(prompt)
        print(f"\nPrompt saved: {save_path}")
        return 0

    agent = select_agent(
        agents,
        agent_id=args.agent_id,
        interactive=sys.stdin.isatty(),
    )
    if agent is None:
        print("koru agent: no matching agent detected. Use `koru agent --list`.")
        return 2
    return launch_agent(agent, project, prompt)


def _is_bare_invocation(args: argparse.Namespace) -> bool:
    """True when the user typed only ``koru`` (or ``koru --project P``).

    Bare = no action flag (init/bootstrap/context/queue/watch) and no
    ``--command``. We route this to the markdown brief — the friendliest
    starting point for both humans and LLM agents.
    """
    return not (
        args.init
        or args.doctor
        or args.bootstrap
        or args.context
        or args.queue
        or args.watch
        or args.command
    )


def main() -> int:
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] == "task":
        return _task_main(raw_args[1:])
    if raw_args and raw_args[0] == "agent":
        return _agent_main(raw_args[1:])

    args = _build_parser().parse_args(raw_args)

    # Friendliest default: ``koru`` with no action flag emits the
    # markdown brief. LLM agents pasted into a chat just see the rules.
    if _is_bare_invocation(args):
        args.context = True
        args.output_format = "markdown"

    if args.doctor:
        report = run_diagnostics(args.project)
        if args.output_format == "json":
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(render_doctor_text(report))
        emit_management_event(
            tool="koru.doctor",
            action="completed",
            status="failed" if report.has_failures else "completed",
            level="error" if report.has_failures else "info",
            message=", ".join(
                f"{k}={v}" for k, v in report.summary().items() if v
            ),
            queue=args.queue_name,
            details={"project": str(args.project)},
        )
        return 1 if report.has_failures else 0

    if args.init:
        try:
            report = init_project(
                args.project,
                from_file=args.from_file,
                sprint=args.sprint,
                force=args.force,
            )
        except FileExistsError as exc:
            print(f"koru init: {exc}")
            return 1
        except (FileNotFoundError, ValueError) as exc:
            print(f"koru init: {exc}")
            return 2
        print(f"koru init: ✓ project initialised at {report.project}")
        print(report.summary())
        print()
        print("Next: run `koru` to get the LLM brief, or "
              "`koru --queue --loop` to drain the starter sprint.")
        emit_management_event(
            tool="koru.init",
            action="completed",
            status="completed",
            message=report.summary(),
            queue=args.queue_name,
            details={
                "project": str(args.project),
                "sprint": args.sprint,
                "used_starter_pipeline": report.used_starter_pipeline,
            },
        )
        return 0

    if args.context:
        ctx = build_context(
            project=args.project,
            ticket_id=args.ticket,
            queue_name=args.queue_name,
        )
        if args.output_format == "markdown":
            print(render_markdown_handoff(ctx))
        else:
            print(json.dumps(ctx, indent=2, sort_keys=True))
        return 0

    if args.bootstrap:
        emit_management_event(
            tool="koru.bootstrap",
            action="started",
            status="running",
            message=str(args.from_file or ""),
            queue=args.queue_name,
            details={"project": str(args.project), "sprint": args.sprint},
        )
        if args.from_file is None:
            parser = _build_parser()
            parser.error("--bootstrap requires --from PATH")
        try:
            report = import_flat_pipeline(
                args.from_file,
                args.project,
                sprint=args.sprint,
                overwrite=args.force,
            )
        except FileExistsError as exc:
            print(f"koru bootstrap: {exc}")
            emit_management_event(
                tool="koru.bootstrap",
                action="failed",
                status="failed",
                level="error",
                message=str(exc),
                queue=args.queue_name,
            )
            return 1
        except (FileNotFoundError, ValueError) as exc:
            print(f"koru bootstrap: {exc}")
            emit_management_event(
                tool="koru.bootstrap",
                action="failed",
                status="failed",
                level="error",
                message=str(exc),
                queue=args.queue_name,
            )
            return 2
        print("koru bootstrap: ✓ imported")
        print(report.summary())
        emit_management_event(
            tool="koru.bootstrap",
            action="completed",
            status="completed",
            message=report.summary(),
            queue=args.queue_name,
            details={"project": str(args.project), "sprint": args.sprint},
        )
        return 0

    if args.watch:
        emit_management_event(
            tool="koru.watch",
            action="started",
            status="running",
            message=args.ws_url,
            queue=args.queue_name,
        )
        try:
            seen = asyncio.run(watch_planfile_events(args.ws_url, max_events=args.max_events))
        except RuntimeError as exc:
            print(f"koru watch: {exc}")
            emit_management_event(
                tool="koru.watch",
                action="failed",
                status="failed",
                level="error",
                message=str(exc),
                queue=args.queue_name,
            )
            return 1
        emit_management_event(
            tool="koru.watch",
            action="completed",
            status="completed",
            message=f"seen={seen}",
            queue=args.queue_name,
            details={"ws_url": args.ws_url, "seen": seen},
        )
        return 0

    if args.queue:
        emit_management_event(
            tool="koru.queue",
            action="started",
            status="running",
            message="loop" if args.loop else "single",
            queue=args.queue_name,
            details={
                "project": str(args.project),
                "actor": args.actor,
                "dry_run": args.dry_run,
                "interactive": args.interactive,
            },
        )
        # Per-run JSONL log under <project>/.planfile/.koru/runs/.
        # Skip for --dry-run (preserves "dry-run leaves zero trace") and
        # when the operator passes --no-log.
        run_log = None
        if not args.no_log and not args.dry_run:
            run_log = open_run_log_eagerly(args.project, prefix="queue")
            run_log.write_header(
                project=args.project,
                mode="loop" if args.loop else "single",
                actor=args.actor,
                queue_name=args.queue_name,
                interactive=args.interactive,
            )

        if args.loop:
            def _progress(r, i):  # noqa: ANN001 — internal helper
                ticket = r.ticket_id or "-"
                kind = r.executor_kind or "-"
                marker = {
                    "completed": "✓",
                    "failed": "✗",
                    "waiting_input": "⏸",
                    "idle": "•",
                    "dry_run": "?",
                    "unsupported_executor": "!",
                    "planfile_error": "!",
                }.get(r.status, "·")
                print(f"  [{i:>3}] {marker} {r.status:<22} {ticket:<14} ({kind})")
                if run_log is not None:
                    run_log.write_iteration(iteration=i, result=r)
                emit_management_event(
                    tool="koru.queue",
                    action="iteration",
                    status=r.status,
                    level="error" if r.status in {"failed", "planfile_error"} else "info",
                    message=r.message,
                    queue=args.queue_name,
                    details={
                        "iteration": i,
                        "ticket_id": r.ticket_id,
                        "executor_kind": r.executor_kind,
                        "exit_code": r.exit_code,
                    },
                )

            loop_result = run_planfile_queue_loop(
                project=args.project,
                actor=args.actor,
                queue_name=args.queue_name,
                interactive=args.interactive,
                max_iterations=args.max_iterations,
                progress_callback=_progress,
            )
            if run_log is not None:
                run_log.write_footer(summary=loop_result)
            print()
            print(f"koru queue loop: {loop_result.summary()}")
            if loop_result.completed:
                print(f"  completed: {', '.join(loop_result.completed)}")
            if loop_result.failed:
                print(f"  failed:    {', '.join(loop_result.failed)}")
            if loop_result.waiting:
                print(f"  waiting:   {', '.join(loop_result.waiting)}")
            exit_code = 0 if loop_result.last_status in {
                "completed", "idle", "waiting_input", "dry_run"
            } else 1
            emit_management_event(
                tool="koru.queue",
                action="completed" if exit_code == 0 else "failed",
                status=loop_result.last_status,
                level="error" if exit_code else "info",
                message=loop_result.summary(),
                queue=args.queue_name,
                details={
                    "completed": loop_result.completed,
                    "failed": loop_result.failed,
                    "waiting": loop_result.waiting,
                    "iterations": loop_result.iterations,
                },
            )
            return exit_code

        result = run_next_planfile_task(
            project=args.project,
            actor=args.actor,
            dry_run=args.dry_run,
            queue_name=args.queue_name,
            interactive=args.interactive,
        )
        if run_log is not None:
            run_log.write_iteration(iteration=1, result=result)
            # Build a one-shot summary so the footer schema matches loop runs.
            single_summary = type(
                "SingleSummary",
                (),
                {
                    "iterations": 1,
                    "completed": (
                        [result.ticket_id]
                        if result.status == "completed" and result.ticket_id
                        else []
                    ),
                    "failed": (
                        [result.ticket_id]
                        if result.status == "failed" and result.ticket_id
                        else []
                    ),
                    "waiting": (
                        [result.ticket_id]
                        if result.status == "waiting_input" and result.ticket_id
                        else []
                    ),
                    "last_status": result.status,
                },
            )()
            run_log.write_footer(summary=single_summary)
        print(
            f"koru queue: status={result.status} "
            f"ticket={result.ticket_id or '-'} executor={result.executor_kind or '-'}"
        )
        if result.message:
            print(result.message)
        exit_code = 0 if result.status in {"completed", "idle", "waiting_input", "dry_run"} else 1
        emit_management_event(
            tool="koru.queue",
            action="completed" if exit_code == 0 else "failed",
            status=result.status,
            level="error" if exit_code else "info",
            message=result.message,
            queue=args.queue_name,
            details={
                "ticket_id": result.ticket_id,
                "executor_kind": result.executor_kind,
                "exit_code": result.exit_code,
                "dry_run": args.dry_run,
            },
        )
        return exit_code

    if not args.command:
        parser = _build_parser()
        parser.error("--command is required unless --queue is used")

    emit_management_event(
        tool="koru.loop",
        action="started",
        status="running",
        message=args.command,
        details={"workspace": str(args.workspace), "include": args.include},
    )
    repositories = discover_repositories(args.workspace, args.include)
    command = shlex.split(args.command)

    report = run_closed_loop(
        command=command,
        repositories=repositories,
        max_rounds=args.max_rounds,
    )

    print(
        f"koru: repos={len(report.succeeded) + len(report.failed)} "
        f"succeeded={len(report.succeeded)} failed={len(report.failed)} "
        f"rounds={report.rounds_executed}"
    )
    for repository in report.failed:
        print(f"FAILED: {repository}")

    exit_code = 0 if not report.failed else 1
    emit_management_event(
        tool="koru.loop",
        action="completed" if exit_code == 0 else "failed",
        status="completed" if exit_code == 0 else "failed",
        level="error" if exit_code else "info",
        message=(
            f"repos={len(report.succeeded) + len(report.failed)} "
            f"succeeded={len(report.succeeded)} failed={len(report.failed)}"
        ),
        details={"failed": [str(item) for item in report.failed]},
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
