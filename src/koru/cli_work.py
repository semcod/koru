"""``koru work`` — ticket-first git workflow with validator-agent publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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

    next_cmd = sub.add_parser(
        "next",
        help="Decide the next refactor ticket and optionally start a work branch.",
    )
    next_cmd.add_argument("--run-gates", action="store_true", help="Run auto steps from decide plan.")
    next_cmd.add_argument("--start-branch", action="store_true", help="koru work start on selected ticket.")
    next_cmd.add_argument("--base", default="main")
    next_cmd.add_argument("--no-push", action="store_true")
    next_cmd.add_argument("--remote", default="origin")
    next_cmd.set_defaults(func=_action_next)

    return parser


def work_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"koru work: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "work_main"]
