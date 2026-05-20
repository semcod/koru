"""CLI helpers for ``koru gc``."""


import json
from argparse import Namespace
from typing import Any

from koru.events import emit_management_event
from koru.gc import GcResult


def gc_statuses_from_args(status_csv: str) -> frozenset[str]:
    return frozenset(s.strip() for s in status_csv.split(",") if s.strip())


def gc_result_to_json(result: GcResult) -> dict[str, Any]:
    return {
        "dry_run": result.dry_run,
        "candidates": [
            {
                "ticket_id": c.ticket_id,
                "name": c.name,
                "status": c.status,
                "age_days": c.age_days,
            }
            for c in result.candidates
        ],
        "removed": result.removed,
        "kept": result.kept,
        "archived_to": str(result.archived_to) if result.archived_to else None,
        "errors": result.errors,
    }


def print_gc_text_report(result: GcResult, *, max_age_days: float) -> None:
    mode = "DRY RUN" if result.dry_run else "APPLIED"
    if not result.candidates:
        print(f"koru gc ({mode}): no stale tickets found (max-age={max_age_days}d)")
        return
    print(f"koru gc ({mode}): {result.summary()}")
    print()
    for c in result.candidates:
        marker = "✗" if c.ticket_id in result.removed else "·"
        age = f"{c.age_days:.0f}d" if c.age_days != float("inf") else "??d"
        print(
            f"  {marker} {c.ticket_id:<14} {c.status:<10} {age:>6}  {c.name[:60]}",
        )
    if result.removed:
        action = "Would remove" if result.dry_run else "Removed"
        print(f"\n  → {action}: {len(result.removed)} ticket(s)")
    if result.kept:
        print(f"  → Kept: {len(result.kept)} ticket(s)")
    if result.archived_to:
        print(f"  → Archived to: {result.archived_to}")
    if result.errors:
        print(f"  → Errors: {len(result.errors)}")
        for err in result.errors:
            print(f"    {err}")


def emit_gc_management_event(args: Namespace, result: GcResult) -> None:
    emit_management_event(
        tool="koru.gc",
        action="applied" if args.apply else "previewed",
        status="completed",
        message=result.summary(),
        details={
            "project": str(args.project),
            "removed": result.removed,
            "kept": result.kept,
            "max_age_days": args.max_age,
            "keep_last": args.keep_last,
        },
    )


def print_gc_report(args: Namespace, result: GcResult) -> None:
    if args.output_format == "json":
        print(json.dumps(gc_result_to_json(result), indent=2, sort_keys=True))
    else:
        print_gc_text_report(result, max_age_days=args.max_age)
