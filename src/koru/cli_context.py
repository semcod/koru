import argparse
import asyncio
import os
import sys
import json
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


