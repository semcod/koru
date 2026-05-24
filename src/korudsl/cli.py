"""CLI for ``koru dsl`` / ``koru-dsl``."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from .transform import dsl_roundtrip_report, library_from_any, library_to_any, load_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru dsl",
        description="Bidirectional scenario DSL ↔ OQL library transforms.",
    )
    parser.add_argument("--version", action="version", version=f"koru-dsl {_cli_version()}")
    sub = parser.add_subparsers(dest="action", required=True)

    to_lib = sub.add_parser("to-library", help="DSL or goals JSON → library JSON.")
    to_lib.add_argument("input", type=Path, nargs="?", help="Input file (stdin if omitted).")
    to_lib.add_argument("-o", "--output", type=Path, help="Output JSON path (stdout if omitted).")
    to_lib.add_argument(
        "--kind",
        choices=("dsl", "goals_json", "library_json", "auto"),
        default="auto",
    )

    to_dsl = sub.add_parser("to-dsl", help="Library JSON → DSL text.")
    to_dsl.add_argument("input", type=Path, nargs="?", help="Input JSON (stdin if omitted).")
    to_dsl.add_argument("-o", "--output", type=Path, help="Output DSL path (stdout if omitted).")

    rt = sub.add_parser("roundtrip", help="DSL → library → DSL round-trip report.")
    rt.add_argument("input", type=Path, nargs="?", help="DSL file (stdin if omitted).")

    return parser


def _cli_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _read_input(path: Path | None) -> str:
    if path is None:
        return sys.stdin.read()
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.action == "to-library":
        raw = _read_input(args.input)
        kind = None if args.kind == "auto" else args.kind
        if args.input is not None and args.kind == "auto":
            detected, raw = load_path(args.input)
            kind = detected if detected != "library_json" else "library_json"
        lib = library_from_any(raw, kind=kind)
        out = json.dumps(lib, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(out, encoding="utf-8")
        else:
            sys.stdout.write(out)
        return 0

    if args.action == "to-dsl":
        raw = _read_input(args.input)
        lib = library_from_any(raw, kind="library_json")
        out = library_to_any(lib, fmt="dsl")
        if args.output:
            args.output.write_text(out, encoding="utf-8")
        else:
            sys.stdout.write(out)
        return 0

    if args.action == "roundtrip":
        raw = _read_input(args.input)
        report = dsl_roundtrip_report(raw)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 0 if report.get("ok") else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
