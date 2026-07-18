"""SQLite backend of the repair-run store.

WAL journalling, foreign keys, a busy timeout, and every invariant expressed
as a constraint the database enforces rather than a convention the code
remembers: UNIQUE(ticket_id, project_root) for run identity,
UNIQUE(run_id, sequence) and UNIQUE(idempotency_key) for events,
UNIQUE(run_id, iteration, attempt) for model attempts. The atomic lease claim
is a single UPDATE whose WHERE clause encodes the whole policy — zero rows
changed means someone else owns the run.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.repair_runs.lifecycle import TERMINAL_STATES, validate_transition
from koru.repair_runs.models import (
    ModelAttempt,
    RepairArtifact,
    RepairEvent,
    RepairFact,
    RepairRun,
    UsedGrant,
    new_id,
    utcnow,
)
from koru.repair_runs.store import (
    GrantAlreadyUsed,
    RepairRunStore,
    RunAlreadyExists,
    StaleVersion,
    UnknownRun,
)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def default_store_path(project: Path) -> Path:
    return project / ".koru" / "state" / "repair-runs.sqlite3"


class SqliteRepairRunStore(RepairRunStore):
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 5000")
        self._migrate()

    def close(self) -> None:
        self._db.close()

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)",
        )
        applied = {
            row["version"]
            for row in self._db.execute("SELECT version FROM schema_migrations")
        }
        for script in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            version = int(script.name.split("_")[0])
            if version in applied:
                continue
            with self._db:  # one migration, one transaction
                self._db.executescript(script.read_text(encoding="utf-8"))
                self._db.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, applied_at) "
                    "VALUES (?, ?)",
                    (version, utcnow().isoformat()),
                )

    # -- runs ---------------------------------------------------------------
    def create_run(
        self,
        *,
        ticket_id: str,
        project_root: str,
        max_iterations: int,
        now: datetime | None = None,
    ) -> RepairRun:
        moment = now or utcnow()
        run = RepairRun(
            id=new_id("run"),
            ticket_id=ticket_id,
            project_root=project_root,
            status="created",
            max_iterations=max_iterations,
            created_at=moment,
            updated_at=moment,
        )
        try:
            self._db.execute(
                "INSERT INTO repair_runs (id, ticket_id, project_root, status, "
                "current_iteration, max_iterations, version, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.id, run.ticket_id, run.project_root, run.status,
                    run.current_iteration, run.max_iterations, run.version,
                    moment.isoformat(), moment.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise RunAlreadyExists(
                f"a repair run for ticket {ticket_id} in {project_root} already exists",
            ) from error
        return run

    def get_run(self, run_id: str) -> RepairRun | None:
        row = self._db.execute(
            "SELECT * FROM repair_runs WHERE id = ?", (run_id,),
        ).fetchone()
        return _run_from_row(row) if row else None

    def find_run(self, ticket_id: str, project_root: str) -> RepairRun | None:
        row = self._db.execute(
            "SELECT * FROM repair_runs WHERE ticket_id = ? AND project_root = ?",
            (ticket_id, project_root),
        ).fetchone()
        return _run_from_row(row) if row else None

    def transition(
        self,
        run_id: str,
        new_status: str,
        *,
        expected_version: int,
        now: datetime | None = None,
        current_iteration: int | None = None,
        base_head: str | None = None,
        manifest_hash: str | None = None,
        context_hash: str | None = None,
    ) -> RepairRun:
        run = self.get_run(run_id)
        if run is None:
            raise UnknownRun(run_id)
        validate_transition(run.status, new_status)
        moment = now or utcnow()
        cursor = self._db.execute(
            "UPDATE repair_runs SET status = ?, version = version + 1, updated_at = ?, "
            "current_iteration = COALESCE(?, current_iteration), "
            "base_head = COALESCE(?, base_head), "
            "manifest_hash = COALESCE(?, manifest_hash), "
            "context_hash = COALESCE(?, context_hash) "
            "WHERE id = ? AND version = ?",
            (
                new_status, moment.isoformat(), current_iteration,
                base_head, manifest_hash, context_hash,
                run_id, expected_version,
            ),
        )
        if cursor.rowcount == 0:
            raise StaleVersion(
                f"run {run_id} moved past version {expected_version}; re-read and retry",
            )
        refreshed = self.get_run(run_id)
        assert refreshed is not None
        return refreshed

    # -- leasing ------------------------------------------------------------
    def claim(
        self,
        run_id: str,
        owner: str,
        *,
        lease_s: int,
        now: datetime | None = None,
    ) -> RepairRun | None:
        moment = now or utcnow()
        expires = (moment + timedelta(seconds=lease_s)).isoformat()
        cursor = self._db.execute(
            "UPDATE repair_runs SET lease_owner = ?, lease_expires_at = ?, "
            "version = version + 1, updated_at = ? "
            "WHERE id = ? AND ("
            "  lease_expires_at IS NULL"
            "  OR lease_expires_at < ?"
            "  OR lease_owner = ?"
            ")",
            (owner, expires, moment.isoformat(), run_id, moment.isoformat(), owner),
        )
        if cursor.rowcount == 0:
            return None
        return self.get_run(run_id)

    def release(self, run_id: str, owner: str) -> None:
        self._db.execute(
            "UPDATE repair_runs SET lease_owner = NULL, lease_expires_at = NULL, "
            "version = version + 1 WHERE id = ? AND lease_owner = ?",
            (run_id, owner),
        )

    # -- events -------------------------------------------------------------
    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict,
        *,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> RepairEvent:
        moment = now or utcnow()
        existing = self._db.execute(
            "SELECT * FROM repair_events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return _event_from_row(existing)
        try:
            with self._db:
                self._db.execute("BEGIN IMMEDIATE")
                sequence = self._db.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next "
                    "FROM repair_events WHERE run_id = ?",
                    (run_id,),
                ).fetchone()["next"]
                self._db.execute(
                    "INSERT INTO repair_events (run_id, sequence, event_type, "
                    "payload_json, idempotency_key, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id, sequence, event_type,
                        json.dumps(payload, sort_keys=True), idempotency_key,
                        moment.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError:
            # A concurrent writer beat us to this key; their event is the truth.
            raced = self._db.execute(
                "SELECT * FROM repair_events WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if raced:
                return _event_from_row(raced)
            raise
        recorded = self._db.execute(
            "SELECT * FROM repair_events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return _event_from_row(recorded)

    def events(self, run_id: str) -> list[RepairEvent]:
        rows = self._db.execute(
            "SELECT * FROM repair_events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        return [_event_from_row(row) for row in rows]

    # -- model attempts -----------------------------------------------------
    def start_attempt(
        self,
        run_id: str,
        *,
        iteration: int,
        attempt: int,
        provider: str,
        model: str,
        input_hash: str,
        now: datetime | None = None,
    ) -> ModelAttempt:
        moment = now or utcnow()
        record = ModelAttempt(
            id=new_id("att"),
            run_id=run_id,
            iteration=iteration,
            attempt=attempt,
            provider=provider,
            model=model,
            status="running",
            input_hash=input_hash,
            started_at=moment,
        )
        self._db.execute(
            "INSERT INTO model_attempts (id, run_id, iteration, attempt, provider, "
            "model, status, input_hash, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.id, run_id, iteration, attempt, provider, model,
                record.status, input_hash, moment.isoformat(),
            ),
        )
        return record

    def finish_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        failure_code: str | None = None,
        output_hash: str | None = None,
        now: datetime | None = None,
    ) -> None:
        moment = now or utcnow()
        self._db.execute(
            "UPDATE model_attempts SET status = ?, failure_code = ?, output_hash = ?, "
            "completed_at = ? WHERE id = ?",
            (status, failure_code, output_hash, moment.isoformat(), attempt_id),
        )

    def attempts(self, run_id: str) -> list[ModelAttempt]:
        rows = self._db.execute(
            "SELECT * FROM model_attempts WHERE run_id = ? ORDER BY iteration, attempt",
            (run_id,),
        ).fetchall()
        return [_attempt_from_row(row) for row in rows]

    # -- facts and artifacts ------------------------------------------------
    def put_fact(self, fact: RepairFact) -> RepairFact:
        try:
            self._db.execute(
                "INSERT INTO repair_facts (id, run_id, schema_id, fact_key, value_json, "
                "source, value_hash, observed_at, expires_at, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fact.id, fact.run_id, fact.schema_id, fact.fact_key,
                    json.dumps(fact.value, sort_keys=True), fact.source, fact.value_hash,
                    fact.observed_at.isoformat(),
                    fact.expires_at.isoformat() if fact.expires_at else None,
                    fact.confidence,
                ),
            )
        except sqlite3.IntegrityError:
            pass  # identical fact already recorded — idempotent by value hash
        return fact

    def facts(self, run_id: str, *, now: datetime | None = None) -> list[RepairFact]:
        moment = (now or utcnow()).isoformat()
        rows = self._db.execute(
            "SELECT * FROM repair_facts WHERE run_id = ? "
            "AND (expires_at IS NULL OR expires_at > ?) ORDER BY observed_at",
            (run_id, moment),
        ).fetchall()
        return [_fact_from_row(row) for row in rows]

    def add_artifact(self, artifact: RepairArtifact) -> None:
        self._db.execute(
            "INSERT INTO repair_artifacts (id, run_id, kind, artifact_ref, sha256, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                artifact.id, artifact.run_id, artifact.kind, artifact.artifact_ref,
                artifact.sha256, artifact.created_at.isoformat(),
            ),
        )

    def artifacts(self, run_id: str) -> list[RepairArtifact]:
        rows = self._db.execute(
            "SELECT * FROM repair_artifacts WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return [_artifact_from_row(row) for row in rows]

    # -- grant replay protection --------------------------------------------
    def record_grant_use(self, grant: UsedGrant) -> None:
        try:
            self._db.execute(
                "INSERT INTO used_grants (id, run_id, grant_jti, grant_hash, used_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    grant.id, grant.run_id, grant.grant_jti, grant.grant_hash,
                    grant.used_at.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as error:
            # UNIQUE(grant_jti): the check and the record are one atomic step.
            raise GrantAlreadyUsed(grant.grant_jti) from error

    def is_grant_used(self, grant_jti: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM used_grants WHERE grant_jti = ?", (grant_jti,),
        ).fetchone()
        return row is not None

    def used_grants(self, run_id: str) -> list[UsedGrant]:
        rows = self._db.execute(
            "SELECT * FROM used_grants WHERE run_id = ? ORDER BY used_at", (run_id,),
        ).fetchall()
        return [
            UsedGrant(
                id=row["id"],
                run_id=row["run_id"],
                grant_jti=row["grant_jti"],
                grant_hash=row["grant_hash"],
                used_at=_parse_dt(row["used_at"]) or utcnow(),
            )
            for row in rows
        ]

    # -- recovery -----------------------------------------------------------
    def resumable_runs(self, *, now: datetime | None = None) -> list[RepairRun]:
        moment = (now or utcnow()).isoformat()
        placeholders = ", ".join("?" for _ in TERMINAL_STATES)
        rows = self._db.execute(
            f"SELECT * FROM repair_runs WHERE status NOT IN ({placeholders}) "
            "AND (lease_expires_at IS NULL OR lease_expires_at < ?) "
            "ORDER BY created_at",
            (*TERMINAL_STATES, moment),
        ).fetchall()
        return [_run_from_row(row) for row in rows]


def _parse_dt(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text).astimezone(UTC) if text else None


def _run_from_row(row: sqlite3.Row) -> RepairRun:
    return RepairRun(
        id=row["id"],
        ticket_id=row["ticket_id"],
        project_root=row["project_root"],
        status=row["status"],
        current_iteration=row["current_iteration"],
        max_iterations=row["max_iterations"],
        base_head=row["base_head"],
        manifest_hash=row["manifest_hash"],
        context_hash=row["context_hash"],
        lease_owner=row["lease_owner"],
        lease_expires_at=_parse_dt(row["lease_expires_at"]),
        version=row["version"],
        created_at=_parse_dt(row["created_at"]) or utcnow(),
        updated_at=_parse_dt(row["updated_at"]) or utcnow(),
    )


def _event_from_row(row: sqlite3.Row) -> RepairEvent:
    return RepairEvent(
        id=row["id"],
        run_id=row["run_id"],
        sequence=row["sequence"],
        event_type=row["event_type"],
        payload=json.loads(row["payload_json"]),
        idempotency_key=row["idempotency_key"],
        created_at=_parse_dt(row["created_at"]) or utcnow(),
    )


def _attempt_from_row(row: sqlite3.Row) -> ModelAttempt:
    return ModelAttempt(
        id=row["id"],
        run_id=row["run_id"],
        iteration=row["iteration"],
        attempt=row["attempt"],
        provider=row["provider"],
        model=row["model"],
        status=row["status"],
        failure_code=row["failure_code"],
        input_hash=row["input_hash"],
        output_hash=row["output_hash"],
        started_at=_parse_dt(row["started_at"]) or utcnow(),
        completed_at=_parse_dt(row["completed_at"]),
    )


def _fact_from_row(row: sqlite3.Row) -> RepairFact:
    return RepairFact(
        id=row["id"],
        run_id=row["run_id"],
        schema_id=row["schema_id"],
        fact_key=row["fact_key"],
        value=json.loads(row["value_json"]),
        source=row["source"],
        value_hash=row["value_hash"],
        observed_at=_parse_dt(row["observed_at"]) or utcnow(),
        expires_at=_parse_dt(row["expires_at"]),
        confidence=float(row["confidence"] if "confidence" in row.keys() else 1.0),
    )


def _artifact_from_row(row: sqlite3.Row) -> RepairArtifact:
    return RepairArtifact(
        id=row["id"],
        run_id=row["run_id"],
        kind=row["kind"],
        artifact_ref=row["artifact_ref"],
        sha256=row["sha256"],
        created_at=_parse_dt(row["created_at"]) or utcnow(),
    )
