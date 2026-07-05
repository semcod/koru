import argparse
import asyncio  # noqa: F401
import os  # noqa: F401
import sys  # noqa: F401
from pathlib import Path
from typing import Any  # noqa: F401

from koru.agents import detect_agent_options  # noqa: F401
from koru.autonomous import autonomous_main, stop_prior_autonomous_for_auto_start  # noqa: F401
from koru.bootstrap import import_flat_pipeline  # noqa: F401
from koru.context import build_context, render_markdown_handoff  # noqa: F401
from koru.events import emit_management_event  # noqa: F401
from koru.serve import DEFAULT_HOST, DEFAULT_PORT
from koru.tasks import create_nl_task  # noqa: F401
from koru.tools import (
    build_tool_task_scaffold,  # noqa: F401
    detect_tools,  # noqa: F401
    find_tool_entry,  # noqa: F401
    load_tool_registry,  # noqa: F401
    render_tools_detect_text,  # noqa: F401
)


def _build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru serve",
        description=(
            "Run a local dashboard for koru (live LLM brief, ticket, "
            "policy, agent lanes). Binds to 127.0.0.1 by default."
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
        help=f"TCP port to listen on (default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help=(
            "If the port is busy, try the next ports (then an ephemeral port). "
            "Also on when KORU_SERVE_AUTO_PORT is 1/true/yes."
        ),
    )
    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=True,
        help="Open the dashboard URL in the default browser (default).",
    )
    open_group.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser tab; just start the server.",
    )
    return parser


def _serve_main(argv: list[str]) -> int:
    from koruapi.dashboard import dashboard_main

    return dashboard_main(argv)


