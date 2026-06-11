"""CLI shell for dsl2coru."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cli2coru.shell import run_shell
from dsl2coru.bus import dispatch, execute_dsl


def _print_result(result: Any, json_out: bool) -> None:
    if json_out:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        if result.error:
            print(f"error: {result.error}", file=sys.stderr)
        if result.output:
            print(result.output.rstrip())


def _handle_shell(args: argparse.Namespace) -> int:
    return run_shell(default_project=args.file, json_out=args.json)


def _handle_run(args: argparse.Namespace) -> int:
    results = execute_dsl(Path(args.script).read_text(encoding="utf-8"), default_project=args.file)
    code = 0
    for result in results:
        _print_result(result, args.json)
        if not result.ok:
            code = 1
    return code


def _handle_exec(args: argparse.Namespace) -> int:
    result = dispatch(args.command, default_project=args.file)
    _print_result(result, args.json)
    return 0 if result.ok else 1


_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "shell": _handle_shell,
    "run": _handle_run,
    "exec": _handle_exec,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cli2coru — shell for dsl2coru")
    sub = parser.add_subparsers(dest="cmd")

    shell = sub.add_parser("shell", help="Interactive REPL")
    shell.add_argument("--file", default=".")
    shell.add_argument("--json", action="store_true")

    run = sub.add_parser("run", help="Run .dsl script")
    run.add_argument("script")
    run.add_argument("--file", default=".")
    run.add_argument("--json", action="store_true")

    exe = sub.add_parser("exec", help="Execute one DSL command")
    exe.add_argument("command")
    exe.add_argument("--file", default=".")
    exe.add_argument("--json", action="store_true")

    args = parser.parse_args(argv or sys.argv[1:])
    cmd = args.cmd or "shell"

    handler = _HANDLERS.get(cmd)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
