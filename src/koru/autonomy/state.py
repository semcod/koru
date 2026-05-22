"""Autoloop state definition for autonomous cycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AutoloopState:
    previous_signature: str = ""
    stagnation_streak: int = 0
    scan_clean_streak: int = 0
    scan_last_head: str = ""
    wup_seen_events: int = 0
    autopilot_events: list[dict[str, Any]] = field(default_factory=list)
    last_message_sent_ts: float = 0.0
    telemetry_autopilot_idle_streak_skips: int = 0
    telemetry_scan_after_idle_runs: int = 0
    telemetry_scan_after_idle_tickets_applied: int = 0
    last_scan_after_idle_ts: float = -1.0
    pending_ide_verify_id: str | None = None
    post_verify_seen: set[str] = field(default_factory=set)

