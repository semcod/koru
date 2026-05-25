"""Argparse setup for ``koru observe`` (kept separate to keep cli.py small)."""

from __future__ import annotations

import argparse
from pathlib import Path

_SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("up", "Start relay + vision agent + dashboard in the background."),
    ("down", "Stop relay + vision agent + dashboard."),
    ("status", "Show PID and aliveness for each process."),
    ("grid", "Print the dashboard /grid URL."),
    ("trace", "Render the semantic observability timeline."),
    ("install", "Pip-install optional observe dependencies (mss + websockets)."),
    ("providers", "List, test, or reset screen-capture providers."),
)

_PROVIDERS_SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("list", "Show capture providers (availability + auto-rank order)."),
    ("test", "Try capturing with one provider or all of them."),
    ("reset", "Clear saved ScreenCast consent token (.koru/keys/screencast.session)."),
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
    parser.add_argument(
        "--relay-port",
        type=int,
        default=9876,
        help="Relay bind port (auto if busy).",
    )
    parser.add_argument(
        "--dashboard-host",
        default=None,
        help="Dashboard bind host (config default).",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=None,
        help="Dashboard bind port (config default).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Vision capture interval seconds (minimum 30).",
    )


def build_observe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru observe",
        description=(
            "Start, stop, or inspect the local observation mesh "
            "(relay + vision + dashboard)."
        ),
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
        if name == "providers":
            prov = cmd.add_subparsers(dest="providers_command", required=True)
            for prov_name, prov_help in _PROVIDERS_SUBCOMMANDS:
                prov_cmd = prov.add_parser(prov_name, help=prov_help)
                _add_subproject(prov_cmd)
                prov_cmd.add_argument(
                    "--json",
                    action="store_true",
                    help="Emit JSON instead of text.",
                )
                if prov_name == "test":
                    prov_cmd.add_argument(
                        "name",
                        nargs="?",
                        default=None,
                        help="Provider name (default: test all).",
                    )
                    prov_cmd.add_argument(
                        "--scale",
                        type=float,
                        default=0.2,
                        help="Thumbnail scale for the probe capture.",
                    )
        if name == "trace":
            cmd.add_argument(
                "--format",
                choices=("compact", "dsl", "json", "path"),
                default="compact",
                help="Trace output format (default: compact OBS lines).",
            )
            cmd.add_argument("--corr", default=None, help="Filter by correlation id.")
            cmd.add_argument("--ticket", default=None, help="Filter by ticket id.")
            cmd.add_argument(
                "--limit",
                type=int,
                default=50,
                help="Maximum recent observability events to render.",
            )
    return parser


def project_path(args: argparse.Namespace) -> Path:
    raw = getattr(args, "sub_project", None) or getattr(args, "project", None) or Path.cwd()
    return Path(raw).expanduser().resolve()
