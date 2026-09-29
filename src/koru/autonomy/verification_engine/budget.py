"""Per-ticket drive budget persistence (failures and reserved attempts)."""

import sqlite3
from contextlib import closing
from pathlib import Path


def _drive_budget_db(project: Path) -> sqlite3.Connection:
    path = project / ".planfile" / ".koru" / "drive-budget.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS failures (ticket TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS attempts (ticket TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        return db
    except sqlite3.Error:
        db.close()
        raise


def record_unsuccessful_drive(project: Path, ticket: str) -> None:
    """Persist failure count independently of waiting streak and loop restarts."""
    if not ticket:
        return
    with closing(_drive_budget_db(project)) as db, db:
        db.execute(
            "INSERT INTO failures VALUES (?, 1) ON CONFLICT(ticket) DO UPDATE SET count=count+1",
            (ticket,),
        )


def drive_budget_exhausted(project: Path, ticket: str, limit: int = 3) -> bool:
    """Storage errors close admission; failures need an explicit ticket repair."""
    if not ticket:
        return False
    try:
        with closing(_drive_budget_db(project)) as db, db:
            counts = _drive_budget_counts(db, ticket)
        return max(counts) >= limit
    except (OSError, sqlite3.Error):
        return True


def _drive_budget_counts(db: sqlite3.Connection, ticket: str) -> tuple[int, int]:
    counts = []
    for table in ("failures", "attempts"):
        row = db.execute(f"SELECT count FROM {table} WHERE ticket=?", (ticket,)).fetchone()
        counts.append(int(row[0]) if row else 0)
    return counts[0], counts[1]


def reserve_drive_attempt(project: Path, ticket: str, limit: int = 3) -> bool:
    """Reserve before a paid shell call, atomically; crashes cannot erase attempts.

    The protected finalizer owns completion. Unverified shell calls share the
    admission budget with failed GUI drives; separate counts avoid double debit.
    """
    if not ticket:
        return True
    try:
        with closing(_drive_budget_db(project)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if max(_drive_budget_counts(db, ticket)) >= limit:
                return False
            db.execute(
                "INSERT INTO attempts VALUES (?, 1) ON CONFLICT(ticket) DO UPDATE SET count=count+1",
                (ticket,),
            )
        return True
    except (OSError, sqlite3.Error):
        return False


# ---------------------------------------------------------------------------
# Verdict logic (pure heuristics, no LLM)
