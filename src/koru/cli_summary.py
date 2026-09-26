"""CLI entrypoint for daily execution summary: ``koru sum`` and ``koru summary``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def summary_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru sum",
        description="Daily execution summary: Planfile completed/queued tasks, GitHub PRs and duration estimates.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/home/tom/github"),
        help="Workspace root containing target repositories (default: /home/tom/github)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON summary document",
    )
    parser.add_argument(
        "--no-github",
        dest="github",
        action="store_false",
        default=True,
        help="Skip querying GitHub PR status via gh CLI",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Time window in hours for daily recency (default: 24.0)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Directory depth to scan for Planfile repositories (default: 3)",
    )
    args = parser.parse_args(argv)

    try:
        from monag import summary as monag_summary

        data = monag_summary.gather_summary(
            root=args.root,
            hours=args.hours,
            github=args.github,
            depth=args.depth,
        )
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(monag_summary.format_markdown(data))
        return 0
    except Exception as exc:
        print(f"koru sum: error gathering daily execution summary: {exc}", file=sys.stderr)
        return 1
