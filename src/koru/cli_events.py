"""CLI command for querying persisted CQRS event history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from koru.cqrs import EventLogQueryService
from koru.cqrs.event_store import JsonlEventStore, project_event_store_path


def build_events_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru events",
        description="Query persisted CQRS events from .koru/event-store.jsonl.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .koru/event-store.jsonl.",
    )
    parser.add_argument(
        "--context",
        required=True,
        help="Bounded context id (e.g. tasks, planfile_queue, env_config).",
    )
    parser.add_argument(
        "--aggregate-id",
        default=None,
        help="Optional aggregate id filter (ticket id, project path, checkpoint path, etc.).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of recent events to return (default: 50).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "text"),
        default="json",
        help="Output format (default: json).",
    )
    return parser


def _render_text(
    *,
    context: str,
    aggregate_id: str | None,
    limit: int | None,
    entries: list[dict[str, object]],
) -> str:
    header = [f"koru events context={context}"]
    if aggregate_id:
        header.append(f"aggregate_id={aggregate_id}")
    if limit is not None:
        header.append(f"limit={limit}")
    lines = [" ".join(header)]
    lines.append(f"count={len(entries)}")
    if not entries:
        lines.append("(no events)")
        return "\n".join(lines)
    for entry in entries:
        payload = json.dumps(entry.get("payload") or {}, ensure_ascii=False, sort_keys=True)
        lines.append(
            " - seq={sequence} type={event_type} aggregate={aggregate_id} at={occurred_at} payload={payload}".format(
                sequence=entry.get("sequence"),
                event_type=entry.get("event_type"),
                aggregate_id=entry.get("aggregate_id") or "-",
                occurred_at=entry.get("occurred_at"),
                payload=payload,
            )
        )
    return "\n".join(lines)


def events_main(argv: list[str]) -> int:
    args = build_events_parser().parse_args(argv)
    store = JsonlEventStore(project_event_store_path(args.project))
    entries = EventLogQueryService(store).recent(
        context=args.context,
        aggregate_id=args.aggregate_id,
        limit=args.limit,
    )
    payload = {
        "project": str(args.project.resolve()),
        "store_path": str(project_event_store_path(args.project)),
        "context": args.context,
        "aggregate_id": args.aggregate_id,
        "limit": args.limit,
        "count": len(entries),
        "events": [
            {
                "sequence": entry.sequence,
                "event_type": entry.event_type,
                "aggregate_id": entry.aggregate_id,
                "occurred_at": entry.occurred_at,
                "payload": entry.payload,
            }
            for entry in entries
        ],
    }
    if args.output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            _render_text(
                context=args.context,
                aggregate_id=args.aggregate_id,
                limit=args.limit,
                entries=payload["events"],
            )
        )
    return 0


__all__ = ["build_events_parser", "events_main"]