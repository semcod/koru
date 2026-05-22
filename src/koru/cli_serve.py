import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any
from koru.events import emit_management_event
from koru.tasks import create_nl_task
from koru.tools import build_tool_task_scaffold, detect_tools, find_tool_entry, load_tool_registry, render_tools_detect_text
from koru.serve import DEFAULT_HOST, DEFAULT_PORT
from koru.agents import detect_agent_options
from koru.context import build_context, render_markdown_handoff
from koru.autonomous import autonomous_main, stop_prior_autonomous_for_auto_start
from koru.bootstrap import import_flat_pipeline


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


