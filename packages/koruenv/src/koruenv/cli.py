"""CLI for lane-scoped Koru environment control (koruenv)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Sequence

from koruenv.lane import build_lane_environ


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koruenv")
    sub = parser.add_subparsers(dest="command", required=True)

    p_env = sub.add_parser("env", help="emit lane env exports")
    p_env.add_argument("ide")
    p_env.add_argument("instance")
    p_env.add_argument(
        "--shell",
        choices=("bash", "sh", "zsh", "powershell"),
        default="bash",
        help="output format for export statements",
    )

    p_run = sub.add_parser("run", help="run command in lane environment")
    p_run.add_argument("ide")
    p_run.add_argument("instance")
    p_run.add_argument("rest", nargs=argparse.REMAINDER)

    p_status = sub.add_parser("status", help="run `koru autopilot status --explain` in lane")
    p_status.add_argument("ide")
    p_status.add_argument("instance")
    p_status.add_argument(
        "--koru-cmd",
        default="koru",
        help="koru executable or command name (default: koru)",
    )
    return parser


def _render_exports(env_overlay: dict[str, str], *, shell: str) -> str:
    lines: list[str] = []
    if shell in {"bash", "sh", "zsh"}:
        for key, value in env_overlay.items():
            lines.append(f"export {key}={value}")
        return "\n".join(lines)
    for key, value in env_overlay.items():
        lines.append(f"$env:{key} = '{value}'")
    return "\n".join(lines)


def _strip_double_dash(rest: Sequence[str]) -> list[str]:
    parts = list(rest)
    if parts and parts[0] == "--":
        return parts[1:]
    return parts


def _run_with_overlay(argv: Sequence[str], overlay: dict[str, str]) -> int:
    env = os.environ.copy()
    env.update(overlay)
    try:
        proc = subprocess.run(list(argv), env=env, check=False)
    except KeyboardInterrupt:
        return 130
    return int(proc.returncode)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        env_overlay = build_lane_environ(ide=args.ide, instance=args.instance)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "env":
        print(_render_exports(env_overlay, shell=args.shell))
        return 0

    if args.command == "status":
        command = [args.koru_cmd, "autopilot", "status", "--explain"]
        return _run_with_overlay(command, env_overlay)

    rest = _strip_double_dash(args.rest)
    if not rest:
        print("error: run requires '-- <command> [args...]'", file=sys.stderr)
        return 2
    return _run_with_overlay(rest, env_overlay)


if __name__ == "__main__":
    raise SystemExit(main())
