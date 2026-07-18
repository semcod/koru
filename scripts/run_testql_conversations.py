#!/usr/bin/env python3
"""Run koru conversation TestQL scenarios (mock LLM default, live optional)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO_DIR = REPO / "testql-scenarios" / "conversations"
DEFAULT_MOCK_REPLIES = REPO / "testql-scenarios" / "artifacts" / "mock-llm-replies.yaml"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", nargs="*", help="Scenario file(s); default: all in conversations/")
    parser.add_argument("--dry-run", action="store_true", help="Parse IR only")
    parser.add_argument("--mock-replies", type=Path, default=DEFAULT_MOCK_REPLIES)
    parser.add_argument("--live-llm", action="store_true", help="Use live LLM (TESTQL_LIVE_LLM=1)")
    parser.add_argument("--api-url", default=os.environ.get("NLP2DSL_URL", "http://localhost:8010"))
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args(argv)


def _discover_scenarios(args: argparse.Namespace) -> list[Path]:
    if args.scenarios:
        return [Path(p) for p in args.scenarios]
    return sorted(DEFAULT_SCENARIO_DIR.glob("*.testql.toon.yaml"))


def _load_conversation_modules() -> tuple[type, type] | None:
    try:
        from testql.adapters.nlp2dsl import Nlp2DslAdapter
        from testql.conversation import ConversationRunner
    except ImportError as exc:
        print(f"testql conversation modules unavailable: {exc}", file=sys.stderr)
        return None
    return Nlp2DslAdapter, ConversationRunner


def _print_scenario_report(path: Path, args: argparse.Namespace, result) -> None:
    if args.json_output:
        print(json.dumps({"file": str(path), **result.to_report_dict()}, indent=2))
        return
    status = "PASS" if result.passed else "FAIL"
    mode = "dry-run" if args.dry_run else ("live-llm" if args.live_llm else "mock-llm")
    print(f"{status} [{mode}] {path.name}")
    for turn in result.turns:
        print(f"  - {turn.kind}: {turn.status} — {turn.summary}")


def _run_scenario(path: Path, args: argparse.Namespace, adapter_cls: type, runner_cls: type) -> bool:
    adapter = adapter_cls()
    plan = adapter.parse(path)
    base = plan.config.get("nlp2dsl_base_url") or args.api_url
    runner = runner_cls(
        dry_run=args.dry_run,
        api_url=str(base),
        live_llm=args.live_llm,
        mock_replies=str(args.mock_replies) if args.mock_replies.is_file() else None,
    )
    result = runner.run(plan)
    _print_scenario_report(path, args, result)
    return result.passed


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    paths = _discover_scenarios(args)
    if not paths:
        print("No scenarios found", file=sys.stderr)
        return 1

    modules = _load_conversation_modules()
    if modules is None:
        return 1
    adapter_cls, runner_cls = modules

    failed = 0
    for path in paths:
        if not _run_scenario(path, args, adapter_cls, runner_cls):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
