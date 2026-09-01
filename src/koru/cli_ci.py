"""``koru ci`` — local CI, quality gates, and validator-agent publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koru.ci.gates import run_quality_gates
from koru.ci.publication import dispatch_validator_merge, load_publication_config
from koru.ci.runner import run_local_ci
from koru.events import emit_management_event


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _action_run(args: argparse.Namespace) -> int:
    result = run_local_ci(
        args.project,
        include_gates=not args.skip_gates,
        gates=args.gates or None,
        fail_fast=not args.no_fail_fast,
    )
    if args.format == "json":
        _print_json(result)
    else:
        for stage in result.get("stages", []):
            name = stage.get("stage", "unknown")
            status = stage.get("status") or stage.get("overall_status", "unknown")
            print(f"koru ci run: {name}: {status}")
        print(f"koru ci run: overall={result.get('overall_status')}")
    emit_management_event(
        tool="koru.ci",
        action="run",
        status="completed" if result.get("overall_status") == "passed" else "failed",
        message=f"overall={result.get('overall_status')}",
        details={"project": str(args.project), "stages": result.get("stages", [])},
    )
    return 0 if result.get("overall_status") == "passed" else 1


def _action_gates(args: argparse.Namespace) -> int:
    result = run_quality_gates(
        args.project,
        gates=args.gates or None,
        fail_fast=not args.no_fail_fast,
    )
    if args.format == "json":
        _print_json(result)
    else:
        for item in result.get("results", []):
            print(f"koru ci gates: {item.get('gate')}: {item.get('status')}")
        print(f"koru ci gates: overall={result.get('overall_status')}")
    return 0 if result.get("overall_status") == "passed" else 1


def _action_publish(args: argparse.Namespace) -> int:
    config = load_publication_config(args.project)
    if args.merge or args.watch or args.update_branch or args.no_wait_checks:
        config = replace(
            config,
            merge=config.merge or args.merge,
            watch=config.watch or args.watch,
            update_branch=config.update_branch or args.update_branch,
            wait_checks=False if args.no_wait_checks else config.wait_checks,
        )
    result = dispatch_validator_merge(
        args.project,
        ticket_id=args.ticket,
        pr_number=args.pr,
        owner=args.owner,
        name=args.name,
        config=config,
        dry_run=args.dry_run,
    )
    if args.format == "json":
        _print_json(result)
    else:
        print(
            f"koru ci publish: status={result.get('status')} "
            f"repo={result.get('repo')} pr={result.get('pr')} head={result.get('frozen_head')}",
        )
        if result.get("output_tail"):
            print(result["output_tail"], file=sys.stderr)
    emit_management_event(
        tool="koru.ci",
        action="publish",
        status="completed" if result.get("status") in {"published", "dry_run"} else "failed",
        message=f"pr={result.get('pr')} status={result.get('status')}",
        details=result,
    )
    return 0 if result.get("status") in {"published", "dry_run"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru ci",
        description=(
            "Run local CI (policy command + quality gates) and optionally "
            "dispatch subactor/validator-agent for protected GitHub merge."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    run = sub.add_parser("run", help="Run policy ci.command then quality gates.")
    run.add_argument("--skip-gates", action="store_true", help="Only run policy ci.command.")
    run.add_argument("--gates", nargs="+", help="Subset of gates (regix, redup, vallm, …).")
    run.add_argument("--no-fail-fast", action="store_true", help="Run all gates even after failure.")
    run.add_argument("--format", choices=("text", "json"), default="text")
    run.set_defaults(func=_action_run)

    gates = sub.add_parser("gates", help="Run Koru quality gates only.")
    gates.add_argument("--gates", nargs="+", help="Subset of gates.")
    gates.add_argument("--no-fail-fast", action="store_true")
    gates.add_argument("--format", choices=("text", "json"), default="text")
    gates.set_defaults(func=_action_gates)

    publish = sub.add_parser(
        "publish",
        help="Freeze PR head and dispatch validator-agent (does not self-approve).",
    )
    publish.add_argument("--ticket", required=True, help="Active ticket id (e.g. ticket-021).")
    publish.add_argument("--pr", type=int, default=None, help="PR number; defaults to open PR for current branch.")
    publish.add_argument("--owner", default=None, help="GitHub org/user; defaults from gh repo view.")
    publish.add_argument("--name", default=None, help="Repository name; defaults from gh repo view.")
    publish.add_argument("--merge", action="store_true", help="Pass --merge to validator dispatch script.")
    publish.add_argument("--watch", action="store_true", help="Pass --watch to validator dispatch script.")
    publish.add_argument("--update-branch", action="store_true", help="Pass --update-branch before dispatch.")
    publish.add_argument("--no-wait-checks", action="store_true", help="Skip --wait-checks on dispatch.")
    publish.add_argument("--dry-run", action="store_true", help="Print frozen head and dispatch argv only.")
    publish.add_argument("--format", choices=("text", "json"), default="text")
    publish.set_defaults(func=_action_publish)

    return parser


def ci_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"koru ci: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "ci_main"]
