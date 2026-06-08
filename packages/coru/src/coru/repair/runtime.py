"""Lane repair runtime — public entry for control-layer handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from coru.repair.domain import RepairPlan


def run_lane_repair(
    ide: str,
    instance: str,
    *,
    trigger: str = "dsl2koru",
    project_root: Path | None = None,
    payload: dict[str, Any] | None = None,
) -> RepairPlan:
    """Run the full lane repair pipeline (same callbacks as ``coru repair run``)."""
    del project_root  # reserved for future explicit project routing
    from coru.cli import _run_lane_repair

    return _run_lane_repair(ide, instance, payload=payload, trigger=trigger)
