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


def _build_runtime_context_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru runtime-context",
        description=(
            "Show the current project runtime context: systems, libraries, "
            "algorithms, APIs, applications, pipelines, and topology."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
        help="Output format (default json).",
    )
    return parser


def _render_runtime_context_text(context: dict[str, Any]) -> str:
    summary = context.get("summary") or {}
    lines = [
        f"koru runtime-context: {summary.get('project') or context.get('project_root')}",
        f"  version: {summary.get('version') or '-'}",
        f"  services: {summary.get('services', 0)}",
        f"  workspaces: {summary.get('workspaces', 0)}",
        f"  pipelines: {summary.get('pipelines', 0)}",
        f"  topology nodes: {summary.get('topology_nodes', 0)}",
        "",
        "Systems:",
    ]
    for service in context.get("systems") or []:
        ports = ", ".join(service.get("ports") or []) or "-"
        files = ", ".join(service.get("compose_files") or []) or "-"
        lines.append(f"  {service.get('name')}: ports={ports} compose={files}")
    lines.append("")
    lines.append("Pipelines:")
    for pipeline in context.get("pipelines") or []:
        mode = "interactive" if pipeline.get("interactive") else "batch"
        lines.append(f"  {pipeline.get('name')}: {mode} — {pipeline.get('description') or '-'}")
    return "\n".join(lines)


def _runtime_context_main(argv: list[str]) -> int:
    args = _build_runtime_context_parser().parse_args(argv)
    try:
        from planfile.runtime_context import build_runtime_context
    except ImportError as exc:
        print(
            "koru runtime-context: planfile.runtime_context is not available. "
            "Install/update semcod/planfile or add it to PYTHONPATH.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    context = build_runtime_context(args.project)
    if args.output_format == "text":
        print(_render_runtime_context_text(context))
    else:
        print(json.dumps(context, indent=2, sort_keys=True, default=str))
    return 0


