"""``koru work`` — ticket-first git workflow with validator-agent publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koru.events import emit_management_event
from koru.work.lifecycle import finish_work, start_work


def _print(payload: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    status = payload.get("status")
    ticket = payload.get("ticket_id")
    branch = payload.get("branch")
    print(f"koru work: status={status} ticket={ticket} branch={branch}")
    for step in payload.get("next") or []:
        print(f"  next: {step}")


def _action_start(args: argparse.Namespace) -> int:
    result = start_work(
        args.project,
        title=args.title,
        description=args.description,
        ticket_id=args.ticket,
        base_branch=args.base,
        push=not args.no_push,
        remote=args.remote,
    )
    _print(result, args.format)
    emit_management_event(
        tool="koru.work",
        action="start",
        status="completed",
        message=f"{result.get('ticket_id')} on {result.get('branch')}",
        details=result,
    )
    return 0


def _action_finish(args: argparse.Namespace) -> int:
    result = finish_work(
        args.project,
        ticket_id=args.ticket,
        base_branch=args.base,
        run_ci=not args.skip_ci,
        open_pr=args.open_pr,
        publish=not args.no_publish,
        merge=args.merge,
        dry_run=args.dry_run,
        pr_number=args.pr,
    )
    _print(result, args.format)
    code = 0 if result.get("status") in {"finished", "dry_run"} else 1
    emit_management_event(
        tool="koru.work",
        action="finish",
        status="completed" if code == 0 else "failed",
        message=f"{args.ticket} -> {result.get('status')}",
        details=result,
    )
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru work",
        description=(
            "Ticket-first workflow: planfile ticket → git branch push → "
            "CI → validator-agent publish (bypass GitHub Actions merge limits)."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("text", "json"), default="text")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    start = sub.add_parser("start", help="Create ticket, branch, commit planfile, push.")
    start.add_argument("--title", required=True)
    start.add_argument("--description", default=None)
    start.add_argument("--ticket", default=None, help="Reuse existing ticket id.")
    start.add_argument("--base", default="main")
    start.add_argument("--no-push", action="store_true")
    start.add_argument("--remote", default="origin")
    start.set_defaults(func=_action_start)

    finish = sub.add_parser("finish", help="Run CI and dispatch validator-agent.")
    finish.add_argument("--ticket", required=True)
    finish.add_argument("--base", default="main")
    finish.add_argument("--skip-ci", action="store_true")
    finish.add_argument(
        "--open-pr",
        action="store_true",
        help="Create GitHub PR if missing (merge still via validator-agent).",
    )
    finish.add_argument("--pr", type=int, default=None, help="Existing PR number for publish.")
    finish.add_argument("--merge", action="store_true", help="Pass --merge to validator dispatch.")
    finish.add_argument("--no-publish", action="store_true", help="Skip validator-agent dispatch.")
    finish.add_argument("--dry-run", action="store_true")
    finish.set_defaults(func=_action_finish)

    return parser


def work_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"koru work: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "work_main"]
