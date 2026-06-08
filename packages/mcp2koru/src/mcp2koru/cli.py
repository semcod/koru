"""MCP server CLI."""

from __future__ import annotations

import argparse
import sys

from mcp2koru.server import create_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mcp2koru MCP server")
    parser.add_argument("--name", default="koru")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve")
    sub.add_parser("server")
    args = parser.parse_args(argv or sys.argv[1:])
    if (args.cmd or "serve") in {"serve", "server"}:
        create_server(name=args.name).run()
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
