"""Locking and coordination utilities for the planfile queue."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from .types import CommandResult, QueueRunResult


def queue_lock_wanted() -> bool:
    """Check if queue locking is enabled via environment variable."""
    v = os.environ.get("KORU_QUEUE_RUNNER_LOCK", "1").strip().lower()
    return v not in {"0", "false", "no", "off"}


@contextlib.contextmanager
def queue_runner_lock(project: Path):
    """Serialize ``run_next_planfile_task`` per project (POSIX ``flock``).

    Prevents multiple IDE/terminal koru drains from picking the same open
    ticket. Set ``KORU_QUEUE_RUNNER_LOCK=0`` to disable (not recommended when
    several agents share one ``.planfile``).
    """
    if not queue_lock_wanted() or os.name != "posix":
        yield
        return

    import fcntl

    lock_dir = project / ".planfile" / ".koru"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "queue-runner.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def claim_lease_seconds_str() -> str:
    """Get the ticket lease duration in seconds from environment."""
    raw = os.environ.get("KORU_TICKET_LEASE_SECONDS", "3600").strip()
    try:
        n = int(raw, 10)
    except ValueError:
        return "3600"
    return str(max(60, min(n, 86400 * 7)))


def ticket_claim_or_error(
    project: Path,
    ticket_id: str,
    actor: str,
    *,
    planfile_runner: Callable[[Sequence[str], Path], CommandResult],
) -> QueueRunResult | None:
    """Run ``planfile ticket claim``; return ``QueueRunResult`` on CLI failure."""
    from .ticket import planfile_command

    claim = planfile_command(
        project,
        [
            "ticket",
            "claim",
            ticket_id,
            "--assigned-to",
            actor,
            "--lease-seconds",
            claim_lease_seconds_str(),
        ],
        runner=planfile_runner,
    )
    if claim.returncode != 0:
        return QueueRunResult(
            status="claim_failed",
            ticket_id=ticket_id,
            message=(claim.stderr or claim.stdout or "ticket claim failed").strip(),
            exit_code=claim.returncode,
            stdout=claim.stdout,
            stderr=claim.stderr,
        )
    return None
