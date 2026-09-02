"""Shared CLI for the nlp2koru and nlp2coru command names."""

from __future__ import annotations

import argparse
import json
import sys

from nlp2koru.apply import apply_nl
from nlp2koru.llm_backend import rewrite_chat_prompt
from nlp2koru.to_dsl import to_dsl, workflow_from_nl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Natural language to Koru control DSL")
    sub = parser.add_subparsers(dest="cmd", required=True)

    to = sub.add_parser("to-dsl", help="Convert natural language to one DSL line")
    to.add_argument("prompt")
    to.add_argument("--project", default=".")
    to.add_argument("--llm", action="store_true")
    to.add_argument("--model", help="deprecated compatibility hint; central policy selects the model")
    to.add_argument("--json", action="store_true")

    apply = sub.add_parser("apply", help="Convert and dispatch natural language")
    apply.add_argument("prompt")
    apply.add_argument("--project", default=".")
    apply.add_argument("--llm", action="store_true")
    apply.add_argument("--model", help="deprecated compatibility hint; central policy selects the model")
    apply.add_argument("--json", action="store_true")

    workflow = sub.add_parser("workflow", help="Build an nlpshim workflow without dispatch")
    workflow.add_argument("prompt")
    workflow.add_argument("--json", action="store_true")

    rewrite = sub.add_parser("rewrite-chat", help="Rewrite natural language for IDE chat")
    rewrite.add_argument("prompt")
    rewrite.add_argument("--ide", default="")
    rewrite.add_argument("--instance", default="")
    rewrite.add_argument("--model", help="deprecated compatibility hint; central policy selects the model")

    args = parser.parse_args(argv)
    if args.cmd == "to-dsl":
        try:
            line = to_dsl(
                args.prompt,
                project=args.project,
                use_llm=args.llm,
                llm_model=args.model,
            )
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps([line], ensure_ascii=False, indent=2) if args.json else line)
        return 0

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
        print(json.dumps(workflow_from_nl(args.prompt), indent=2, ensure_ascii=False))
        return 0

    rewritten = rewrite_chat_prompt(
        args.prompt,
        ide=args.ide,
        instance=args.instance,
        model=args.model,
    )
    if rewritten:
        print(rewritten)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
