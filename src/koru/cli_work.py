"""``koru work`` — ticket-first git workflow with validator-agent publication."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomy.execution_plan import (
    compile_execution_plan,
    resolve_ticket_repo,
    run_auto_steps,
)
from koru.events import emit_management_event
from koru.work.lifecycle import finish_work, start_work
from koru.work.llm_provenance import resolve_work_llm_context


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


def _action_next(args: argparse.Namespace) -> int:
    plan = compile_execution_plan(args.project)
    llm_ctx = resolve_work_llm_context(args.project)
    payload: dict = {
        "status": "planned",
        "plan": plan.to_dict(),
        "llm": llm_ctx.to_dict(),
    }
    if args.run_gates:
        payload["auto_run"] = run_auto_steps(plan, dry_run=False)
    if args.start_branch and plan.selected_ticket:
        repo = Path(resolve_ticket_repo(args.project, plan.selected_ticket) or args.project)
        title = str(plan.selected_ticket.get("name") or plan.selected_ticket.get("id"))
        ticket_id = str(plan.selected_ticket.get("id") or "")
        work = start_work(
            repo,
            title=title,
            ticket_id=ticket_id,
            base_branch=args.base,
            push=not args.no_push,
            remote=args.remote,
        )
        payload["work"] = work
        payload["status"] = work.get("status", "started")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"koru work next: {plan.summary}")
        print(
            "  llm: "
            f"planning={llm_ctx.planning_provider}/{llm_ctx.planning_model} "
            f"work={llm_ctx.work_llm_mode}"
        )
        if llm_ctx.project_url:
            print(f"  project: {llm_ctx.project_url}")
        if plan.selected_ticket:
            ticket = plan.to_dict().get("selected_ticket") or {}
            print(f"  selected: {ticket.get('id')} @ {ticket.get('repo')}")
        for step in plan.steps:
            print(f"  step {step.id}: {step.kind} ({step.profile_id})")
            for command in step.commands:
                print(f"    $ {command}")
    emit_management_event(
        tool="koru.work",
        action="next",
        status="completed",
        message=plan.summary,
        details=payload,
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


_ArgSpec = tuple[str, dict[str, Any]]
_WorkAction = Callable[[argparse.Namespace], int]

_START_ARGS: tuple[_ArgSpec, ...] = (
    ("--title", {"required": True}),
    ("--description", {"default": None}),
    ("--ticket", {"default": None, "help": "Reuse existing ticket id."}),
    ("--base", {"default": "main"}),
    ("--no-push", {"action": "store_true"}),
    ("--remote", {"default": "origin"}),
)

_FINISH_ARGS: tuple[_ArgSpec, ...] = (
    ("--ticket", {"required": True}),
    ("--base", {"default": "main"}),
    ("--skip-ci", {"action": "store_true"}),
    (
        "--open-pr",
        {"action": "store_true", "help": "Create GitHub PR if missing (merge still via validator-agent)."},
    ),
    ("--pr", {"type": int, "default": None, "help": "Existing PR number for publish."}),
    ("--merge", {"action": "store_true", "help": "Pass --merge to validator dispatch."}),
    ("--no-publish", {"action": "store_true", "help": "Skip validator-agent dispatch."}),
    ("--dry-run", {"action": "store_true"}),
)

_NEXT_ARGS: tuple[_ArgSpec, ...] = (
    ("--run-gates", {"action": "store_true", "help": "Run auto steps from decide plan."}),
    ("--start-branch", {"action": "store_true", "help": "koru work start on selected ticket."}),
    ("--base", {"default": "main"}),
    ("--no-push", {"action": "store_true"}),
    ("--remote", {"default": "origin"}),
)

_SUBCOMMANDS: tuple[tuple[str, str, tuple[_ArgSpec, ...], _WorkAction], ...] = (
    ("start", "Create ticket, branch, commit planfile, push.", _START_ARGS, _action_start),
    ("finish", "Run CI and dispatch validator-agent.", _FINISH_ARGS, _action_finish),
    (
        "next",
        "Decide the next refactor ticket and optionally start a work branch.",
        _NEXT_ARGS,
        _action_next,
    ),
)


def _add_subcommand(
    sub: argparse._SubParsersAction,
    name: str,
    help_text: str,
    args: tuple[_ArgSpec, ...],
    func: _WorkAction,
) -> None:
    cmd = sub.add_parser(name, help=help_text)
    for flags, kwargs in args:
        cmd.add_argument(flags, **kwargs)
    cmd.set_defaults(func=func)


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
    for name, help_text, args, func in _SUBCOMMANDS:
        _add_subcommand(sub, name, help_text, args, func)
    return parser


def work_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"koru work: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "work_main"]
