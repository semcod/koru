"""Canonical CLI for the Koru and compatibility Coru DSL dialects."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from dsl2koru.bus import dispatch, execute_dsl
from dsl2koru.codec import envelope_from_bytes, envelope_to_bytes, parse_text, roundtrip_text
from dsl2koru.events import EventStore
from dsl2koru.schema_registry import validate_schemas

Dialect = Literal["native", "compat"]
ArgumentSpec = tuple[tuple[str, ...], dict[str, Any]]
SubcommandSpec = tuple[str, str | None, list[ArgumentSpec]]


class _ContextAction(argparse.Action):
    def __call__(
        self,
        _parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        del option_string
        setattr(namespace, self.dest, values)
        namespace._context_explicit = self.dest


_SUBCOMMAND_SPECS: list[SubcommandSpec] = [
    ("validate-schema", None, []),
    (
        "encode",
        None,
        [
            (("line",), {}),
            (("--project",), {"default": ".", "action": _ContextAction}),
            (("--file",), {"default": "", "action": _ContextAction}),
            (("--format",), {"choices": ["protobuf", "json"], "default": "protobuf"}),
            (("--output",), {}),
        ],
    ),
    (
        "decode",
        None,
        [
            (("--input",), {"required": True}),
            (("--format",), {"choices": ["protobuf", "json"], "default": "protobuf"}),
        ],
    ),
    (
        "roundtrip",
        None,
        [
            (("line",), {}),
            (("--project",), {"default": ".", "action": _ContextAction}),
            (("--file",), {"default": "", "action": _ContextAction}),
        ],
    ),
    (
        "replay",
        None,
        [
            (("--project",), {"default": ".", "action": _ContextAction}),
            (("--file",), {"default": ".", "action": _ContextAction}),
            (("--format",), {"choices": ["jsonl", "protobuf", "auto"], "default": "auto"}),
        ],
    ),
    (
        "run",
        None,
        [
            (("script",), {"nargs": "?"}),
            (("-c", "--command"), {}),
            (("--project",), {"default": ".", "action": _ContextAction}),
            (("--file",), {"default": "", "action": _ContextAction}),
            (("--json",), {"action": "store_true"}),
        ],
    ),
    (
        "exec",
        "Execute one DSL line (alias for run -c)",
        [
            (("command",), {}),
            (("--project",), {"default": ".", "action": _ContextAction}),
            (("--file",), {"default": "", "action": _ContextAction}),
            (("--json",), {"action": "store_true"}),
        ],
    ),
]
_SUBCOMMANDS = frozenset(spec[0] for spec in _SUBCOMMAND_SPECS)


def _console_dialect(program: str) -> Dialect:
    path = Path(program)
    return "compat" if path.name.startswith("dsl2coru") or "dsl2coru" in path.parts else "native"


def _program_name(program: str, dialect: Dialect) -> str:
    name = Path(program).name
    if name in {"cli.py", "__main__.py"}:
        return "dsl2coru" if dialect == "compat" else "dsl2koru"
    return name or ("dsl2coru" if dialect == "compat" else "dsl2koru")


def _run_results(results: list[Any], *, json_out: bool) -> int:
    code = 0
    for result in results:
        if json_out:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if result.error:
                print(f"error: {result.error}", file=sys.stderr)
            if result.output:
                print(result.output.rstrip())
        if not result.ok:
            code = 1
    return code


def main(argv: list[str] | None = None) -> int:
    raw = argv if argv is not None else sys.argv[1:]
    dialect = _console_dialect(sys.argv[0])
    if raw and raw[0] in _SUBCOMMANDS:
        return _main_subcommand(raw, dialect=dialect)
    return _main_legacy(raw, dialect=dialect)


def _build_subcommand_parser(
    *,
    program: str = "dsl2koru",
    dialect: Dialect | None = None,
) -> argparse.ArgumentParser:
    selected = dialect or _console_dialect(program)
    parser = argparse.ArgumentParser(prog=_program_name(program, selected))
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, help_text, argument_specs in _SUBCOMMAND_SPECS:
        sub_parser = sub.add_parser(name, help=help_text)
        sub_parser.set_defaults(_dialect=selected)
        for flags, kwargs in argument_specs:
            sub_parser.add_argument(*flags, **kwargs)
    return parser


def _main_subcommand(argv: list[str], *, dialect: Dialect) -> int:
    parser = _build_subcommand_parser(program=sys.argv[0], dialect=dialect)
    return _handle_subcommand(parser.parse_args(argv))


def _build_legacy_parser(dialect: Dialect) -> argparse.ArgumentParser:
    compatibility = dialect == "compat"
    parser = argparse.ArgumentParser(
        prog="dsl2coru" if compatibility else "dsl2koru",
        description=(
            "CORU control DSL (STATUS, AUTO, LANE, …)"
            if compatibility
            else "Koru control DSL (QUERY_REPAIR_HISTORY, REPAIR_RUN, …)"
        ),
    )
    parser.add_argument("script", nargs="?", help="Optional .dsl script file")
    parser.add_argument("-c", "--command", help="Execute single DSL command")
    parser.add_argument("--project", default=".", action=_ContextAction, help="Default project root")
    parser.add_argument("--file", default="", action=_ContextAction, help="Default file context")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(_dialect=dialect)
    return parser


def _main_legacy(argv: list[str], *, dialect: Dialect) -> int:
    parser = _build_legacy_parser(dialect)
    args = parser.parse_args(argv)
    if args.command:
        return _run_results([dispatch(args.command, **_context_kwargs(args))], json_out=args.json)
    if args.script:
        text = Path(args.script).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
        if not text.strip():
            parser.print_help()
            return 1
    return _run_results(execute_dsl(text, **_context_kwargs(args)), json_out=args.json)


def _selected_context(args: argparse.Namespace) -> tuple[Dialect, str]:
    explicit = getattr(args, "_context_explicit", None)
    if explicit == "file":
        return "compat", str(args.file)
    if explicit == "project":
        return "native", str(args.project)
    if getattr(args, "file", ""):
        dialect: Dialect = getattr(args, "_dialect", "native")
        if dialect == "compat":
            return dialect, str(args.file)
    if getattr(args, "project", ".") != ".":
        return "native", str(args.project)
    dialect: Dialect = getattr(args, "_dialect", "native")
    return (dialect, "" if dialect == "compat" else ".")


def _context_kwargs(args: argparse.Namespace) -> dict[str, str | None]:
    dialect, context = _selected_context(args)
    if dialect == "compat":
        return {"default_file": context or None}
    return {"default_project": context or "."}


def _cmd_validate_schema(_args: argparse.Namespace) -> int:
    errors = validate_schemas()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("schema OK")
    return 0


def _cmd_encode(args: argparse.Namespace) -> int:
    kwargs = _context_kwargs(args)
    payload = parse_text(args.line, **kwargs)
    if args.format == "json":
        from dsl2koru.codec import envelope_to_json

        data = envelope_to_json(payload)
    else:
        data = envelope_to_bytes(
            payload,
            default_project=str(kwargs.get("default_project") or ""),
            default_file=str(kwargs.get("default_file") or ""),
        )
    if args.output:
        Path(args.output).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    raw = Path(args.input).read_bytes()
    if args.format == "json":
        from dsl2koru.codec import envelope_from_json

        payload = envelope_from_json(raw)
    else:
        payload = envelope_from_bytes(raw)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    print(roundtrip_text(args.line, **_context_kwargs(args)))
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    dialect, context = _selected_context(args)
    store = (
        EventStore.for_default(context or None)
        if dialect == "compat"
        else EventStore.for_project(Path(context or "."))
    )
    if args.format == "protobuf":
        events = store.replay_pb()
    elif args.format == "jsonl":
        events = store.read_all()
    else:
        events = store.replay()
    for event in events:
        print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    kwargs = _context_kwargs(args)
    if args.command:
        results = [dispatch(args.command, **kwargs)]
    elif args.script:
        results = execute_dsl(Path(args.script).read_text(encoding="utf-8"), **kwargs)
    else:
        results = execute_dsl(sys.stdin.read(), **kwargs)
    return _run_results(results, json_out=args.json)


def _cmd_exec(args: argparse.Namespace) -> int:
    return _run_results([dispatch(args.command, **_context_kwargs(args))], json_out=args.json)


_SUBCOMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "validate-schema": _cmd_validate_schema,
    "encode": _cmd_encode,
    "decode": _cmd_decode,
    "roundtrip": _cmd_roundtrip,
    "replay": _cmd_replay,
    "run": _cmd_run,
    "exec": _cmd_exec,
}


def _handle_subcommand(args: argparse.Namespace) -> int:
    handler = _SUBCOMMAND_HANDLERS.get(args.cmd)
    return handler(args) if handler else 1


if __name__ == "__main__":
    raise SystemExit(main())
