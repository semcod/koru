-- Repair-run store, schema v1.
--
-- One row in repair_runs is the durable identity of a repair; everything else
-- hangs off it. UNIQUE(ticket_id, project_root) makes "one live repair per
-- ticket per checkout" a database fact rather than a convention, and the
-- UNIQUE constraints on events and attempts are what make replay and
-- double-workers impossible instead of merely discouraged.

CREATE TABLE IF NOT EXISTS repair_runs (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    project_root TEXT NOT NULL,
    status TEXT NOT NULL,
    current_iteration INTEGER NOT NULL DEFAULT 0,
    max_iterations INTEGER NOT NULL,
    base_head TEXT,
    manifest_hash TEXT,
    context_hash TEXT,
    lease_owner TEXT,
    lease_expires_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(ticket_id, project_root)
);

CREATE TABLE IF NOT EXISTS repair_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES repair_runs(id),
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, sequence),
    UNIQUE(idempotency_key)
);

CREATE TABLE IF NOT EXISTS model_attempts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES repair_runs(id),
    iteration INTEGER NOT NULL,
    attempt INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_code TEXT,
    input_hash TEXT NOT NULL,
    output_hash TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(run_id, iteration, attempt)
);

CREATE TABLE IF NOT EXISTS repair_facts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES repair_runs(id),
    schema_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    source TEXT NOT NULL,
    value_hash TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    expires_at TEXT,
    UNIQUE(run_id, schema_id, fact_key, value_hash)
);

CREATE TABLE IF NOT EXISTS repair_artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES repair_runs(id),
    kind TEXT NOT NULL,
    artifact_ref TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
