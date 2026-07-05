import argparse
import asyncio  # noqa: F401
import os  # noqa: F401
import sys  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Any  # noqa: F401

from koru.agents import detect_agent_options  # noqa: F401
from koru.autonomous import autonomous_main, stop_prior_autonomous_for_auto_start  # noqa: F401
from koru.bootstrap import import_flat_pipeline  # noqa: F401
from koru.context import build_context, render_markdown_handoff  # noqa: F401
from koru.events import emit_management_event  # noqa: F401
from koru.serve import DEFAULT_HOST, DEFAULT_PORT  # noqa: F401
from koru.tasks import create_nl_task  # noqa: F401
from koru.tools import (
    build_tool_task_scaffold,  # noqa: F401
    detect_tools,  # noqa: F401
    find_tool_entry,  # noqa: F401
    load_tool_registry,  # noqa: F401
    render_tools_detect_text,  # noqa: F401
)


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


