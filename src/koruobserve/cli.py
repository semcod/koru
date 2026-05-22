"""CLI for ``koru observe`` — one-command start/stop/status of observation mesh."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koruobserve.lifecycle import observe_down, observe_status, observe_up


def build_observe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru observe",
        description="Start, stop, or inspect the local observation mesh (relay + vision + dashboard).",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_project(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", type=Path, default=None, help="Project root (overrides global flag).")

    up = sub.add_parser("up", help="Start relay + vision agent + dashboard in the background.")
    _add_project(up)
    up.add_argument("--relay-host", default="127.0.0.1", help="Relay bind host.")
    up.add_argument("--relay-port", type=int, default=9876, help="Relay bind port (auto if busy).")
    up.add_argument("--dashboard-host", default=None, help="Dashboard bind host (config default).")
    up.add_argument("--dashboard-port", type=int, default=None, help="Dashboard bind port (config default).")
    up.add_argument("--interval", type=float, default=None, help="Vision capture interval seconds.")

    for name, help_text in (
        ("down", "Stop relay + vision agent + dashboard."),
        ("status", "Show PID and aliveness for each process."),
        ("grid", "Print the dashboard /grid URL."),
    ):
        _add_project(sub.add_parser(name, help=help_text))
    return parser


def _project_arg(args: argparse.Namespace) -> Path:
    sub_project = getattr(args, "project", None)
    if isinstance(sub_project, Path):
        return sub_project
    return args.project


def _cmd_up(args: argparse.Namespace) -> int:
    state = observe_up(
        _project_arg(args),
        relay_host=args.relay_host,
        relay_port=args.relay_port,
        dashboard_host=args.dashboard_host,
        dashboard_port=args.dashboard_port,
        interval_seconds=args.interval,
    )
    print(
        f"koru observe: up\n"
        f"  relay     ws://{args.relay_host}:?   pid={state.relay_pid}\n"
        f"  vision    pid={state.vision_pid}\n"
        f"  dashboard {state.dashboard_url}      pid={state.dashboard_pid}\n"
        f"  open      {state.grid_url}"
    )
    return 0


def _cmd_down(args: argparse.Namespace) -> int:
    stopped = observe_down(_project_arg(args))
    for name, killed in stopped.items():
        print(f"koru observe: {name} stopped={killed}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    status = observe_status(_project_arg(args))
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if all(item["alive"] for item in status.values()) else 1


def _cmd_grid(args: argparse.Namespace) -> int:
    from koruobserve.paths import state_file

    path = state_file(_project_arg(args))
    if not path.is_file():
        print("koru observe: not running (no state file). Run 'koru observe up' first.", file=sys.stderr)
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    print(data.get("grid_url", ""))
    return 0


_HANDLERS = {
    "up": _cmd_up,
    "down": _cmd_down,
    "status": _cmd_status,
    "grid": _cmd_grid,
}


def observe_main(argv: list[str] | None = None) -> int:
    args = build_observe_parser().parse_args(argv)
    handler = _HANDLERS.get(args.command)
    if handler is None:
        print(f"koru observe: unknown command {args.command!r}", file=sys.stderr)
        return 2
    return handler(args)
