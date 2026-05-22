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


def build_vision_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru vision", description="Capture monitors for observation mesh.")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    once = sub.add_parser("capture")
    once.add_argument("--monitor", type=int, default=0)
    register_mesh_publish_args(once)

    agent = sub.add_parser("agent")
    agent.add_argument("--monitor", type=int, default=0)
    agent.add_argument("--interval", type=float, default=None)
    agent.add_argument("--max-frames", type=int, default=None)
    register_mesh_publish_args(agent, agent=True)
    return parser
