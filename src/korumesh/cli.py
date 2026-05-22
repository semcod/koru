"""CLI entry for ``koru mesh``."""

from __future__ import annotations

import sys

from korumesh.cli_commands import mesh_init, mesh_publish, mesh_relay
from korumesh.cli_parser import build_mesh_parser
from korumesh.keys import load_mesh_key


def mesh_main(argv: list[str] | None = None) -> int:
    args = build_mesh_parser().parse_args(argv)
    command = args.command
    if command == "init":
        return mesh_init(args)
    try:
        key = load_mesh_key(args.key_file)
    except (OSError, ValueError) as exc:
        print(f"koru mesh: {exc}", file=sys.stderr)
        return 2
    if command == "relay":
        return mesh_relay(args, key)
    if command == "publish":
        return mesh_publish(args, key)
    print(f"koru mesh: unknown command {command!r}", file=sys.stderr)
    return 2
