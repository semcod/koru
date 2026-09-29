"""Read native Planfile readiness through the configured CLI transport."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from koru.queue.ticket import planfile_command
from koru.queue.types import CommandResult


def _is_sdk_runner(runner: Callable[[list[str], Path], CommandResult]) -> bool:
    from koru.queue.runners import run_process

    return runner is run_process or getattr(runner, "__name__", "") in {
        "run_process",
        "sprint_runner",
    }


def _servable_ids(report: object) -> list[str] | None:
    ids = report.get("servable") if isinstance(report, dict) else None
    if isinstance(ids, list) and all(isinstance(item, str) and item for item in ids):
        return ids
    return None


def _filter_tickets(payload: str, admitted: set[str]) -> str:
    tickets = json.loads(payload, strict=False)
    if isinstance(tickets, dict):
        return json.dumps(tickets if tickets.get("id") in admitted else None)
    return json.dumps([
        ticket
        for ticket in tickets
        if isinstance(ticket, dict) and ticket.get("id") in admitted
    ])


def _sdk_admitted_payload(
    project: Path, payload: str, queue_name: str | None
) -> str | None:
    try:
        from planfile import Planfile

        pf = Planfile.auto_discover(project)
        if not hasattr(pf, "runnable_report"):
            return None
        ids = _servable_ids(pf.runnable_report(queue=queue_name))
        if ids is None:
            return None
        return _filter_tickets(payload, set(ids))
    except Exception:
        return None


def _cli_servable_ids(
    project: Path,
    runner: Callable[[list[str], Path], CommandResult],
    queue_name: str | None,
) -> list[str]:
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
        ids = _servable_ids(json.loads(result.stdout))
    except (ValueError, TypeError) as exc:
        raise ValueError("Native Planfile readiness report is invalid or unsupported") from exc
    if ids is None:
        raise ValueError("Native Planfile readiness report is invalid or unsupported")
    return ids


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
    if _is_sdk_runner(runner):
        admitted = _sdk_admitted_payload(project, payload, queue_name)
        if admitted is not None:
            return admitted
    return _filter_tickets(payload, set(_cli_servable_ids(project, runner, queue_name)))
