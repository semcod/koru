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


def _refactor_planfile_handoff_main(argv: list[str]) -> int:
    """CLI: ``koru refactor-planfile-handoff`` — markdown for IDE chat (planfile tickets)."""
    import argparse

    from koru.refactor_planfile_handoff import render_planfile_refactor_handoff

    p = argparse.ArgumentParser(
        prog="koru refactor-planfile-handoff",
        description=(
            "Print markdown instructions for attaching project/analysis.toon.yaml "
            "and drafting planfile refactor tickets in the IDE chat."
        ),
    )
    p.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    args = p.parse_args(argv)
    print(render_planfile_refactor_handoff(args.project), end="")
    return 0


