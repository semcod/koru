"""Trace rendering action for ``koru autopilot trace``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def action_trace(args: argparse.Namespace) -> int:
    """Print the structured ``DecisionRecord`` ring buffer."""
    from koru.autonomy.decision_trace import (
        DecisionRecord,
        human_skip_reason,
        load_recent_decisions,
    )

    project = args.project.resolve()
    if args.format == "dsl":
        return _print_observability_dsl_trace(args, project)
    history = load_recent_decisions(project, limit=int(args.limit or 10))
    if args.format == "json":
        print(json.dumps({"project": str(project), "decisions": history}, indent=2))
        return 0
    if not history:
        print(
            f"koru autopilot trace: no decisions recorded yet for {project}\n"
            "  Run `koru auto` (or one cycle of it) to populate "
            "`.planfile/.koru/autonomy-telemetry.json`."
        )
        return 0
    print(f"koru autopilot trace: last {len(history)} decision(s) for {project}\n")
    for item in history:
        try:
            record = DecisionRecord(
                at=str(item.get("at", "")),
                cycle=int(item.get("cycle", 0) or 0),
                observed=str(item.get("observed", "")),
                decided=str(item.get("decided", "")),
                action=str(item.get("action", "")),
                evidence=str(item.get("evidence", "")),
                next_step=str(item.get("next_step", "")),
                skip_code=str(item.get("skip_code", "unknown")),
                skip_because=str(item.get("skip_because", "")),
            )
        except (TypeError, ValueError):
            continue
        print(f"  cycle={record.cycle:>4} [{record.skip_code}] {record.at}")
        print(f"    {record.compact_line()}")
        if record.skip_because:
            print(f"    because: {record.skip_because}")
        elif record.skip_code not in ("ok", "unknown"):
            print(f"    because: {human_skip_reason(record.skip_code)}")
        print()
    return 0


def _print_observability_dsl_trace(args: argparse.Namespace, project: Path) -> int:
    from koru.cqrs.event_store import JsonlEventStore
    from koru.observability_dsl import OBSERVABILITY_CONTEXT, stored_event_to_dsl
    from koru.observability_writer import observability_event_store_path

    store = JsonlEventStore(observability_event_store_path(project))
    events = store.all_events(context=OBSERVABILITY_CONTEXT)
    limit = int(args.limit or 10)
    if limit > 0:
        events = events[-limit:]
    if not events:
        print(f"koru autopilot trace: no observability DSL events recorded yet for {project}")
        return 0
    print("\n\n".join(stored_event_to_dsl(event) for event in events))
    return 0


_action_trace = action_trace


__all__ = ["action_trace"]
