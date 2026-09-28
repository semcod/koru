"""Read native Planfile readiness through the configured CLI transport."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from koru.queue.ticket import planfile_command
from koru.queue.types import CommandResult


def admitted_payload(
    project: Path,
    payload: str,
    *,
    runner: Callable[[list[str], Path], CommandResult],
    queue_name: str | None,
) -> str:
    """Filter candidates by native readiness, including archived dependencies.

    An unsupported or malformed report is not permission to execute. Keep this
    read before claim/start and use the same Planfile command as ticket reads.
    """
    # Fast path: native in-process Planfile SDK when using default runner
    from koru.queue.runners import run_process

    if runner is run_process or getattr(runner, "__name__", "") in {"run_process", "sprint_runner"}:
        try:
            from planfile import Planfile

            pf = Planfile.auto_discover(project)
            if hasattr(pf, "runnable_report"):
                report = pf.runnable_report(queue=queue_name)
                ids = report.get("servable") if isinstance(report, dict) else None
                if isinstance(ids, list) and all(isinstance(item, str) and item for item in ids):
                    tickets = json.loads(payload, strict=False)
                    admitted = set(ids)
                    if isinstance(tickets, dict):
                        return json.dumps(tickets if tickets.get("id") in admitted else None)
                    return json.dumps([
                        ticket for ticket in tickets
                        if isinstance(ticket, dict) and ticket.get("id") in admitted
                    ])
        except Exception:
            pass

    args = ["ticket", "next", "--debug", "--sprint", "all", "--format", "json"]
    if queue_name:
        args.extend(["--queue", queue_name])
    try:
        result = planfile_command(project, args, runner=runner)
    except OSError as exc:
        raise ValueError("Native Planfile readiness query unavailable; no task was claimed") from exc
    if result.returncode != 0:
        raise ValueError("Native Planfile readiness query failed; no task was claimed")
    try:
        report = json.loads(result.stdout)
        ids = report.get("servable") if isinstance(report, dict) else None
        if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
            raise ValueError("Invalid servable ticket IDs")
        tickets = json.loads(payload, strict=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("Native Planfile readiness report is invalid or unsupported") from exc
    admitted = set(ids)
    if isinstance(tickets, dict):
        return json.dumps(tickets if tickets.get("id") in admitted else None)
    return json.dumps([
        ticket for ticket in tickets
        if isinstance(ticket, dict) and ticket.get("id") in admitted
    ])
