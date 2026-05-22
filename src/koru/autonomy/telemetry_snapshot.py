"""Last autonomous cycle metrics (JSON) for operators and ``koru --context``."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SNAPSHOT = "autonomy-telemetry.json"


def autonomy_telemetry_path(project: Path) -> Path:
    return project.resolve() / ".planfile" / ".koru" / _SNAPSHOT


def write_autonomy_cycle_telemetry(
    project: Path,
    *,
    cycle: int,
    cumulative: dict[str, int],
    cycle_metrics: dict[str, Any],
    knobs: dict[str, Any],
) -> None:
    path = autonomy_telemetry_path(project)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(UTC).isoformat(),
            "cycle": cycle,
            "cumulative": dict(cumulative),
            "last_cycle": dict(cycle_metrics),
            "knobs": dict(knobs),
        }
        path.write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def build_autonomy_loop_brief(project: Path) -> dict[str, Any]:
    """Subset for ``build_context`` / markdown handoff."""
    p = autonomy_telemetry_path(project)
    snap: dict[str, Any] | None = None
    if p.is_file():
        try:
            snap = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            snap = None

    def _e(name: str) -> str | None:
        raw = os.environ.get(name)
        return raw if raw is not None and str(raw).strip() else None

    hints = {
        k: v
        for k, v in (
            ("TICKET_SOURCES", _e("TICKET_SOURCES")),
            ("SCAN_AFTER_IDLE_QUEUE", _e("SCAN_AFTER_IDLE_QUEUE")),
            ("SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS", _e("SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS")),
            ("AUTOPILOT_SKIP_DRIVE_IDLE_STREAK", _e("AUTOPILOT_SKIP_DRIVE_IDLE_STREAK")),
        )
        if v is not None
    }
    return {
        "telemetry_file": str(p),
        "last_run_snapshot": snap,
        "environment_hints": hints,
    }


__all__ = [
    "autonomy_telemetry_path",
    "build_autonomy_loop_brief",
    "write_autonomy_cycle_telemetry",
]
