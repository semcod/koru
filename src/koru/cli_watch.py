"""CLI command for watching planfile events."""

from __future__ import annotations

import argparse
import asyncio

from koru.events import emit_management_event
from koru.watch import watch_planfile_events


def watch_main(args: argparse.Namespace) -> int:
    emit_management_event(
        tool="koru.watch",
        action="started",
        status="running",
        message=args.ws_url,
        queue=args.queue_name,
    )
    try:
        seen = asyncio.run(watch_planfile_events(args.ws_url, max_events=args.max_events))
    except RuntimeError as exc:
        print(f"koru watch: {exc}")
        emit_management_event(
            tool="koru.watch",
            action="failed",
            status="failed",
            level="error",
            message=str(exc),
            queue=args.queue_name,
        )
        return 1
    emit_management_event(
        tool="koru.watch",
        action="completed",
        status="completed",
        message=f"seen={seen}",
        queue=args.queue_name,
        details={"ws_url": args.ws_url, "seen": seen},
    )
    return 0
