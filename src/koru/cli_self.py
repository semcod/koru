"""CLI for Koru self-control diagnostics and repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from koru.self_control import (
    format_self_control_report,
    repair_self_control,
    run_self_control,
)


def _add_common_args(parser: argparse.ArgumentParser, *, suppress_defaults: bool = False) -> None:
    default: Any = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument("--project", type=Path, default=default)
    parser.add_argument("--ide", default=default)
    parser.add_argument("--socket", type=Path, default=default)
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS if suppress_defaults else False,
        help="Emit machine-readable JSON.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru self")
    _add_common_args(parser)
    sub = parser.add_subparsers(dest="command")
    doctor = sub.add_parser("doctor", help="Diagnose Koru's own package/plugin control plane.")
    _add_common_args(doctor, suppress_defaults=True)
    repair = sub.add_parser("repair", help="Run local repairs for Koru itself.")
    _add_common_args(repair, suppress_defaults=True)
    repair.add_argument("--yes", action="store_true", help="Actually perform writes.")
    return parser


def self_main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "doctor"
    project = (args.project or Path.cwd()).expanduser().resolve()
    ide = args.ide or "auto"
    socket_path = args.socket
    if command == "doctor":
        report = run_self_control(project, ide=ide, socket_path=socket_path)
    elif command == "repair":
        report = repair_self_control(
            project,
            ide=ide,
            socket_path=socket_path,
            yes=bool(args.yes),
        )
    else:  # pragma: no cover - argparse owns this
        parser.error(f"unknown command: {command}")

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_self_control_report(report))
    return 1 if report.has_failures else 0


__all__ = ["self_main"]
