"""CLI for uri2coru."""

from __future__ import annotations

import argparse
import json
import sys

from uri2coru.decode import uri_to_dsl
from uri2coru.nlp2uri import nlp2uri
from uri2coru.run import run_uri


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="coru:// URI → dsl2coru")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dec = sub.add_parser("decode", help="URI → DSL line")
    dec.add_argument("--uri", required=True)
    dec.add_argument("--file", default=".")

    run = sub.add_parser("run", help="URI → dispatch")
    run.add_argument("--uri", required=True)
    run.add_argument("--file", default=".")
    run.add_argument("--json", action="store_true")

    resolve = sub.add_parser("resolve", help="NL → coru:// URIs (nlp2uri)")
    resolve.add_argument("prompt")
    resolve.add_argument("--file", default=".")
    resolve.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "decode":
        print(uri_to_dsl(args.uri, default_file=args.file))
        return 0

    if args.cmd == "run":
        result = run_uri(args.uri, default_file=args.file)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if result.error:
                print(f"error: {result.error}", file=sys.stderr)
            if result.output:
                print(result.output.rstrip())
        return 0 if result.ok else 1

    if args.cmd == "resolve":
        hits = nlp2uri(args.prompt, default_file=args.file)
        if args.json:
            print(json.dumps([h.to_dict() for h in hits], indent=2, ensure_ascii=False))
        else:
            for hit in hits:
                print(f"{hit.confidence:.2f}  {hit.uri}  {hit.dsl}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
