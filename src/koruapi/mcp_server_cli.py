"""CLI entry point for ``koru mcp-serve``."""

from __future__ import annotations

import os
from pathlib import Path

from koruapi.mcp_server_runtime import SERVER_VERSION, run_stdio


def mcp_serve_main(argv: list[str]) -> int:
    """Entry point for ``koru mcp-serve``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="koru mcp-serve",
        description="Start the koru MCP server (stdio transport for IDE integration).",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"koru mcp-server {SERVER_VERSION}")
        return 0

    os.environ.setdefault("KORU_PROJECT_ROOT", str(args.project.resolve()))
    return run_stdio()
