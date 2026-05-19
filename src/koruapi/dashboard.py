"""Dashboard HTTP server (koru serve) — canonical CLI in :mod:`koruapi`."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from koru.events import emit_management_event
from koruapi.dashboard_serve import DEFAULT_HOST, DEFAULT_PORT, ServeConfig, serve


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru serve",
        description=(
            "Run the koru dashboard (live LLM brief, tickets, topology). "
            "Canonical implementation: koruapi.dashboard."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address (default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port (default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Try next ports if busy (also when KORU_SERVE_AUTO_PORT=1).",
    )
    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=True,
        help="Open dashboard in browser (default).",
    )
    open_group.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser tab.",
    )
    return parser


def dashboard_main(argv: list[str] | None = None) -> int:
    """Entry point for ``koru serve`` and ``koru api dashboard``."""
    from koru.activity_log import activity

    args = build_serve_parser().parse_args(argv)
    config = ServeConfig(
        project=args.project.resolve(),
        host=args.host,
        port=args.port,
        open_browser=args.open_browser,
        queue_name=args.queue_name,
        auto_port=bool(args.auto_port) or _env_truthy("KORU_SERVE_AUTO_PORT"),
    )
    activity(
        "HTTP",
        f"dashboard start project={config.project} http://{config.host}:{config.port}/",
    )
    exit_code = serve(config)
    emit_management_event(
        tool="koru.serve",
        action="completed" if exit_code == 0 else "failed",
        status="completed" if exit_code == 0 else "failed",
        level="info" if exit_code == 0 else "error",
        message=f"exit={exit_code}",
        queue=config.queue_name,
    )
    return exit_code
