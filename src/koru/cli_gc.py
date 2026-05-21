"""CLI command for garbage-collecting stale planfile tickets."""

from __future__ import annotations

import argparse
from pathlib import Path

from koru.gc import DEFAULT_KEEP_LAST, DEFAULT_MAX_AGE_DAYS, GC_STATUSES, run_gc


def build_gc_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru gc",
        description=(
            "Garbage-collect stale planfile tickets. Removes done, failed, "
            "and blocked tickets that exceed --max-age days. Dry-run by "
            "default; pass --apply to actually delete."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete stale tickets (default is dry-run preview).",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Delete tickets finished more than N days ago (default {DEFAULT_MAX_AGE_DAYS}).",
    )
    parser.add_argument(
        "--keep-last",
        type=int,
        default=DEFAULT_KEEP_LAST,
        help=(
            "Always keep the N most recently finished tickets per status, "
            f"even if older than --max-age (default {DEFAULT_KEEP_LAST})."
        ),
    )
    parser.add_argument(
        "--status",
        default=",".join(sorted(GC_STATUSES)),
        help=(
            f"Comma-separated ticket statuses to clean (default: {','.join(sorted(GC_STATUSES))})."
        ),
    )
    parser.add_argument(
        "--sprint",
        default="current",
        help="Sprint YAML to scan (default: current).",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Skip archiving removed tickets to .planfile/.koru/gc/.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def gc_main(argv: list[str]) -> int:
    from koru.gc_cli_helpers import (
        emit_gc_management_event,
        gc_statuses_from_args,
        print_gc_report,
    )

    args = build_gc_parser().parse_args(argv)
    result = run_gc(
        args.project.resolve(),
        apply=args.apply,
        statuses=gc_statuses_from_args(args.status),
        max_age_days=args.max_age,
        keep_last=args.keep_last,
        sprint=args.sprint,
        archive=not args.no_archive,
    )
    print_gc_report(args, result)
    emit_gc_management_event(args, result)
    return 0
