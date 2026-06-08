"""CLI for uri2koru."""

from __future__ import annotations

import argparse
import json
import sys

from uri2koru.decode import uri_to_dsl
from uri2koru.nlp2uri import nlp2uri
from uri2koru.run import run_uri


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="koru:// URI → dsl2koru")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dec = sub.add_parser("decode", help="URI → DSL line")
    dec.add_argument("--uri", required=True)

    run = sub.add_parser("run", help="URI → dispatch")
    run.add_argument("--uri", required=True)
    run.add_argument("--project", default=".")
    run.add_argument("--json", action="store_true")

    resolve = sub.add_parser("resolve", help="NL → koru:// URIs (nlp2uri)")
    resolve.add_argument("prompt")
    resolve.add_argument("--project", default=".")
    resolve.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "decode":
        print(uri_to_dsl(args.uri, default_project=args.project if hasattr(args, "project") else None))
        return 0

    if args.cmd == "run":
        result = run_uri(args.uri, default_project=args.project)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if result.error:
                print(f"error: {result.error}", file=sys.stderr)
            if result.output:
                print(result.output.rstrip())
        return 0 if result.ok else 1

    if args.cmd == "resolve":
        hits = nlp2uri(args.prompt, project=args.project)
        if args.json:
            print(json.dumps([h.to_dict() for h in hits], indent=2, ensure_ascii=False))
        else:
            for hit in hits:
                print(f"{hit.confidence:.2f}  {hit.uri}  {hit.dsl}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
