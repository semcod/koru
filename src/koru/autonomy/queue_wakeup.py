"""Read-only wakeup for plain idle queue waits, never a dispatch authority."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from koru.autonomy.env import effective_ticket_source_flags
from koru.queue.admission import admitted_payload
from koru.queue.ticket import parse_next_ticket, planfile_command

POLL_SECONDS = 5.0
RECHECK_SECONDS = 60.0


def _queue_revision(project: Path) -> tuple:
    """Observe canonical YAML/shards, excluding read caches and our own logs."""
    paths = [project / "planfile.yaml", project / ".planfile/config.yaml"]
    sprints = project / ".planfile/sprints"
    if sprints.is_dir():
        paths.extend(
            p
            for p in sprints.rglob("*")
            if p.suffix in {".yaml", ".yml", ".json"} and not p.name.endswith(".fast.json")
        )
    revision = []
    for path in sorted(paths):
        try:
            stat = path.stat()
            revision.append((str(path), stat.st_mtime_ns, stat.st_size))
        except OSError:
            continue
    return tuple(revision)


def _read_command(command, project):
    return subprocess.run(
        command,
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env={**os.environ, "COLUMNS": "10000", "TERM": "dumb", "PYTHONIOENCODING": "utf-8"},
    )


def has_ready_machine_work(project: Path, queue_name: str | None) -> bool:
    """Reuse both native admission and the actual current-queue selector."""
    try:
        result = planfile_command(
            project,
            ["ticket", "list", "--status", "open", "--format", "json"],
            runner=_read_command,
        )
        if result.returncode != 0:
            return False
        payload = admitted_payload(project, result.stdout, runner=_read_command, queue_name=queue_name)
        ticket = parse_next_ticket(payload, queue_name=queue_name)
        return bool(
            ticket and (ticket.get("executor") or {}).get("kind") in {"shell", "api", "llm", "taskand", "process"}
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False


def sleep_until_queue_ready(
    context, seconds, *, sleep, now=time.monotonic, ready=has_ready_machine_work, revision=_queue_revision
) -> bool:
    """Return true only when an eligible arrival interrupts a plain idle wait.

    File changes trigger readiness checks within five seconds. A periodic check
    also covers time-based readiness and storage formats without a file signal.
    Failure/provider waits keep their original duration. No ticket is claimed.
    """
    project = Path(context.project)
    queue = context.queue_result
    if (
        seconds <= POLL_SECONDS
        or queue.last_status != "idle"
        or getattr(queue, "failed", ())
        or getattr(queue, "waiting", ())
        or context.autopilot_status not in {"skipped(idle_no_ticket)", "skipped(disabled)"}
        or getattr(context.diag_result, "status", "") not in {"ok", "skipped"}
        or not (project / ".planfile").is_dir()
    ):
        sleep(seconds)
        return False
    _, all_queues = effective_ticket_source_flags(getattr(context.args, "ticket_sources", "queue"))
    queue_name = None if all_queues else getattr(context.args, "queue_name", "default")
    deadline = now() + seconds
    last_revision = None
    next_check = now()
    while now() < deadline:
        try:
            observed = revision(project)
        except OSError:
            observed = last_revision  # Metadata failure falls back to periodic readiness.
        if observed != last_revision or now() >= next_check:
            last_revision = observed
            if ready(project, queue_name):
                return True
            next_check = now() + RECHECK_SECONDS
        remaining = deadline - now()
        if remaining > 0:
            sleep(min(POLL_SECONDS, remaining))
    return False
