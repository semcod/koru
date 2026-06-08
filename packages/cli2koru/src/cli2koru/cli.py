"""CLI shell for dsl2koru."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cli2koru.shell import run_shell
from dsl2koru.bus import dispatch, execute_dsl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cli2koru — shell for dsl2koru")
    sub = parser.add_subparsers(dest="cmd")

    shell = sub.add_parser("shell", help="Interactive REPL")
    shell.add_argument("--project", default=".")
    shell.add_argument("--json", action="store_true")

    run = sub.add_parser("run", help="Run .dsl script")
    run.add_argument("script")
    run.add_argument("--project", default=".")
    run.add_argument("--json", action="store_true")

    exe = sub.add_parser("exec", help="Execute one DSL command")
    exe.add_argument("command")
    exe.add_argument("--project", default=".")
    exe.add_argument("--json", action="store_true")

    args = parser.parse_args(argv or sys.argv[1:])
    cmd = args.cmd or "shell"

    if cmd == "shell":
        return run_shell(default_project=args.project, json_out=args.json)

    if cmd == "run":
        results = execute_dsl(Path(args.script).read_text(encoding="utf-8"), default_project=args.project)
        code = 0
        for result in results:
            if args.json:
                print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                if result.error:
                    print(f"error: {result.error}", file=sys.stderr)
                if result.output:
                    print(result.output.rstrip())
            if not result.ok:
                code = 1
        return code

    if cmd == "exec":
        result = dispatch(args.command, default_project=args.project)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if result.error:
                print(f"error: {result.error}", file=sys.stderr)
            if result.output:
                print(result.output.rstrip())
        return 0 if result.ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
