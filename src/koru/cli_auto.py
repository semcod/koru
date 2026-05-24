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



def _legacy_attr(name: str, fallback):
    legacy = sys.modules.get("koru._legacy_cli_impl")
    return getattr(legacy, name, fallback) if legacy is not None else fallback


def _peek_project_from_argv(argv: list[str]) -> Path:
    for idx, part in enumerate(argv):
        if part == "--project" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def _should_suggest_wizard(argv: list[str], project: Path) -> bool:
    if argv:
        return False
    if os.environ.get("KORU_AUTO_SKIP_WIZARD", "").strip().lower() in {"1", "true", "yes"}:
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    return not (project / ".planfile").exists() and not (project / ".koru").exists()


def _auto_main(argv: list[str]) -> int:
    """``koru auto``: stop prior autonomous/auto loops, then start with ``--replace-existing``.

    On a brand-new project (no ``.planfile``, interactive TTY, no args) we
    suggest running ``koru wizard`` first so the user can pick a strategy
    instead of blindly entering the autonomous loop with an empty backlog.
    """
    from koru.cli import _peek_project_from_argv, _should_suggest_wizard
    # ``koru auto up`` is equivalent to ``koru auto``; argv normalization injects
    # the ``up`` subcommand once — a redundant token here becomes a duplicate.
    if argv and argv[0] == "up":
        argv = argv[1:]
    if any(arg in {"-h", "--help"} for arg in argv):
        return autonomous_main(argv, invoked_as_auto=True)
    project = _peek_project_from_argv(argv)
    if _should_suggest_wizard(argv, project):
        print(
            "koru auto: no .planfile detected — recommended first step is "
            "`koru wizard` to pick a strategy and seed the first ticket.",
            file=sys.stderr,
        )
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            print(
                "  GUI: `koru wizard --gui` opens a browser wizard "
                "(requires pip install 'koru[api]').",
                file=sys.stderr,
            )
        print("(skip with KORU_AUTO_SKIP_WIZARD=1 or run `koru auto --allow-duplicate`)", file=sys.stderr)
    if "--allow-duplicate" not in argv:
        stdio = os.environ.get("KORU_STDIO_FORMAT", "human")
        stop_prior = _legacy_attr(
            "stop_prior_autonomous_for_auto_start",
            stop_prior_autonomous_for_auto_start,
        )
        stop_prior(project, stdio_format=stdio)
    if "--replace-existing" not in argv and "--allow-duplicate" not in argv:
        argv = ["--replace-existing", *argv]
    run_autonomous = _legacy_attr("autonomous_main", autonomous_main)
    return run_autonomous(argv, invoked_as_auto=True)
