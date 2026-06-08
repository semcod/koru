"""CLI for nlp2koru."""

from __future__ import annotations

import argparse
import json
import sys

from nlp2koru.apply import apply_nl
from nlp2koru.to_dsl import to_dsl, workflow_from_nl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NL → dsl2koru")
    sub = parser.add_subparsers(dest="cmd", required=True)

    to = sub.add_parser("to-dsl", help="NL → DSL line only")
    to.add_argument("prompt")
    to.add_argument("--project", default=".")
    to.add_argument("--llm", action="store_true")

    apply = sub.add_parser("apply", help="NL → DSL → dispatch")
    apply.add_argument("prompt")
    apply.add_argument("--project", default=".")
    apply.add_argument("--llm", action="store_true")
    apply.add_argument("--json", action="store_true")

    wf = sub.add_parser("workflow", help="NL → nlpshim workflow (no dispatch)")
    wf.add_argument("prompt")
    wf.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "to-dsl":
        try:
            print(to_dsl(args.prompt, project=args.project, use_llm=args.llm))
            return 0
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "apply":
        result = apply_nl(args.prompt, project=args.project, use_llm=args.llm)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(result.dsl)
            if result.result and result.result.output:
                print(result.result.output.rstrip())
            if result.error:
                print(f"error: {result.error}", file=sys.stderr)
        return 0 if result.ok else 1

    if args.cmd == "workflow":
        payload = workflow_from_nl(args.prompt)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
