"""CLI for machine-global agent availability controls."""

from __future__ import annotations

import argparse
import json
import time

from koru.agent_availability import (
    availability_registry_path,
    block_agent,
    clear_agent_block,
    get_agent_availability,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru agent-availability",
        description="Inspect or change whether Koru may drive an agent on this machine.",
    )
    commands = parser.add_subparsers(dest="command")

    status = commands.add_parser("status", help="Show effective availability.")
    status.add_argument("agent", help="Agent/IDE id, for example qoder or cursor.")
    status.add_argument("--format", choices=("text", "json"), default="text")

    block = commands.add_parser("block", help="Prevent Koru from driving an agent.")
    block.add_argument("agent")
    block.add_argument("--reason", required=True)
    block.add_argument(
        "--for-seconds",
        type=float,
        default=None,
        help="Expire the block automatically after this many seconds.",
    )

    clear = commands.add_parser("clear", help="Mark an agent operational again.")
    clear.add_argument("agent")
    return parser


def _format_text(availability) -> str:
    retry = ""
    if availability.retry_after is not None:
        remaining = max(0, round(availability.retry_after - time.time()))
        retry = f" retry_after={availability.retry_after:.3f} remaining_seconds={remaining}"
    return (
        f"agent={availability.agent_id} status={availability.status} "
        f"reason={availability.reason or '-'} source={availability.source or '-'}{retry}"
    )


def agent_availability_main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    if args.command == "block":
        availability = block_agent(
            args.agent,
            reason=args.reason,
            source="cli",
            retry_after_seconds=args.for_seconds,
        )
    elif args.command == "clear":
        availability = clear_agent_block(args.agent, source="cli")
    else:
        availability = get_agent_availability(args.agent)

    if getattr(args, "format", "text") == "json":
        payload = availability.to_dict()
        payload["registry_path"] = str(availability_registry_path())
        print(json.dumps(payload, sort_keys=True))
    else:
        print(_format_text(availability))
    return 0
