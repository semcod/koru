import argparse
import asyncio  # noqa: F401
import json
import os  # noqa: F401
import sys  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Any  # noqa: F401

from koru.agents import detect_agent_options  # noqa: F401
from koru.autonomous import autonomous_main, stop_prior_autonomous_for_auto_start  # noqa: F401
from koru.bootstrap import import_flat_pipeline  # noqa: F401
from koru.context import build_context, render_markdown_handoff
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


def _context_main(args: argparse.Namespace) -> int:
    ctx = build_context(
        project=args.project,
        ticket_id=args.ticket,
        queue_name=args.queue_name,
        include_fixtures=getattr(args, "include_fixtures", None),
    )
    if args.output_format == "markdown":
        print(render_markdown_handoff(ctx))
    else:
        print(json.dumps(ctx, indent=2, sort_keys=True))
    return 0


