-- Repair-run store, schema v2: per-run grant replay protection.
--
-- A signed apply-grant authorizes exactly one mutation. Recording its jti here
-- with UNIQUE(grant_jti) makes replay a database impossibility: a second
-- attempt to use the same grant — within a run or across a restart/resume —
-- fails the INSERT instead of relying on in-memory state that a crash would
-- lose. run_id ties the use to the run that consumed it, for audit.

CREATE TABLE IF NOT EXISTS used_grants (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES repair_runs(id),
    grant_jti TEXT NOT NULL,
    grant_hash TEXT NOT NULL,
    used_at TEXT NOT NULL,
    UNIQUE(grant_jti)
);

CREATE INDEX IF NOT EXISTS idx_used_grants_run ON used_grants(run_id);
