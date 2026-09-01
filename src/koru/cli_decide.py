"""``koru decide`` — compile and optionally run the next autonomy action."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koru.autonomy.execution_plan import compile_execution_plan, run_auto_steps
from koru.events import emit_management_event


def _print_plan(plan, fmt: str) -> None:
    payload = plan.to_dict()
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"koru decide: {plan.summary}")
    print(f"  strategy: {plan.strategy_id}")
    print(f"  signals: {plan.signals.get('planfile')}")
    if plan.selected_ticket:
        ticket = payload.get("selected_ticket") or {}
        print(
            f"  ticket: {ticket.get('id')} — {ticket.get('name')} "
            f"(repo={ticket.get('repo')})",
        )
    for step in plan.steps:
        auto = "auto" if step.auto_runnable else "manual"
        print(f"  step {step.id} [{step.kind}/{auto}] profile={step.profile_id}")
        for command in step.commands:
            print(f"    $ {command}")
        if step.hint:
            print(f"    hint: {step.hint[:240]}")


def decide_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru decide",
        description=(
            "Compile the next execution plan from koru.yaml strategy, planfile "
            "tickets, and built-in task profiles."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute auto-runnable shell steps from the compiled plan.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --run, print commands without executing them.",
    )
    args = parser.parse_args(argv)

    try:
        plan = compile_execution_plan(args.project)
    except Exception as exc:
        print(f"koru decide: {exc}", file=sys.stderr)
        return 2

    _print_plan(plan, args.format)

    if args.run:
        results = run_auto_steps(plan, dry_run=args.dry_run)
        if args.format == "json":
            print(json.dumps({"run": results}, indent=2, sort_keys=True))
        else:
            for row in results:
                print(f"  run {row.get('step')}: {row.get('status')}")
        failed = [row for row in results if row.get("status") == "failed"]
        emit_management_event(
            tool="koru.decide",
            action="run" if args.run else "compile",
            status="failed" if failed else "completed",
            message=plan.summary,
            details={"plan": plan.to_dict(), "run": results},
        )
        return 1 if failed else 0

    emit_management_event(
        tool="koru.decide",
        action="compile",
        status="completed",
        message=plan.summary,
        details=plan.to_dict(),
    )
    return 0


__all__ = ["decide_main"]
