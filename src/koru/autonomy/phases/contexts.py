"""Typed context objects shared by autonomous phase modules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from koru.autonomous_cycle_common import DiagnosticResult
from koru.autonomous_wup import WupHealthResult
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.scan import ScanResult


PhaseCallback = Callable[..., Any]


@dataclass(frozen=True)
class PhaseCallbacks:
    hp: PhaseCallback
    emit: PhaseCallback


@dataclass(frozen=True)
class CyclePhaseContext:
    project: Path
    state: AutoloopState
    cycle: int
    callbacks: PhaseCallbacks


@dataclass(frozen=True)
class QueueScanPhaseConfig:
    actor: str
    queue_name: str | None
    enable_scan: bool
    max_iterations: int
    include_semcod_artifacts: bool | None
    idle_diagnostics: str
    diagnostic_tickets: bool
    diagnostic_ticket_queue: str
    diagnostic_ticket_priority: str
    diagnostic_state_dir: Path | None
    wup_watch_enabled: bool
    wup_diagnostic_tickets: bool
    wup_ticket_queue: str
    scan_skip_if_clean: bool
    scan_skip_after: int
    scan_after_idle_queue: bool
    scan_after_idle_min_interval_seconds: float
    topology_integration: bool


@dataclass(frozen=True)
class PreDrivePhaseResult:
    scan_result: ScanResult | None
    queue_result: QueueLoopResult
    diag_result: DiagnosticResult
    wup_health: WupHealthResult


@dataclass(frozen=True)
class DrivePhaseConfig:
    queue_name: str | None
    enable_autopilot: bool
    client: Any
    autopilot_ide: str
    drive_prompt: str
    submit: bool
    autopilot_action: str
    autopilot_on_idle_only: bool
    autopilot_skip_on_diagnostics_fail: bool
    autopilot_skip_drive_idle_streak: int
    autopilot_skip_statuses: str
    topology_integration: bool
    scan_after_idle_queue: bool
    scan_after_idle_min_interval_seconds: float


@dataclass(frozen=True)
class DrivePhaseInputs:
    queue_result: QueueLoopResult
    diag_result: DiagnosticResult
    wup_health: WupHealthResult
    cycle_telemetry: dict[str, Any]


@dataclass(frozen=True)
class DrivePhaseResult:
    status: str
    backend: str | None
    drive_kind: str | None


@dataclass(frozen=True)
class SleepBackoffContext:
    args: Any
    project: Any
    cycle: int
    queue_result: Any
    waiting_ticket: str
    loop_state: Any
    diag_result: Any
    autopilot_status: str
    autopilot_ide: str
    correlation_id: str
