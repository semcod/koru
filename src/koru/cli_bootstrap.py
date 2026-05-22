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


def _bootstrap_main(args: argparse.Namespace) -> int:
    emit_management_event(
        tool="koru.bootstrap",
        action="started",
        status="running",
        message=str(args.from_file or ""),
        queue=args.queue_name,
        details={"project": str(args.project), "sprint": args.sprint},
    )
    if args.from_file is None:
        parser = _build_parser()
        parser.error("--bootstrap requires --from PATH")
    try:
        report = import_flat_pipeline(
            args.from_file,
            args.project,
            sprint=args.sprint,
            overwrite=args.force,
        )
    except FileExistsError as exc:
        print(f"koru bootstrap: {exc}")
        emit_management_event(
            tool="koru.bootstrap",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"koru bootstrap: {exc}")
        emit_management_event(
            tool="koru.bootstrap",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 2
    print("koru bootstrap: ✓ imported")
    print(report.summary())
    emit_management_event(
        tool="koru.bootstrap",
        action="completed",
        status="completed",
        message=report.summary(),
        queue=args.queue_name,
        details={"project": str(args.project), "sprint": args.sprint},
    )
    return 0


