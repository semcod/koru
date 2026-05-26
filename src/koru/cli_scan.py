"""CLI command for scanning repositories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from koru.scan import run_scan
from koru.scan_render import render_scan_markdown, render_scan_text


def build_scan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru scan",
        description=(
            "Auto-generate planfile tickets from real repo signals "
            "(pytest collection errors, TODO/FIXME markers, missing gates "
            "and semcod tools, gitignore drift). Dry-run by default; "
            "pass --apply to create tickets via `planfile ticket create`."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the proposed tickets in planfile (otherwise dry-run).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of suggestions (default: all).",
    )
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        default=[],
        help=(
            "Limit suggestions to a file or directory path. "
            "Can be repeated; matches suggestion files, titles, and descriptions."
        ),
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Do not run `pytest --collect-only` (faster scan).",
    )
    parser.add_argument(
        "--semcod-artifacts",
        action="store_true",
        help=(
            "Include semcod-style quality exports (jscpd JSON, code2llm analysis.toon*, "
            "testql_api_results.json, redup/regix/redsl/pyqual/prefact/vallm reports). "
            "Otherwise only when KORU_SCAN_SEMCOD_ARTIFACTS is truthy."
        ),
    )
    parser.add_argument(
        "--source",
        default="koru-scan",
        help="`--source` tag used when creating tickets (default: koru-scan).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format for dry-run (default: text).",
    )
    return parser


def scan_main(argv: list[str]) -> int:
    args = build_scan_parser().parse_args(argv)
    result = run_scan(
        project=args.project.resolve(),
        apply=args.apply,
        limit=args.limit,
        skip_pytest=args.skip_pytest,
        include_semcod_artifacts=args.semcod_artifacts,
        paths=args.paths,
        source=args.source,
    )
    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
    if args.output_format == "markdown":
        print(render_scan_markdown(result))
        return 0
    print(render_scan_text(result))
    return 0
