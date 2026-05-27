"""CLI entrypoint for replaying structured Koru operator actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from koru.autonomy.replay_actions import (
    execute_replay_action,
    parse_replay_dsl,
    validate_replay_action,
)


def build_replay_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru replay",
        description="Replay or validate a structured Koru operator action.",
    )
    parser.add_argument(
        "replay_dsl",
        metavar="action",
        nargs="?",
        help="Replay DSL, for example: 'trace show-decisions' or 'ticket input STARTER-1'.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used as the working directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the parsed action and command without executing it.",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Explain what would run. Alias for --dry-run.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that the action's expected effect is present.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def replay_main(argv: list[str]) -> int:
    args = build_replay_parser().parse_args(argv)
    if not args.replay_dsl:
        print("koru replay: action is required")
        return 2
    try:
        replay_action = parse_replay_dsl(args.replay_dsl)
    except ValueError as exc:
        print(f"koru replay: {exc}")
        return 2

    if args.dry_run or args.explain:
        payload = _replay_action_payload(replay_action)
        _print_payload(payload, args.output_format)
        return 0

    if args.validate:
        result = validate_replay_action(replay_action, project=args.project)
        payload = {
            **_replay_action_payload(replay_action),
            "validation": {
                "passed": result.passed,
                "reason": result.reason,
                "regression_point": result.regression_point,
            },
        }
        _print_payload(payload, args.output_format)
        return 0 if result.passed else 1

    result = execute_replay_action(replay_action, project=args.project)
    payload = {
        **_replay_action_payload(replay_action),
        "execution": {
            "ok": result.ok,
            "returncode": result.returncode,
            "output": result.output,
        },
    }
    _print_payload(payload, args.output_format)
    return 0 if result.ok else 1


def _replay_action_payload(replay_action) -> dict[str, object]:
    return {
        "dsl": replay_action.to_dsl(),
        "shell": replay_action.to_shell(),
        "domain": replay_action.domain,
        "verb": replay_action.verb,
        "positional": list(replay_action.positional),
        "args": dict(replay_action.args),
        "label": replay_action.label,
        "replayable": replay_action.replayable,
        "safe": replay_action.safe,
        "requires_active_window": replay_action.requires_active_window,
        "validate_cmd": replay_action.validate_cmd,
    }


def _print_payload(payload: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"koru replay: {payload['dsl']}")
    print(f"  shell: {payload['shell']}")
    print(f"  replayable: {payload['replayable']} safe: {payload['safe']}")
    if payload.get("validate_cmd"):
        print(f"  validate: {payload['validate_cmd']}")
    execution = payload.get("execution")
    if isinstance(execution, dict):
        print(f"  result: ok={execution['ok']} rc={execution['returncode']}")
        if execution.get("output"):
            print(str(execution["output"]).rstrip())
    validation = payload.get("validation")
    if isinstance(validation, dict):
        print(f"  validation: passed={validation['passed']} {validation['reason']}")


__all__ = ["build_replay_parser", "replay_main"]
