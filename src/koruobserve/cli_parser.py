"""Argparse setup for ``koru observe`` (kept separate to keep cli.py small)."""

from __future__ import annotations

import argparse
from pathlib import Path


_SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("up", "Start relay + vision agent + dashboard in the background."),
    ("down", "Stop relay + vision agent + dashboard."),
    ("status", "Show PID and aliveness for each process."),
    ("grid", "Print the dashboard /grid URL."),
    ("install", "Pip-install optional observe dependencies (mss + websockets)."),
)


def _add_subproject(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project",
        type=Path,
        default=argparse.SUPPRESS,
        dest="sub_project",
        help="Project root (alternative placement; overrides global --project).",
    )


def _register_up_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--relay-host", default="127.0.0.1", help="Relay bind host.")
    parser.add_argument("--relay-port", type=int, default=9876, help="Relay bind port (auto if busy).")
    parser.add_argument("--dashboard-host", default=None, help="Dashboard bind host (config default).")
    parser.add_argument("--dashboard-port", type=int, default=None, help="Dashboard bind port (config default).")
    parser.add_argument("--interval", type=float, default=None, help="Vision capture interval seconds.")


def build_observe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru observe",
        description="Start, stop, or inspect the local observation mesh (relay + vision + dashboard).",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root (place before the subcommand, e.g. koru observe --project . up).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in _SUBCOMMANDS:
        cmd = sub.add_parser(name, help=help_text)
        _add_subproject(cmd)
        if name == "up":
            _register_up_arguments(cmd)
    return parser


def project_path(args: argparse.Namespace) -> Path:
    raw = getattr(args, "sub_project", None) or getattr(args, "project", None) or Path.cwd()
    return Path(raw).expanduser().resolve()
