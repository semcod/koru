"""Canonical CLI for the Koru and compatibility Coru DSL dialects."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from dsl2koru.bus import dispatch, execute_dsl
from dsl2koru.codec import (
    envelope_from_bytes,
    envelope_from_json,
    envelope_to_bytes,
    envelope_to_json,
    parse_text,
    roundtrip_text,
)
from dsl2koru.events import EventStore
from dsl2koru.schema_registry import validate_schemas

Dialect = Literal["native", "compat"]
ArgumentSpec = tuple[tuple[str, ...], dict[str, Any]]


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


def _arg(*flags: str, **kwargs: Any) -> ArgumentSpec:
    return flags, kwargs


def _context_specs(*, documented: bool = False, file_default: str = "") -> tuple[ArgumentSpec, ...]:
    help_text = ({"help": "Default project root"}, {"help": "Default file context"}) if documented else ({}, {})
    return (
        _arg("--project", default=".", action=_ContextAction, **help_text[0]),
        _arg("--file", default=file_default, action=_ContextAction, **help_text[1]),
    )


_JSON = _arg("--json", action="store_true")
_PROTOBUF_FORMAT = _arg("--format", choices=["protobuf", "json"], default="protobuf")


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
        parser = _build_subcommand_parser(program=sys.argv[0], dialect=dialect)
        args = parser.parse_args(raw)
        return args._handler(args)
    parser = _build_legacy_parser(dialect)
    return _execute_input(parser.parse_args(raw), empty_parser=parser)


def _add_arguments(parser: argparse.ArgumentParser, specs: Sequence[ArgumentSpec]) -> None:
    for flags, kwargs in specs:
        parser.add_argument(*flags, **kwargs)


def _build_subcommand_parser(
    *,
    program: str = "dsl2koru",
    dialect: Dialect | None = None,
) -> argparse.ArgumentParser:
    selected = dialect or _console_dialect(program)
    parser = argparse.ArgumentParser(prog=_program_name(program, selected))
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, help_text, handler, specs in _SUBCOMMAND_SPECS:
        sub_parser = sub.add_parser(name, help=help_text)
        sub_parser.set_defaults(_dialect=selected, _handler=handler)
        _add_arguments(sub_parser, specs)
    return parser


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
    _add_arguments(
        parser,
        (
            _arg("script", nargs="?", help="Optional .dsl script file"),
            _arg("-c", "--command", help="Execute single DSL command"),
            *_context_specs(documented=True),
            _JSON,
        ),
    )
    parser.set_defaults(_dialect=dialect)
    return parser


def _selected_context(args: argparse.Namespace) -> tuple[Dialect, str]:
    dialect: Dialect = getattr(args, "_dialect", "native")
    explicit = getattr(args, "_context_explicit", None)
    if explicit:
        return ("compat" if explicit == "file" else "native"), str(getattr(args, explicit))
    file = getattr(args, "file", "")
    if dialect == "compat" and file:
        return dialect, str(file)
    project = getattr(args, "project", ".")
    if project != ".":
        return "native", str(project)
    return dialect, "" if dialect == "compat" else "."


def _context_kwargs(args: argparse.Namespace) -> dict[str, str | None]:
    dialect, context = _selected_context(args)
    return {"default_file": context or None} if dialect == "compat" else {"default_project": context or "."}


def _execute_input(
    args: argparse.Namespace,
    *,
    empty_parser: argparse.ArgumentParser | None = None,
) -> int:
    kwargs = _context_kwargs(args)
    if args.command:
        results = [dispatch(args.command, **kwargs)]
    elif args.script:
        results = execute_dsl(Path(args.script).read_text(encoding="utf-8"), **kwargs)
    else:
        text = sys.stdin.read()
        if empty_parser and not text.strip():
            empty_parser.print_help()
            return 1
        results = execute_dsl(text, **kwargs)
    return _run_results(results, json_out=args.json)


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
    data = (
        envelope_to_json(payload)
        if args.format == "json"
        else envelope_to_bytes(
            payload,
            default_project=str(kwargs.get("default_project") or ""),
            default_file=str(kwargs.get("default_file") or ""),
        )
    )
    if args.output:
        Path(args.output).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    raw = Path(args.input).read_bytes()
    payload = envelope_from_json(raw) if args.format == "json" else envelope_from_bytes(raw)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    print(roundtrip_text(args.line, **_context_kwargs(args)))
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    dialect, context = _selected_context(args)
    store = (
        EventStore.for_default(context or None) if dialect == "compat" else EventStore.for_project(Path(context or "."))
    )
    replay = {"protobuf": store.replay_pb, "jsonl": store.read_all, "auto": store.replay}[args.format]
    for event in replay():
        print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    return _execute_input(args)


def _cmd_exec(args: argparse.Namespace) -> int:
    return _run_results([dispatch(args.command, **_context_kwargs(args))], json_out=args.json)


def _command(
    name: str,
    handler: Any,
    *specs: ArgumentSpec,
    help_text: str | None = None,
) -> tuple[str, str | None, Any, tuple[ArgumentSpec, ...]]:
    return name, help_text, handler, specs


_SUBCOMMAND_SPECS = (
    _command("validate-schema", _cmd_validate_schema),
    _command("encode", _cmd_encode, _arg("line"), *_context_specs(), _PROTOBUF_FORMAT, _arg("--output")),
    _command("decode", _cmd_decode, _arg("--input", required=True), _PROTOBUF_FORMAT),
    _command("roundtrip", _cmd_roundtrip, _arg("line"), *_context_specs()),
    _command(
        "replay",
        _cmd_replay,
        *_context_specs(file_default="."),
        _arg("--format", choices=["jsonl", "protobuf", "auto"], default="auto"),
    ),
    _command("run", _cmd_run, _arg("script", nargs="?"), _arg("-c", "--command"), *_context_specs(), _JSON),
    _command(
        "exec",
        _cmd_exec,
        _arg("command"),
        *_context_specs(),
        _JSON,
        help_text="Execute one DSL line (alias for run -c)",
    ),
)
_SUBCOMMANDS = frozenset(spec[0] for spec in _SUBCOMMAND_SPECS)


if __name__ == "__main__":
    raise SystemExit(main())
