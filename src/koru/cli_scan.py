"""CLI command for scanning repositories."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from koru.scan import ScanResult, run_scan


_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR_FORCE") in {"1", "true", "TRUE", "yes", "YES"}:
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _color_signal(signal: str, *, enabled: bool) -> str:
    if not enabled:
        return signal
    lowered = signal.lower()
    if "critical" in lowered or "bug" in lowered:
        return f"{_RED}{signal}{_RESET}"

    by_token = {
        "code2llm": _CYAN,
        "jscpd": _BLUE,
        "redup": _MAGENTA,
        "pytest": _YELLOW,
        "testql": _GREEN,
        "mypy": _BLUE,
        "ruff": _GREEN,
        "pylint": _YELLOW,
    }
    for token, color in by_token.items():
        if token in lowered:
            return f"{color}{signal}{_RESET}"

    return f"{_DIM}{signal}{_RESET}"


def _color_priority(priority: str, *, enabled: bool) -> str:
    if not enabled:
        return priority
    mapping = {
        "critical": _RED,
        "high": _YELLOW,
        "normal": _CYAN,
        "low": _DIM,
    }
    code = mapping.get(priority, _DIM)
    return f"{code}{priority}{_RESET}"


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
        "--skip-pytest",
        action="store_true",
        help="Do not run `pytest --collect-only` (faster scan).",
    )
    parser.add_argument(
        "--semcod-artifacts",
        action="store_true",
        help=(
            "Include semcod-style quality exports (jscpd JSON, code2llm analysis.toon*, "
            "testql_api_results.json, redup filtered JSON). "
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


def render_scan_text(result: ScanResult) -> str:
    color = _supports_color()
    if not result.suggestions:
        return "koru scan: no suggestions — repo looks clean."
    lines: list[str] = [f"koru scan: {len(result.suggestions)} suggestion(s)"]
    for s in result.suggestions:
        marker = {"critical": "!!", "high": "!", "normal": "·", "low": " "}.get(
            s.priority,
            "·",
        )
        priority = _color_priority(f"{s.priority:<8}", enabled=color)
        signal = _color_signal(f"{s.signal:<15}", enabled=color)
        marker_prefix = f"{_BOLD}[{marker}]{_RESET}" if color else f"[{marker}]"
        lines.append(f"  {marker_prefix} {priority} {signal} {s.title}")
    if result.applied:
        lines.append("")
        lines.append(f"Applied ({len(result.applied)}):")
        for t in result.applied:
            lines.append(f"  + {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"Skipped ({len(result.skipped)}):")
        for t in result.skipped:
            lines.append(f"  - {t}")
    return "\n".join(lines)


def render_scan_markdown(result: ScanResult) -> str:
    if not result.suggestions:
        return "# koru scan\n\n_No suggestions — repo looks clean._\n"
    lines = [
        "# koru scan",
        "",
        f"Found **{len(result.suggestions)}** suggestion(s).",
        "",
        "| priority | signal | title |",
        "| --- | --- | --- |",
    ]
    for s in result.suggestions:
        lines.append(f"| `{s.priority}` | `{s.signal}` | {s.title} |")
    if result.applied:
        lines.append("")
        lines.append(f"## Applied ({len(result.applied)})")
        for t in result.applied:
            lines.append(f"- {t}")
    if result.skipped:
        lines.append("")
        lines.append(f"## Skipped ({len(result.skipped)})")
        for t in result.skipped:
            lines.append(f"- {t}")
    return "\n".join(lines) + "\n"


def scan_main(argv: list[str]) -> int:
    args = build_scan_parser().parse_args(argv)
    result = run_scan(
        project=args.project.resolve(),
        apply=args.apply,
        limit=args.limit,
        skip_pytest=args.skip_pytest,
        include_semcod_artifacts=args.semcod_artifacts,
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
