"""CLI for dsl2coru — dual mode: legacy (-c) + subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dsl2coru.bus import dispatch, execute_dsl
from dsl2coru.codec import envelope_from_bytes, envelope_to_bytes, parse_text, roundtrip_text
from dsl2coru.events import EventStore
from dsl2coru.schema_registry import validate_schemas

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
    parser = argparse.ArgumentParser(prog="dsl2coru")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate-schema")

    enc = sub.add_parser("encode")
    enc.add_argument("line")
    enc.add_argument("--file", default="")
    enc.add_argument("--format", choices=["protobuf", "json"], default="protobuf")
    enc.add_argument("--output")

    dec = sub.add_parser("decode")
    dec.add_argument("--input", required=True)
    dec.add_argument("--format", choices=["protobuf", "json"], default="protobuf")

    rt = sub.add_parser("roundtrip")
    rt.add_argument("line")
    rt.add_argument("--file", default="")

    rep = sub.add_parser("replay")
    rep.add_argument("--file", default=".")
    rep.add_argument("--format", choices=["jsonl", "protobuf", "auto"], default="auto")

    run = sub.add_parser("run")
    run.add_argument("script", nargs="?")
    run.add_argument("-c", "--command")
    run.add_argument("--file", default="")
    run.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    return _handle_subcommand(args)


def _main_legacy(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="dsl2coru",
        description="CORU control DSL (STATUS, AUTO, LANE, …)",
    )
    parser.add_argument("script", nargs="?", help="Optional .dsl script file")
    parser.add_argument("-c", "--command", help="Execute single DSL command")
    parser.add_argument("--file", default="", help="Default file context")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    default_file = args.file or None
    if args.command:
        return _run_results([dispatch(args.command, default_file=default_file)], json_out=args.json)
    if args.script:
        text = Path(args.script).read_text(encoding="utf-8")
        return _run_results(execute_dsl(text, default_file=default_file), json_out=args.json)
    text = sys.stdin.read()
    if text.strip():
        return _run_results(execute_dsl(text, default_file=default_file), json_out=args.json)
    parser.print_help()
    return 1


def _handle_subcommand(args: argparse.Namespace) -> int:
    if args.cmd == "validate-schema":
        errors = validate_schemas()
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            return 1
        print("schema OK")
        return 0

    if args.cmd == "encode":
        payload = parse_text(args.line, default_file=args.file or None)
        if args.format == "json":
            from dsl2coru.codec import envelope_to_json

            data = envelope_to_json(payload)
        else:
            data = envelope_to_bytes(payload, default_file=args.file)
        if args.output:
            Path(args.output).write_bytes(data)
        else:
            sys.stdout.buffer.write(data)
        return 0

    if args.cmd == "decode":
        raw = Path(args.input).read_bytes()
        if args.format == "json":
            from dsl2coru.codec import envelope_from_json

            payload = envelope_from_json(raw)
        else:
            payload = envelope_from_bytes(raw)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "roundtrip":
        print(roundtrip_text(args.line, default_file=args.file or None))
        return 0

    if args.cmd == "replay":
        store = EventStore.for_default(args.file or None)
        if args.format == "protobuf":
            events = store.replay_pb()
        elif args.format == "jsonl":
            events = store.read_all()
        else:
            events = store.replay_pb() or store.read_all()
        for event in events:
            print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "run":
        default_file = args.file or None
        if args.command:
            results = [dispatch(args.command, default_file=default_file)]
        elif args.script:
            text = Path(args.script).read_text(encoding="utf-8")
            results = execute_dsl(text, default_file=default_file)
        else:
            text = sys.stdin.read()
            results = execute_dsl(text, default_file=default_file)
        return _run_results(results, json_out=args.json)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
