"""CLI helpers for ``koru agent``."""


import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from koru.agents import (
    agent_lane_environment,
    detect_agent_options,
    format_agent_lane_exports,
    launch_agent,
    save_agent_prompt,
    select_agent,
)
from koru.context import build_context, render_markdown_handoff


def try_agent_env_exports(args: Namespace) -> int | None:
    """Handle ``--env-json`` / ``--env-exports``; return exit code or None."""
    if not (args.env_json or args.env_exports):
        return None
    lane = (args.lane_id or args.agent_id or "").strip()
    if not lane:
        print(
            "koru agent: --env-exports / --env-json require --lane or --agent <id>",
            file=sys.stderr,
        )
        return 2
    env_map = agent_lane_environment(lane)
    if args.env_json:
        print(json.dumps(env_map, indent=2, sort_keys=True))
    else:
        print(format_agent_lane_exports(env_map), end="")
    return 0


def print_agent_list(args: Namespace, agents: list[Any]) -> None:
    if args.output_format == "json":
        available_ct = sum(1 for a in agents if a.available)
        launchable_ct = sum(1 for a in agents if a.launchable)
        print(
            json.dumps(
                {
                    "summary": {
                        "total": len(agents),
                        "available": available_ct,
                        "launchable": launchable_ct,
                        "ready": launchable_ct > 0,
                    },
                    "agents": [agent.to_dict() for agent in agents],
                },
                indent=2,
                sort_keys=True,
            ),
        )
        return
    for agent in agents:
        marker = "✓" if agent.available else "·"
        launch = "launchable" if agent.launchable else "manual"
        print(f"{marker} {agent.id:<14} {launch:<10} {agent.reason}")


def run_agent_handoff(project: Path, args: Namespace) -> int:
    ctx = build_context(
        project=project,
        ticket_id=args.ticket,
        queue_name=args.queue_name,
    )
    prompt = render_markdown_handoff(ctx)
    if not args.launch:
        save_path = save_agent_prompt(project, prompt)
        print(prompt)
        print(f"\nPrompt saved: {save_path}")
        return 0
    agents = detect_agent_options(project)
    agent = select_agent(
        agents,
        agent_id=args.agent_id,
        interactive=sys.stdin.isatty(),
    )
    if agent is None:
        print("koru agent: no matching agent detected. Use `koru agent --list`.")
        return 2
    return launch_agent(agent, project, prompt)
