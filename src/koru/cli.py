"""Command-line entrypoint for koru."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from .loop import discover_repositories, run_closed_loop


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
        required=True,
        type=_command_value,
        help="Command to execute in each repository, e.g. 'python -m pytest -q'.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
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
