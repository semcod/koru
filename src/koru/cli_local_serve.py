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


def _build_local_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru local-serve",
        description=(
            "Minimal localhost JSON/NDJSON hub for scripts and HTTP clients "
            "(see docs/local-service.md)."
        ),
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Bind address (default: KORU_LOCAL_SERVICE_HOST or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "TCP port (default: KORU_LOCAL_SERVICE_PORT or 18766). "
            "Use 0 for an ephemeral OS-assigned port."
        ),
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Ring buffer size (default: KORU_LOCAL_SERVICE_MAX_EVENTS or 256).",
    )
    return parser


def _local_serve_main(argv: list[str]) -> int:
    from koruapi.local import local_main

    return local_main(argv)


