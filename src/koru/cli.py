"""Command-line entrypoint for koru-loop."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex

from .loop import discover_repositories, run_closed_loop


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run closed-loop automation on semcod repositories.")
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
        help="Command to execute in each repository, e.g. 'python -m pytest -q'.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    repositories = discover_repositories(args.workspace, args.include)
    command = shlex.split(args.command)
    if not command:
        raise SystemExit("Command cannot be empty")

    report = run_closed_loop(command=command, repositories=repositories, max_rounds=args.max_rounds)

    print(
        f"koru-loop: repos={len(report.succeeded) + len(report.failed)} "
        f"succeeded={len(report.succeeded)} failed={len(report.failed)} rounds={report.rounds_executed}"
    )
    for repository in report.failed:
        print(f"FAILED: {repository}")

    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
