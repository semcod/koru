"""Argparse helpers for ``koru vision``."""

from __future__ import annotations

import argparse
from pathlib import Path


def register_mesh_publish_args(parser: argparse.ArgumentParser, *, agent: bool = False) -> None:
    if agent:
        parser.add_argument("--publish-mesh", action="store_true", default=None)
        parser.add_argument("--no-publish-mesh", dest="publish_mesh", action="store_false")
    else:
        parser.add_argument("--publish-mesh", action="store_true")
    parser.add_argument("--mesh-url", default=None)
    parser.add_argument("--peer-id", default=None)
    parser.add_argument("--key-file", type=Path, default=None)


def _add_capture_subparser(sub: argparse._SubParsersAction) -> None:
    once = sub.add_parser("capture")
    once.add_argument("--monitor", type=int, default=None, help="Monitor index (auto by default).")
    register_mesh_publish_args(once)


def _add_agent_subparser(sub: argparse._SubParsersAction) -> None:
    agent = sub.add_parser("agent")
    agent.add_argument("--monitor", type=int, default=None, help="Monitor index (auto = all).")
    agent.add_argument("--interval", type=float, default=None, help="Capture interval seconds (minimum 30).")
    agent.add_argument("--max-frames", type=int, default=None)
    register_mesh_publish_args(agent, agent=True)


def build_vision_parser() -> argparse.ArgumentParser:
    """Build the ``koru vision`` argparse tree (capture + agent subcommands)."""
    parser = argparse.ArgumentParser(prog="koru vision", description="Capture monitors for observation mesh.")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    _add_capture_subparser(sub)
    _add_agent_subparser(sub)
    return parser
