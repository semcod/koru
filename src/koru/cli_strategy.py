"""CLI for project autonomy strategy configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from koru.autonomy_strategy import (
    build_strategy_heuristics,
    build_strategy_update_prompt,
    ensure_autonomy_strategy_config,
    load_autonomy_strategy,
)
from koru.autonomy_strategy.openrouter import ask_openrouter_for_strategy_patch


def strategy_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru strategy",
        description="Inspect and evolve the autonomy.strategy section in koru.yaml.",
    )
    parser.add_argument("--project", default=".", help="Project root.")
    parser.add_argument("--ensure", action="store_true", help="Create missing default strategy.")
    parser.add_argument("--heuristics", action="store_true", help="Print heuristic report as JSON.")
    parser.add_argument("--prompt", action="store_true", help="Print LLM prompt for a YAML patch.")
    parser.add_argument(
        "--ask-openrouter",
        action="store_true",
        help="Explicitly call OpenRouter and print its proposed patch.",
    )
    parser.add_argument(
        "--model",
        default="qwen/qwen3-coder-next",
        help="OpenRouter model for --ask-openrouter.",
    )
    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()

    if args.ensure:
        result = ensure_autonomy_strategy_config(project)
        status = "added" if result.added_strategy or result.created_koru_yaml else "present"
        print(f"autonomy.strategy {status}: {result.path}")
        return 0

    if args.heuristics:
        print(json.dumps(build_strategy_heuristics(project), indent=2, ensure_ascii=False))
        return 0

    if args.prompt:
        print(build_strategy_update_prompt(project))
        return 0

    if args.ask_openrouter:
        prompt = build_strategy_update_prompt(project)
        response = ask_openrouter_for_strategy_patch(prompt, model=args.model)
        if not response.ok:
            print(f"OpenRouter strategy proposal failed: {response.error}")
            return 1
        print(response.content)
        return 0

    strategy = load_autonomy_strategy(project)
    if strategy is None:
        print("autonomy.strategy missing; run `koru strategy --ensure`")
        return 1
    print(yaml.safe_dump(strategy, sort_keys=False, allow_unicode=True))
    return 0


__all__ = ["strategy_main"]
