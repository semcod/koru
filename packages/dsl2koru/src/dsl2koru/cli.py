"""CLI for dsl2koru — dual mode: legacy (-c) + subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from dsl2koru.bus import dispatch, execute_dsl
from dsl2koru.codec import envelope_from_bytes, envelope_to_bytes, parse_text, roundtrip_text
from dsl2koru.events import EventStore
from dsl2koru.schema_registry import validate_schemas

_SUBCOMMANDS = {"validate-schema", "encode", "decode", "replay", "run", "roundtrip"}


def _run_results(results: list, *, json_out: bool) -> int:
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
    if raw and raw[0] in _SUBCOMMANDS:
        return _main_subcommand(raw)
    return _main_legacy(raw)


def _main_subcommand(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dsl2koru")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate-schema")

    enc = sub.add_parser("encode")
    enc.add_argument("line")
    enc.add_argument("--project", default=".")
    enc.add_argument("--format", choices=["protobuf", "json"], default="protobuf")
    enc.add_argument("--output")

    dec = sub.add_parser("decode")
    dec.add_argument("--input", required=True)
    dec.add_argument("--format", choices=["protobuf", "json"], default="protobuf")

    rt = sub.add_parser("roundtrip")
    rt.add_argument("line")
    rt.add_argument("--project", default=".")

    rep = sub.add_parser("replay")
    rep.add_argument("--project", default=".")
    rep.add_argument("--format", choices=["jsonl", "protobuf", "auto"], default="auto")

    run = sub.add_parser("run")
    run.add_argument("script", nargs="?")
    run.add_argument("-c", "--command")
    run.add_argument("--project", default=".")
    run.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    return _handle_subcommand(args)


def _main_legacy(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="dsl2koru",
        description="Koru control DSL (QUERY_REPAIR_HISTORY, REPAIR_RUN, …)",
    )
    parser.add_argument("script", nargs="?", help="Optional .dsl script file")
    parser.add_argument("-c", "--command", help="Execute single DSL command")
    parser.add_argument("--project", default=".", help="Default project root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command:
        return _run_results([dispatch(args.command, default_project=args.project)], json_out=args.json)
    if args.script:
        text = Path(args.script).read_text(encoding="utf-8")
        return _run_results(execute_dsl(text, default_project=args.project), json_out=args.json)
    text = sys.stdin.read()
    if text.strip():
        return _run_results(execute_dsl(text, default_project=args.project), json_out=args.json)
    parser.print_help()
    return 1


def _cmd_validate_schema(_args: argparse.Namespace) -> int:
    errors = validate_schemas()
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("schema OK")
    return 0


def _cmd_encode(args: argparse.Namespace) -> int:
    payload = parse_text(args.line, default_project=args.project)
    if args.format == "json":
        from dsl2koru.codec import envelope_to_json

        data = envelope_to_json(payload)
    else:
        data = envelope_to_bytes(payload, default_project=args.project)
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
    print(roundtrip_text(args.line, default_project=args.project))
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    store = EventStore.for_project(Path(args.project))
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
    if args.command:
        results = [dispatch(args.command, default_project=args.project)]
    elif args.script:
        text = Path(args.script).read_text(encoding="utf-8")
        results = execute_dsl(text, default_project=args.project)
    else:
        text = sys.stdin.read()
        results = execute_dsl(text, default_project=args.project)
    return _run_results(results, json_out=args.json)


_SUBCOMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "validate-schema": _cmd_validate_schema,
    "encode": _cmd_encode,
    "decode": _cmd_decode,
    "roundtrip": _cmd_roundtrip,
    "replay": _cmd_replay,
    "run": _cmd_run,
}


def _handle_subcommand(args: argparse.Namespace) -> int:
    handler = _SUBCOMMAND_HANDLERS.get(args.cmd)
    if handler:
        return handler(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
