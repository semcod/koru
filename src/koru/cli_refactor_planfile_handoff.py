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
from koru.serve import DEFAULT_HOST, DEFAULT_PORT  # noqa: F401
from koru.tasks import create_nl_task  # noqa: F401
from koru.tools import (
    build_tool_task_scaffold,  # noqa: F401
    detect_tools,  # noqa: F401
    find_tool_entry,  # noqa: F401
    load_tool_registry,  # noqa: F401
    render_tools_detect_text,  # noqa: F401
)


def _refactor_planfile_handoff_main(argv: list[str]) -> int:
    """CLI: ``koru refactor-planfile-handoff`` — markdown for IDE chat (planfile tickets)."""

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


