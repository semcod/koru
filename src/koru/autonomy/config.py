"""Unified autoloop configuration model.

This module provides a single source of truth for autoloop configuration,
mapping 1:1 between shell environment variables (koru-autoloop.sh) and
Python CLI arguments (koru autonomous up).
"""


from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from koru.autonomy.env import AUTOLOOP_ENV_DEFAULTS, env_get, env_int, env_truthy


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

    # Reporting
    structured_cycle_report: bool = False

    @classmethod
    def from_env(cls) -> AutonomyConfig:
        """Create config from environment variables (shell compatibility)."""
        import os

        env = os.environ
        autopilot_skip_drive_idle_streak = max(
            0,
            env_int(
                "AUTOPILOT_SKIP_DRIVE_IDLE_STREAK",
                int(AUTOLOOP_ENV_DEFAULTS["AUTOPILOT_SKIP_DRIVE_IDLE_STREAK"]),
                environ=env,
            ),
        )

        return cls(
            project=Path(env_get("PROJECT", str(Path.cwd()), environ=env) or str(Path.cwd())),
            actor=(
                env_get("ACTOR", None, environ=env)
                or env_get("ACTOR_NAME", None, environ=env)
                or "koru-shell"
            ),
            queue_name=env_get("QUEUE_NAME", "", environ=env) or "",
            use_all_queues=env_truthy("USE_ALL_QUEUES", False, environ=env),
            max_iterations=env_int("MAX_ITERATIONS", int(AUTOLOOP_ENV_DEFAULTS["MAX_ITERATIONS"]), environ=env),
            max_cycles=env_int("MAX_CYCLES", int(AUTOLOOP_ENV_DEFAULTS["MAX_CYCLES"]), environ=env),
            sleep_seconds=env_int("SLEEP_SECONDS", int(AUTOLOOP_ENV_DEFAULTS["SLEEP_SECONDS"]), environ=env),
            initial_delay_seconds=env_int(
                "INITIAL_DELAY_SECONDS",
                int(AUTOLOOP_ENV_DEFAULTS["INITIAL_DELAY_SECONDS"]),
                environ=env,
            ),
            enable_scan=env_truthy("ENABLE_SCAN", True, environ=env),
            ticket_sources=env_get("TICKET_SOURCES", AUTOLOOP_ENV_DEFAULTS["TICKET_SOURCES"], environ=env),  # type: ignore[arg-type]
            enable_interactive=env_truthy("ENABLE_INTERACTIVE", False, environ=env),
            enable_autopilot_drive=env_truthy("ENABLE_AUTOPILOT_DRIVE", True, environ=env),
            autopilot_action=env_get("AUTOPILOT_ACTION", AUTOLOOP_ENV_DEFAULTS["AUTOPILOT_ACTION"], environ=env),  # type: ignore[arg-type]
            autopilot_ide=env_get("AUTOPILOT_IDE", AUTOLOOP_ENV_DEFAULTS["AUTOPILOT_IDE"], environ=env) or "auto",
            autopilot_submit=env_truthy("AUTOPILOT_SUBMIT", True, environ=env),
            autopilot_on_idle_only=env_truthy("AUTOPILOT_ON_IDLE_ONLY", False, environ=env),
            autopilot_skip_on_diagnostics_fail=env_truthy(
                "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL",
                True,
                environ=env,
            ),
            drive_prompt=env_get("DRIVE_PROMPT", "continue with the next ticket", environ=env)
            or "continue with the next ticket",
            enable_idle_diagnostics=env_truthy("ENABLE_IDLE_DIAGNOSTICS", False, environ=env),
            idle_diagnostics_profile=env_get("IDLE_DIAGNOSTICS_PROFILE", "off", environ=env),  # type: ignore[arg-type]
            strict_diagnostics=env_truthy("STRICT_DIAGNOSTICS", False, environ=env),
            enable_diagnostic_tickets=env_truthy("ENABLE_DIAGNOSTIC_TICKETS", False, environ=env),
            diagnostic_ticket_queue=env_get(
                "DIAGNOSTIC_TICKET_QUEUE",
                AUTOLOOP_ENV_DEFAULTS["DIAGNOSTIC_TICKET_QUEUE"],
                environ=env,
            )
            or "default",
            diagnostic_ticket_priority=env_get(
                "DIAGNOSTIC_TICKET_PRIORITY",
                AUTOLOOP_ENV_DEFAULTS["DIAGNOSTIC_TICKET_PRIORITY"],
                environ=env,
            )
            or "high",
            diag_state_dir=Path(env_get("DIAG_STATE_DIR", ".planfile/.koru/autoloop-diag", environ=env) or ".planfile/.koru/autoloop-diag"),
            autopilot_skip_statuses=env_get("AUTOPILOT_SKIP_STATUSES", "waiting_input", environ=env)
            or "waiting_input",
            autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
            backoff_on_stagnation=env_truthy("BACKOFF_ON_STAGNATION", True, environ=env),
            max_sleep_seconds=env_int("MAX_SLEEP_SECONDS", 900, environ=env),
            scan_skip_if_clean=env_truthy("SCAN_SKIP_IF_CLEAN", False, environ=env),
            scan_skip_after=env_int("SCAN_SKIP_AFTER", 1, environ=env),
            topology_integration=env_truthy("TOPOLOGY_INTEGRATION", True, environ=env),
            structured_cycle_report=structured_cycle_report_enabled(environ=env),
        )


def structured_cycle_report_enabled(
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the human structured cycle report should be emitted."""
    return env_truthy("KORU_STRUCTURED_CYCLE_REPORT", False, environ=environ)


__all__ = ["AutonomyConfig", "structured_cycle_report_enabled"]
