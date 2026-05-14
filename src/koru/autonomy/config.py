"""Unified autoloop configuration model.

This module provides a single source of truth for autoloop configuration,
mapping 1:1 between shell environment variables (koru-autoloop.sh) and
Python CLI arguments (koru autonomous up).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


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
    backoff_on_stagnation: bool = True
    max_sleep_seconds: int = 900
    scan_skip_if_clean: bool = False
    scan_skip_after: int = 1

    # Topology integration
    topology_integration: bool = True

    @classmethod
    def from_env(cls) -> "AutonomyConfig":
        """Create config from environment variables (shell compatibility)."""
        import os

        return cls(
            project=Path(os.getenv("PROJECT", str(Path.cwd()))),
            actor=os.getenv("ACTOR", os.getenv("ACTOR_NAME", "koru-shell")),
            queue_name=os.getenv("QUEUE_NAME", ""),
            use_all_queues=os.getenv("USE_ALL_QUEUES", "false").lower() == "true",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
            max_cycles=int(os.getenv("MAX_CYCLES", "0")),
            sleep_seconds=int(os.getenv("SLEEP_SECONDS", "120")),
            initial_delay_seconds=int(os.getenv("INITIAL_DELAY_SECONDS", "0")),
            enable_scan=os.getenv("ENABLE_SCAN", "true").lower() == "true",
            ticket_sources=os.getenv("TICKET_SOURCES", "queue"),
            enable_interactive=os.getenv("ENABLE_INTERACTIVE", "false").lower() == "true",
            enable_autopilot_drive=os.getenv("ENABLE_AUTOPILOT_DRIVE", "true").lower() == "true",
            autopilot_action=os.getenv("AUTOPILOT_ACTION", "drive"),
            autopilot_ide=os.getenv("AUTOPILOT_IDE", "auto"),
            autopilot_submit=os.getenv("AUTOPILOT_SUBMIT", "true").lower() == "true",
            autopilot_on_idle_only=os.getenv("AUTOPILOT_ON_IDLE_ONLY", "false").lower() == "true",
            autopilot_skip_on_diagnostics_fail=os.getenv("AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL", "true").lower() == "true",
            drive_prompt=os.getenv("DRIVE_PROMPT", "continue with the next ticket"),
            enable_idle_diagnostics=os.getenv("ENABLE_IDLE_DIAGNOSTICS", "false").lower() == "true",
            idle_diagnostics_profile=os.getenv("IDLE_DIAGNOSTICS_PROFILE", "off"),
            strict_diagnostics=os.getenv("STRICT_DIAGNOSTICS", "false").lower() == "true",
            enable_diagnostic_tickets=os.getenv("ENABLE_DIAGNOSTIC_TICKETS", "false").lower() == "true",
            diagnostic_ticket_queue=os.getenv("DIAGNOSTIC_TICKET_QUEUE", "default"),
            diagnostic_ticket_priority=os.getenv("DIAGNOSTIC_TICKET_PRIORITY", "high"),
            diag_state_dir=Path(os.getenv("DIAG_STATE_DIR", ".planfile/.koru/autoloop-diag")),
            autopilot_skip_statuses=os.getenv("AUTOPILOT_SKIP_STATUSES", "waiting_input"),
            backoff_on_stagnation=os.getenv("BACKOFF_ON_STAGNATION", "true").lower() == "true",
            max_sleep_seconds=int(os.getenv("MAX_SLEEP_SECONDS", "900")),
            scan_skip_if_clean=os.getenv("SCAN_SKIP_IF_CLEAN", "false").lower() == "true",
            scan_skip_after=int(os.getenv("SCAN_SKIP_AFTER", "1")),
            topology_integration=os.getenv("TOPOLOGY_INTEGRATION", "true").lower() == "true",
        )


__all__ = ["AutonomyConfig"]
