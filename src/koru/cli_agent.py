import argparse
import sys
from pathlib import Path

from koru.agents import detect_agent_options


def _detect_agent_options(project: Path):
    legacy = sys.modules.get("koru._legacy_cli_impl")
    detector = (
        getattr(legacy, "detect_agent_options", detect_agent_options)
        if legacy
        else detect_agent_options
    )
    return detector(project)


def _build_agent_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru agent",
        description="Print or launch the best available LLM/IDE handoff for this project.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument("--ticket", default=None, help="Render prompt for a specific ticket id.")
    parser.add_argument("--agent", dest="agent_id", default=None, help="Agent id to select.")
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch the selected agent if it has a CLI.",
    )
    parser.add_argument("--list", action="store_true", help="List detected agents and exit.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="With --list: machine-readable json (default: text).",
    )
    parser.add_argument(
        "--lane",
        dest="lane_id",
        default=None,
        help=(
            "Agent lane id for --env-exports / --env-json (e.g. cursor, windsurf, claude-code). "
            "Falls back to --agent when set."
        ),
    )
    parser.add_argument(
        "--env-exports",
        action="store_true",
        help=(
            "Print shell exports for KORU_AUTOPILOT_* / queue actor hints; "
            "requires --lane or --agent."
        ),
    )
    parser.add_argument(
        "--env-json",
        action="store_true",
        help="Print recommended lane env as JSON (requires --lane or --agent).",
    )
    return parser


def _agent_main(argv: list[str]) -> int:
    from koru.agent_cli_helpers import (
        print_agent_list,
        run_agent_handoff,
        try_agent_env_exports,
    )

    args = _build_agent_parser().parse_args(argv)
    project = args.project.resolve()
    env_code = try_agent_env_exports(args)
    if env_code is not None:
        return env_code
    if args.list:
        print_agent_list(args, _detect_agent_options(project))
        return 0
    return run_agent_handoff(project, args)

