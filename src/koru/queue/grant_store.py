"""Replay protection: every grant's ``jti`` is spent exactly once.

A valid signature proves local control said yes — once. This store makes the
"once" durable: the first claim wins via ``O_CREAT|O_EXCL`` (the filesystem's
own atomicity, no lock daemon), every later claim of the same ``jti`` is
refused, and a claim interrupted by a crash can be *reclaimed* only by the same
run against the same manifest after its lease expires. A new grant for a
different manifest can never resume an old transaction — that would let a
stale permission authorize work it never described.

States: ``processing → completed | failed``. Terminal states never reopen.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

STATE_PROCESSING = "processing"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"

DEFAULT_LEASE_S = 900


@dataclass(frozen=True)
class ClaimDecision:
    ok: bool
    reason: str


def claim_jti(
    project: Path,
    jti: str,
    *,
    run_id: str,
    manifest_hash: str,
    lease_s: int = DEFAULT_LEASE_S,
    now: datetime | None = None,
) -> ClaimDecision:
    """Atomically take the one right to act on this grant.

    First writer wins; a crash mid-transaction leaves ``processing`` with a
    lease, and only the same run with the same manifest may pick that up after
    the lease runs out. Everything else is a replay and is refused.
    """
    if not jti or "/" in jti or "." in jti:
        return ClaimDecision(False, "jti is missing or malformed")
    moment = now or datetime.now(UTC)
    path = _jti_path(project, jti)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "jti": jti,
        "state": STATE_PROCESSING,
        "run_id": run_id,
        "manifest_hash": manifest_hash,
        "claimed_at": moment.isoformat(),
        "lease_expires_at": (moment + timedelta(seconds=lease_s)).isoformat(),
    }

    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return _reclaim(path, record, moment)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    return ClaimDecision(True, "claimed")


def complete_jti(project: Path, jti: str) -> None:
    """Mark the grant spent for good."""
    _transition(project, jti, STATE_COMPLETED)


def fail_jti(project: Path, jti: str) -> None:
    """Mark the grant consumed by a failed run — failure also spends it."""
    _transition(project, jti, STATE_FAILED)


def jti_state(project: Path, jti: str) -> str | None:
    record = _read(_jti_path(project, jti))
    return record.get("state") if record else None


def _reclaim(path: Path, record: dict, moment: datetime) -> ClaimDecision:
    """Decide whether an existing claim may be taken over."""
    existing = _read(path)
    if existing is None:
        return ClaimDecision(False, "jti record exists but is unreadable — refusing")
    state = existing.get("state")
    if state in {STATE_COMPLETED, STATE_FAILED}:
        return ClaimDecision(False, f"grant jti was already spent ({state}) — replay refused")
    if state != STATE_PROCESSING:
        return ClaimDecision(False, f"grant jti is in unknown state {state!r} — refusing")

    if (
        existing.get("run_id") != record["run_id"]
        or existing.get("manifest_hash") != record["manifest_hash"]
    ):
        return ClaimDecision(
            False,
            "grant jti is claimed by a different run or manifest — a new grant "
            "cannot resume an old transaction",
        )
    try:
        lease_expires = datetime.fromisoformat(str(existing.get("lease_expires_at")))
    except (TypeError, ValueError):
        return ClaimDecision(False, "jti lease is unreadable — refusing")
    if moment < lease_expires:
        return ClaimDecision(False, "grant jti is being processed and its lease has not expired")

    # Same run, same manifest, lease expired: the original process died and
    # this is its own recovery finishing the same transaction.
    _write_atomic(path, record)
    return ClaimDecision(True, "reclaimed after lease expiry by the same run")


def _transition(project: Path, jti: str, state: str) -> None:
    path = _jti_path(project, jti)
    record = _read(path)
    if record is None or record.get("state") != STATE_PROCESSING:
        return  # terminal states never reopen; missing records stay missing
    record["state"] = state
    _write_atomic(path, record)


def _jti_path(project: Path, jti: str) -> Path:
    return project / ".koru" / "grants" / f"{jti}.json"


def _read(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _write_atomic(path: Path, record: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
