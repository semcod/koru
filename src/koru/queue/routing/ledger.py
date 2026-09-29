"""SQLite ledger for transactional daily benchmark campaigns and probe evidence."""
from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from .contracts import ProbeResult

_T = TypeVar("_T")


def current_local_day() -> str:
    """Return today's date in local system timezone (YYYY-MM-DD), honoring DST."""
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite tables for campaigns and probe records."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            day TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            claim_token TEXT NOT NULL,
            claimed_at TEXT NOT NULL,
            finished_at TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS probes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            candidate_id TEXT NOT NULL,
            task_key TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            validator_digest TEXT,
            tokens INTEGER,
            cost REAL,
            detail TEXT,
            created_at TEXT NOT NULL
        );
    """)
    return conn


def _with_conn(db_path: Path, fn: Callable[[sqlite3.Connection], _T]) -> _T:
    """Run ``fn`` on a freshly initialized connection, always closing it."""
    conn = init_db(db_path)
    try:
        return fn(conn)
    finally:
        conn.close()


def claim_daily_campaign(
    db_path: Path,
    day: str | None = None,
    claim_token: str | None = None,
    stale_timeout_seconds: int = 3600,
) -> tuple[bool, str]:
    """Attempt to claim the daily campaign in a transactional boundary (AC-02).

    Returns (claimed, token). If another process claimed it or it is already
    completed for the day, returns (False, token). Recovers stale running claims.
    """
    day = day or current_local_day()
    token = claim_token or uuid.uuid4().hex
    now_iso = datetime.now(UTC).isoformat()

    def _claim(conn: sqlite3.Connection) -> tuple[bool, str]:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute("SELECT status, claim_token, claimed_at FROM campaigns WHERE day = ?", (day,))
            row = cursor.fetchone()

            if row is not None:
                status, existing_token, claimed_at = row
                if status == "completed":
                    conn.execute("COMMIT")
                    return False, existing_token

                # Check if previous claim is stale
                try:
                    claimed_dt = datetime.fromisoformat(claimed_at)
                    age = (datetime.now(UTC) - claimed_dt).total_seconds()
                except Exception:
                    age = stale_timeout_seconds + 1

                if age > stale_timeout_seconds:
                    # Stale claim takeover
                    conn.execute(
                        "UPDATE campaigns SET status = 'claimed', claim_token = ?, claimed_at = ? WHERE day = ?",
                        (token, now_iso, day),
                    )
                    conn.execute("COMMIT")
                    return True, token

                conn.execute("COMMIT")
                return False, existing_token

            # Unclaimed day: insert new record
            conn.execute(
                "INSERT INTO campaigns (day, status, claim_token, claimed_at) VALUES (?, 'claimed', ?, ?)",
                (day, token, now_iso),
            )
            conn.execute("COMMIT")
            return True, token
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            return False, token

    return _with_conn(db_path, _claim)


def complete_daily_campaign(
    db_path: Path,
    day: str | None = None,
    claim_token: str | None = None,
    status: str = "completed",
) -> None:
    """Mark daily campaign finished."""
    day = day or current_local_day()
    now_iso = datetime.now(UTC).isoformat()

    def _complete(conn: sqlite3.Connection) -> None:
        if claim_token:
            conn.execute(
                "UPDATE campaigns SET status = ?, finished_at = ? WHERE day = ? AND claim_token = ?",
                (status, now_iso, day, claim_token),
            )
        else:
            conn.execute(
                "UPDATE campaigns SET status = ?, finished_at = ? WHERE day = ?",
                (status, now_iso, day),
            )

    _with_conn(db_path, _complete)


def record_probe(
    db_path: Path,
    day: str,
    candidate_id: str,
    task_key: str,
    probe: ProbeResult,
) -> None:
    """Record a verified or failed probe outcome."""
    now_iso = datetime.now(UTC).isoformat()

    def _record(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO probes (
                day, candidate_id, task_key, status, duration_ms,
                validator_digest, tokens, cost, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day,
                candidate_id,
                task_key,
                probe.status,
                probe.duration_ms,
                probe.validator_digest,
                probe.tokens,
                probe.cost,
                probe.detail,
                now_iso,
            ),
        )

    _with_conn(db_path, _record)


def get_latest_daily_probes(
    db_path: Path,
    day: str | None = None,
) -> dict[str, ProbeResult]:
    """Retrieve all probe results for a given day."""
    day = day or current_local_day()
    if not db_path.exists():
        return {}

    def _load(conn: sqlite3.Connection) -> dict[str, ProbeResult]:
        cursor = conn.execute(
            """
            SELECT candidate_id, task_key, status, duration_ms, validator_digest, tokens, cost, detail
            FROM probes
            WHERE day = ?
            ORDER BY id ASC
            """,
            (day,),
        )
        evidence: dict[str, ProbeResult] = {}
        for row in cursor.fetchall():
            cand_id, task_key, status, dur, digest, tok, cost, det = row
            res = ProbeResult(
                status=status,
                duration_ms=dur,
                validator_digest=digest or "",
                tokens=tok,
                cost=cost,
                detail=det or "",
            )
            # Store both specific (cand_id:task_key) and general (cand_id)
            evidence[f"{cand_id}:{task_key}"] = res
            evidence[cand_id] = res
        return evidence

    return _with_conn(db_path, _load)


def get_campaign_history(
    db_path: Path,
    limit: int = 30,
) -> list[dict[str, object]]:
    """Return recent daily campaign summaries."""
    if not db_path.exists():
        return []

    def _history(conn: sqlite3.Connection) -> list[dict[str, object]]:
        cursor = conn.execute(
            """
            SELECT c.day, c.status, c.claimed_at, c.finished_at, COUNT(p.id) as probe_count
            FROM campaigns c
            LEFT JOIN probes p ON c.day = p.day
            GROUP BY c.day
            ORDER BY c.day DESC
            LIMIT ?
            """,
            (limit,),
        )
        history = []
        for row in cursor.fetchall():
            day, status, claimed_at, finished_at, probe_count = row
            history.append({
                "day": day,
                "status": status,
                "claimed_at": claimed_at,
                "finished_at": finished_at,
                "probe_count": probe_count,
            })
        return history

    return _with_conn(db_path, _history)
