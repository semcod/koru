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


def ide_router_main(argv: list[str]) -> int:
    """CLI: ``koru ide-router`` — print resolved IDE / headless routing."""
    import argparse
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


