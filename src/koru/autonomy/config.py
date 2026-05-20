"""Unified autoloop configuration model.

This module provides a single source of truth for autoloop configuration,
mapping 1:1 between shell environment variables (koru-autoloop.sh) and
Python CLI arguments (koru autonomous up).
"""


from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from koru.autonomy.env import env_truthy


@dataclass(frozen=True)
class AutonomyConfig:
    """Configuration for autonomous loop (unified shell + Python).

    Fields map 1:1 to environment variables in scripts/koru-autoloop.sh.
    """

    # Core
    project: Path = field(default_factory=Path.cwd)
    actor: str = "koru-shell"
    queue_name: str = ""
    use_all_queues: bool = False
    max_iterations: int = 50
    max_cycles: int = 0  # 0 = infinite
    sleep_seconds: int = 120
    initial_delay_seconds: int = 0

    # Intake
    enable_scan: bool = True
    ticket_sources: Literal["queue", "scan", "all"] = "queue"

    # Execution
    enable_interactive: bool = False

    # Autopilot
    enable_autopilot_drive: bool = True
    autopilot_action: Literal["drive", "handoff", "off"] = "drive"
    autopilot_ide: str = "auto"
    autopilot_submit: bool = True
    autopilot_on_idle_only: bool = False
    autopilot_skip_on_diagnostics_fail: bool = True
    drive_prompt: str = "continue with the next ticket"

    # Diagnostics
    enable_idle_diagnostics: bool = False
    idle_diagnostics_profile: Literal["off", "quick", "full"] = "off"
    strict_diagnostics: bool = False
    enable_diagnostic_tickets: bool = False
    diagnostic_ticket_queue: str = "default"
    diagnostic_ticket_priority: str = "high"
    diag_state_dir: Path = field(default_factory=lambda: Path(".planfile/.koru/autoloop-diag"))

    # Stagnation control
    autopilot_skip_statuses: str = "waiting_input"
    autopilot_skip_drive_idle_streak: int = 0
    backoff_on_stagnation: bool = True
    max_sleep_seconds: int = 900
    scan_skip_if_clean: bool = False
    scan_skip_after: int = 1

    # Topology integration
    topology_integration: bool = True

    @classmethod
    def from_env(cls) -> AutonomyConfig:
        """Create config from environment variables (shell compatibility)."""
        import os

        _idle_raw = os.getenv("AUTOPILOT_SKIP_DRIVE_IDLE_STREAK", "0")
        autopilot_skip_drive_idle_streak = 0
        if _idle_raw is not None and str(_idle_raw).strip():
            try:
                autopilot_skip_drive_idle_streak = max(0, int(str(_idle_raw).strip()))
            except ValueError:
                autopilot_skip_drive_idle_streak = 0

        return cls(
            project=Path(os.getenv("PROJECT", str(Path.cwd()))),
            actor=os.getenv("ACTOR", os.getenv("ACTOR_NAME", "koru-shell")),
            queue_name=os.getenv("QUEUE_NAME", ""),
            use_all_queues=env_truthy("USE_ALL_QUEUES", False),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
            max_cycles=int(os.getenv("MAX_CYCLES", "0")),
            sleep_seconds=int(os.getenv("SLEEP_SECONDS", "120")),
            initial_delay_seconds=int(os.getenv("INITIAL_DELAY_SECONDS", "0")),
            enable_scan=env_truthy("ENABLE_SCAN", True),
            ticket_sources=os.getenv("TICKET_SOURCES", "queue"),  # type: ignore[arg-type]
            enable_interactive=env_truthy("ENABLE_INTERACTIVE", False),
            enable_autopilot_drive=env_truthy("ENABLE_AUTOPILOT_DRIVE", True),
            autopilot_action=os.getenv("AUTOPILOT_ACTION", "drive"),  # type: ignore[arg-type]
            autopilot_ide=os.getenv("AUTOPILOT_IDE", "auto"),
            autopilot_submit=env_truthy("AUTOPILOT_SUBMIT", True),
            autopilot_on_idle_only=env_truthy("AUTOPILOT_ON_IDLE_ONLY", False),
            autopilot_skip_on_diagnostics_fail=env_truthy(
                "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL",
                True,
            ),
            drive_prompt=os.getenv("DRIVE_PROMPT", "continue with the next ticket"),
            enable_idle_diagnostics=env_truthy("ENABLE_IDLE_DIAGNOSTICS", False),
            idle_diagnostics_profile=os.getenv("IDLE_DIAGNOSTICS_PROFILE", "off"),  # type: ignore[arg-type]
            strict_diagnostics=env_truthy("STRICT_DIAGNOSTICS", False),
            enable_diagnostic_tickets=env_truthy("ENABLE_DIAGNOSTIC_TICKETS", False),
            diagnostic_ticket_queue=os.getenv("DIAGNOSTIC_TICKET_QUEUE", "default"),
            diagnostic_ticket_priority=os.getenv("DIAGNOSTIC_TICKET_PRIORITY", "high"),
            diag_state_dir=Path(os.getenv("DIAG_STATE_DIR", ".planfile/.koru/autoloop-diag")),
            autopilot_skip_statuses=os.getenv("AUTOPILOT_SKIP_STATUSES", "waiting_input"),
            autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
            backoff_on_stagnation=env_truthy("BACKOFF_ON_STAGNATION", True),
            max_sleep_seconds=int(os.getenv("MAX_SLEEP_SECONDS", "900")),
            scan_skip_if_clean=env_truthy("SCAN_SKIP_IF_CLEAN", False),
            scan_skip_after=int(os.getenv("SCAN_SKIP_AFTER", "1")),
            topology_integration=env_truthy("TOPOLOGY_INTEGRATION", True),
        )


__all__ = ["AutonomyConfig"]
