"""CLI for nlp2coru."""

from __future__ import annotations

import argparse
import json
import sys

from .apply import apply_prompt
from .heuristic import to_dsl_lines
from .models import ApplyResult
from .rewrite import rewrite_chat_prompt


def _emit(result: ApplyResult, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return
    for line in result.lines:
        print(line)
    if result.error:
        print(f"error: {result.error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Natural language for CORU control")
    sub = parser.add_subparsers(dest="cmd", required=True)

    to_dsl = sub.add_parser("to-dsl", help="Convert prompt to CORU DSL")
    to_dsl.add_argument("prompt")
    to_dsl.add_argument("--llm", action="store_true")
    to_dsl.add_argument("--model", default="openrouter/qwen/qwen3-coder-next")
    to_dsl.add_argument("--json", action="store_true")

    apply = sub.add_parser("apply", help="Convert+execute NL through CORU DSL")
    apply.add_argument("prompt")
    apply.add_argument("--llm", action="store_true")
    apply.add_argument("--model", default="openrouter/qwen/qwen3-coder-next")
    apply.add_argument("--json", action="store_true")

    rewrite = sub.add_parser("rewrite-chat", help="Rewrite NL prompt for chat")
    rewrite.add_argument("prompt")
    rewrite.add_argument("--ide", default="")
    rewrite.add_argument("--instance", default="")
    rewrite.add_argument("--model", default="openrouter/qwen/qwen3-coder-next")

    args = parser.parse_args(argv)

    if args.cmd == "to-dsl":
        lines = to_dsl_lines(args.prompt, use_llm=args.llm, llm_model=args.model)
        if args.json:
            print(json.dumps(lines, ensure_ascii=False, indent=2))
        else:
            for line in lines:
                print(line)
        return 0

    if args.cmd == "apply":
        result = apply_prompt(args.prompt, use_llm=args.llm, llm_model=args.model)
        _emit(result, as_json=args.json)
        return 0 if result.ok else 1

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
