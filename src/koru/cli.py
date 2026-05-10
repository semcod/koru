"""Command-line entrypoint for koru."""

from __future__ import annotations

import argparse
import asyncio
import shlex
from pathlib import Path

from .bootstrap import import_flat_pipeline
from .loop import discover_repositories, run_closed_loop
from .planfile_queue import run_next_planfile_task
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
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.bootstrap:
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
            return 1
        except (FileNotFoundError, ValueError) as exc:
            print(f"koru bootstrap: {exc}")
            return 2
        print("koru bootstrap: ✓ imported")
        print(report.summary())
        return 0

    if args.watch:
        try:
            asyncio.run(watch_planfile_events(args.ws_url, max_events=args.max_events))
        except RuntimeError as exc:
            print(f"koru watch: {exc}")
            return 1
        return 0

    if args.queue:
        result = run_next_planfile_task(
            project=args.project,
            actor=args.actor,
            dry_run=args.dry_run,
            queue_name=args.queue_name,
        )
        print(
            f"koru queue: status={result.status} "
            f"ticket={result.ticket_id or '-'} executor={result.executor_kind or '-'}"
        )
        if result.message:
            print(result.message)
        return 0 if result.status in {"completed", "idle", "waiting_input", "dry_run"} else 1

    if not args.command:
        parser = _build_parser()
        parser.error("--command is required unless --queue is used")

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

    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
