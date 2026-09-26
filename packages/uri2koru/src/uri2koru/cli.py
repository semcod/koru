"""CLI for uri2koru."""

from __future__ import annotations

import argparse
import json
import sys

from uri2koru.decode import uri_to_dsl
from uri2koru.nlp2uri import nlp2uri
from uri2koru.run import run_uri


def _add_decode(sub: argparse._SubParsersAction) -> None:
    dec = sub.add_parser("decode", help="URI → DSL line")
    dec.add_argument("--uri", required=True)


def _add_run(sub: argparse._SubParsersAction) -> None:
    run = sub.add_parser("run", help="URI → dispatch")
    run.add_argument("--uri", required=True)
    run.add_argument("--project", default=".")
    run.add_argument("--json", action="store_true")


def _add_resolve(sub: argparse._SubParsersAction) -> None:
    resolve = sub.add_parser("resolve", help="NL → koru:// URIs (nlp2uri)")
    resolve.add_argument("prompt")
    resolve.add_argument("--project", default=".")
    resolve.add_argument("--json", action="store_true")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="koru:// URI → dsl2koru")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_decode(sub)
    _add_run(sub)
    _add_resolve(sub)
    return parser


def _cmd_decode(args: argparse.Namespace) -> int:
    print(uri_to_dsl(args.uri, default_project=getattr(args, "project", None)))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    result = run_uri(args.uri, default_project=args.project)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.ok else 1
    if result.error:
        print(f"error: {result.error}", file=sys.stderr)
    if result.output:
        print(result.output.rstrip())
    return 0 if result.ok else 1


def _cmd_resolve(args: argparse.Namespace) -> int:
    hits = nlp2uri(args.prompt, project=args.project)
    if args.json:
        print(json.dumps([h.to_dict() for h in hits], indent=2, ensure_ascii=False))
    else:
        for hit in hits:
            print(f"{hit.confidence:.2f}  {hit.uri}  {hit.dsl}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "decode":
        return _cmd_decode(args)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "resolve":
        return _cmd_resolve(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
