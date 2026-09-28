"""Tests for daily transactional benchmark campaigns and SQLite ledger."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.queue.benchmark_router import run_daily_benchmark_campaign
from koru.queue.routing.contracts import ProbeResult
from koru.queue.routing.ledger import (
    claim_daily_campaign,
    current_local_day,
    get_campaign_history,
    get_latest_daily_probes,
    init_db,
    record_probe,
)


def test_current_local_day_format() -> None:
    day = current_local_day()
    assert len(day) == 10
    # Must parse as YYYY-MM-DD
    dt = datetime.strptime(day, "%Y-%m-%d")
    assert dt.year >= 2026


def test_transactional_daily_claim_prevents_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "benchmark.sqlite"

    # First process claims
    claimed, claim_id1 = claim_daily_campaign(db_path, day="2026-09-28", claim_token="proc-1")
    assert claimed is True
    assert claim_id1 == "proc-1"

    # Concurrent second process tries to claim the same day -> rejected
    claimed2, claim_id2 = claim_daily_campaign(db_path, day="2026-09-28", claim_token="proc-2")
    assert claimed2 is False
    assert claim_id2 == "proc-1"

    # Different day can be claimed
    claimed3, claim_id3 = claim_daily_campaign(db_path, day="2026-09-29", claim_token="proc-3")
    assert claimed3 is True


def test_daily_claim_stale_recovery(tmp_path: Path) -> None:
    db_path = tmp_path / "benchmark.sqlite"
    conn = init_db(db_path)

    # Insert a stale claim from 2 hours ago
    stale_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    conn.execute(
        "INSERT INTO campaigns (day, status, claim_token, claimed_at) VALUES (?, 'claimed', ?, ?)",
        ("2026-09-28", "stale-proc", stale_time),
    )
    conn.close()

    # New process attempts to claim with 1-hour timeout -> should recover and succeed
    claimed, claim_id = claim_daily_campaign(
        db_path,
        day="2026-09-28",
        claim_token="fresh-proc",
        stale_timeout_seconds=3600,
    )
    assert claimed is True
    assert claim_id == "fresh-proc"


def test_record_and_retrieve_probes(tmp_path: Path) -> None:
    db_path = tmp_path / "benchmark.sqlite"
    probe = ProbeResult(
        status="ok",
        duration_ms=45,
        validator_digest="sha256:abc12345",
        tokens=120,
        cost=0.0002,
        detail="verified pass",
    )
    record_probe(db_path, "2026-09-28", "test-cand", "simple:coding", probe)

    probes = get_latest_daily_probes(db_path, "2026-09-28")
    assert "test-cand:simple:coding" in probes
    loaded = probes["test-cand:simple:coding"]
    assert loaded.status == "ok"
    assert loaded.duration_ms == 45
    assert loaded.validator_digest == "sha256:abc12345"
    assert loaded.cost == 0.0002


def test_run_daily_benchmark_campaign_idempotence(tmp_path: Path) -> None:
    res1 = run_daily_benchmark_campaign(project_root=tmp_path)
    assert res1["status"] == "completed"
    assert "results" in res1

    # Second invocation on the same day without force
    res2 = run_daily_benchmark_campaign(project_root=tmp_path, force=False)
    assert res2["status"] == "already_run_today"

    # Force invocation
    res3 = run_daily_benchmark_campaign(project_root=tmp_path, force=True)
    assert res3["status"] == "completed"

    # Campaign history reflects the day
    history = get_campaign_history(tmp_path / ".planfile" / "benchmark.sqlite")
    assert len(history) >= 1
    assert history[0]["status"] == "completed"
