from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import DiagnosticResult
from koru.autonomous_wup import WupHealthResult
from koru.autonomy.cycle_trace import record_decision_trace
from koru.autonomy.state import AutoloopState
from koru.autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
from koru.queue import QueueLoopResult


def emit_cycle_completion_events(
    *,
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    wup_health: WupHealthResult,
    autopilot_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
    scan_after_idle_queue: bool,
    scan_after_idle_min_interval_seconds: float,
    autopilot_skip_drive_idle_streak: int,
    hp: Callable[[str], None],
    emit: Callable[[str, dict[str, Any]], None],
) -> None:
    environment_profile = cycle_telemetry.get("environment_profile")
    autopilot_payload = {
        "cycle": cycle,
        "decision": autopilot_status,
        "queue_status": queue_result.last_status,
        "ide": autopilot_ide,
        "backend": autopilot_backend,
        "drive_kind": autopilot_drive_kind,
    }
    if isinstance(environment_profile, dict):
        autopilot_payload["environment_profile"] = environment_profile
    emit(
        "AutopilotDecision",
        autopilot_payload,
    )
    hp(
        f"koru autonomous: cycle={cycle} queue={queue_result.last_status} "
        f"diagnostics={diag_result.status} wup={wup_health.status} autopilot={autopilot_status}",
    )
    cycle_completed_payload: dict[str, Any] = {
        "cycle": cycle,
        "queue_status": queue_result.last_status,
        "diagnostics_status": diag_result.status,
        "wup_status": wup_health.status,
        "autopilot_status": autopilot_status,
        "telemetry": {
            "cycle": cycle_telemetry,
            "cumulative": {
                "autopilot_idle_streak_skips": state.telemetry_autopilot_idle_streak_skips,
                "scan_after_idle_runs": state.telemetry_scan_after_idle_runs,
                "scan_after_idle_tickets_applied": (
                    state.telemetry_scan_after_idle_tickets_applied
                ),
            },
        },
    }
    if isinstance(environment_profile, dict):
        cycle_completed_payload["environment_profile"] = environment_profile
    emit("CycleCompleted", cycle_completed_payload)

    write_autonomy_cycle_telemetry(
        project,
        cycle=cycle,
        cumulative={
            "autopilot_idle_streak_skips": state.telemetry_autopilot_idle_streak_skips,
            "scan_after_idle_runs": state.telemetry_scan_after_idle_runs,
            "scan_after_idle_tickets_applied": state.telemetry_scan_after_idle_tickets_applied,
        },
        cycle_metrics=cycle_telemetry,
        knobs={
            "scan_after_idle_queue": scan_after_idle_queue,
            "scan_after_idle_min_interval_seconds": scan_after_idle_min_interval_seconds,
            "autopilot_skip_drive_idle_streak": autopilot_skip_drive_idle_streak,
        },
    )

    record_decision_trace(
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        cycle_telemetry=cycle_telemetry,
        stagnation_streak=int(getattr(state, "stagnation_streak", 0) or 0),
        hp=hp,
    )


__all__ = ["emit_cycle_completion_events"]
