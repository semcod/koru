"""CLI wrapper for the packaged ``koru-autoloop.sh`` script."""

import argparse
import os
import re
import subprocess
import sys
from importlib import resources
from pathlib import Path

_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def _packaged_script_path() -> Path:
    return Path(resources.files("koru").joinpath("scripts/koru-autoloop.sh"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autoloop",
        description=(
            "Run the packaged unattended scan + queue + diagnostics + autopilot loop. "
            "Configuration is env-driven; pass KEY=VALUE arguments to set env for this run."
        ),
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project directory; equivalent to PROJECT=DIR for the shell loop.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Override the autoloop shell script path, useful while developing the script.",
    )
    parser.add_argument(
        "--print-script",
        action="store_true",
        help="Print the resolved shell script path and exit.",
    )
    parser.add_argument(
        "env",
        nargs="*",
        metavar="KEY=VALUE",
        help="Environment overrides for the loop, e.g. TICKET_SOURCES=all ENABLE_SCAN=true.",
    )
    return parser


def _env_from_assignments(assignments: list[str]) -> dict[str, str]:
    env = dict(os.environ)
    for item in assignments:
        if not _ENV_ASSIGNMENT_RE.match(item):
            raise ValueError(f"expected KEY=VALUE env assignment, got {item!r}")
        key, value = item.split("=", 1)
        env[key] = value
    return env


def autoloop_main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    script = (args.script or _packaged_script_path()).resolve()
    if args.print_script:
        print(script)
        return 0
    if not script.exists():
        print(f"koru autoloop: script not found: {script}", file=sys.stderr)
        return 2

    try:
        env = _env_from_assignments(list(args.env))
    except ValueError as exc:
        parser.error(str(exc))

    if args.project is not None:
        env["PROJECT"] = str(args.project)

    try:
        return subprocess.call(["bash", str(script)], env=env)
    except KeyboardInterrupt:
        return 130


__all__ = ["autoloop_main"]
