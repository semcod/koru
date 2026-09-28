"""High-level router and daily benchmark campaign runner."""
from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path

from .routing.classifier import classify_task
from .routing.contracts import Candidate, Decision, Task
from .routing.ledger import (
    claim_daily_campaign,
    complete_daily_campaign,
    current_local_day,
    get_latest_daily_probes,
    record_probe,
)
from .routing.probes import get_default_candidates, run_deterministic_ruff_probe
from .routing.ranking import rank_candidates


def get_benchmark_db_path(project_root: Path | None = None) -> Path:
    """Resolve the SQLite database path for benchmark campaigns."""
    if project_root:
        return project_root.resolve() / ".planfile" / "benchmark.sqlite"
    return Path.home() / ".koru" / "benchmark.sqlite"


def resolve_task_route(
    task: Mapping | Task,
    project_root: Path | None = None,
    explicit_choice: str | None = None,
    candidates: list[Candidate] | None = None,
) -> Decision:
    """Classify task and rank candidates using today's verified benchmark evidence."""
    classified = task if isinstance(task, Task) else classify_task(task)
    db_path = get_benchmark_db_path(project_root)
    day = current_local_day()
    evidence = get_latest_daily_probes(db_path, day)
    cands = candidates or get_default_candidates()

    return rank_candidates(
        task=classified,
        candidates=cands,
        evidence=evidence,
        explicit_choice=explicit_choice,
        evidence_date=day if evidence else None,
    )


def run_daily_benchmark_campaign(
    project_root: Path | None = None,
    force: bool = False,
) -> dict[str, object]:
    """Execute the daily verified benchmark campaign (AC-02, AC-03).

    Ensures only one run per local day under concurrent timer/CLI invocations,
    unless `force=True`. Records verified outcomes into SQLite.
    """
    db_path = get_benchmark_db_path(project_root)
    day = current_local_day()

    if not force:
        claimed, claim_id = claim_daily_campaign(db_path, day=day)
        if not claimed:
            probes = get_latest_daily_probes(db_path, day=day)
            return {
                "status": "already_run_today",
                "day": day,
                "message": "Daily benchmark campaign already executed or running for today.",
                "probes": {k: p.status for k, p in probes.items()},
            }
    else:
        claim_id = "forced"

    # Execute isolated probes
    probe_results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="koru-benchmark-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Deterministic ruff probe
        ruff_result = run_deterministic_ruff_probe(tmp_path)
        record_probe(db_path, day, "deterministic-ruff", "simple:ruff", ruff_result)
        probe_results["deterministic-ruff:simple:ruff"] = {
            "status": ruff_result.status,
            "duration_ms": ruff_result.duration_ms,
            "validator_digest": ruff_result.validator_digest,
            "detail": ruff_result.detail,
        }

    complete_daily_campaign(db_path, day=day, claim_token=claim_id, status="completed")
    return {
        "status": "completed",
        "day": day,
        "results": probe_results,
    }
