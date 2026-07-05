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


def ide_router_main(argv: list[str]) -> int:
    """CLI: ``koru ide-router`` — print resolved IDE / headless routing."""
    import json

    from koru.ide_router import resolve_ide_route

    p = argparse.ArgumentParser(prog="koru ide-router")
    p.add_argument(
        "--cli-ide",
        default="auto",
        help="Preview merge as if autonomous passed --autopilot-ide (default: auto).",
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="text lines (default) or json for scripts",
    )
    args = p.parse_args(argv)
    route = resolve_ide_route(cli_autopilot_ide=args.cli_ide)
    payload = {
        "autopilot_ide": route.autopilot_ide,
        "headless": route.headless,
        "primary_surface": route.primary_surface,
        "recommend_mcp": route.recommend_mcp,
        "recommend_autopilot_drive": route.recommend_autopilot_drive,
        "notes": route.notes,
    }
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    else:
        for key, val in payload.items():
            print(f"{key}: {val}")
    return 0


