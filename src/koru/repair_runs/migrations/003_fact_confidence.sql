-- Repair-run store, schema v3: fact confidence.
--
-- The koru.fact/v1 envelope carries a confidence; storing it as a real column
-- keeps the envelope honest — a value smuggled inside value_json would not
-- survive the value hash contract (same value, different confidence, same
-- hash) and could not be queried.

ALTER TABLE repair_facts ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0;
