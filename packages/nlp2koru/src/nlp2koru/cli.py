"""Shared CLI for the nlp2koru and nlp2coru command names."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from nlp2koru.apply import apply_nl
from nlp2koru.llm_backend import rewrite_chat_prompt
from nlp2koru.to_dsl import to_dsl, workflow_from_nl

ArgumentSpec = tuple[tuple[str, ...], dict[str, Any]]


def _arg(*flags: str, **kwargs: Any) -> ArgumentSpec:
    return flags, kwargs


_LLM_MODEL = _arg("--model", help="deprecated compatibility hint; central policy selects the model")
_JSON = _arg("--json", action="store_true")
_CONVERT_ARGUMENTS: tuple[ArgumentSpec, ...] = (
    _arg("prompt"),
    _arg("--project", default="."),
    _arg("--llm", action="store_true"),
    _LLM_MODEL,
    _JSON,
)
_SUBCOMMANDS: tuple[tuple[str, str, tuple[ArgumentSpec, ...]], ...] = (
    ("to-dsl", "Convert natural language to one DSL line", _CONVERT_ARGUMENTS),
    ("apply", "Convert and dispatch natural language", _CONVERT_ARGUMENTS),
    ("workflow", "Build an nlpshim workflow without dispatch", (_arg("prompt"), _JSON)),
    (
        "rewrite-chat",
        "Rewrite natural language for IDE chat",
        (
            _arg("prompt"),
            _arg("--ide", default=""),
            _arg("--instance", default=""),
            _LLM_MODEL,
        ),
    ),
)


def _add_arguments(parser: argparse.ArgumentParser, specs: tuple[ArgumentSpec, ...]) -> None:
    for flags, kwargs in specs:
        parser.add_argument(*flags, **kwargs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Natural language to Koru control DSL")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, help_text, specs in _SUBCOMMANDS:
        command = sub.add_parser(name, help=help_text)
        _add_arguments(command, specs)
    return parser


def _cmd_to_dsl(args: argparse.Namespace) -> int:
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


def _cmd_apply(args: argparse.Namespace) -> int:
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


def _cmd_workflow(args: argparse.Namespace) -> int:
    print(json.dumps(workflow_from_nl(args.prompt), indent=2, ensure_ascii=False))
    return 0


def _cmd_rewrite(args: argparse.Namespace) -> int:
    rewritten = rewrite_chat_prompt(
        args.prompt,
        ide=args.ide,
        instance=args.instance,
        model=args.model,
    )
    if rewritten:
        print(rewritten)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "to-dsl":
        return _cmd_to_dsl(args)
    if args.cmd == "apply":
        return _cmd_apply(args)
    if args.cmd == "workflow":
        return _cmd_workflow(args)
    return _cmd_rewrite(args)


if __name__ == "__main__":
    raise SystemExit(main())
