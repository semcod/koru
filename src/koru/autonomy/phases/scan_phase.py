"""Scan phase logic for autonomous cycle."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomy.phases.utils import current_head, is_topology_enabled
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.scan import ScanResult, run_scan


def handle_scan_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    enable_scan: bool,
    include_semcod_artifacts: bool | None,
    scan_skip_if_clean: bool,
    scan_skip_after: int,
    topology_integration: bool,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> ScanResult | None:
    scan_result: ScanResult | None = None
    if enable_scan:
        if not is_topology_enabled(
            project,
            "scan:on-change",
            fallback=True,
            enabled=topology_integration,
        ):
            _hp("- koru scan --apply skipped (scan:on-change disabled in topology)")
            _emit("ScanSkipped", {"cycle": cycle, "reason": "topology:scan:on-change_disabled"})
        else:
            head_now = current_head(project)
            if (
                scan_skip_if_clean
                and state.scan_clean_streak >= scan_skip_after
                and head_now
                and head_now == state.scan_last_head
            ):
                _hp(
                    "- koru scan --apply skipped "
                    f"(clean_streak={state.scan_clean_streak}, HEAD unchanged)",
                )
                _emit(
                    "ScanSkipped",
                    {
                        "cycle": cycle,
                        "reason": "clean_git_head_unchanged",
                        "clean_streak": state.scan_clean_streak,
                        "head": head_now,
                    },
                )
            else:
                scan_cmd = "koru scan --apply" + (
                    " --semcod-artifacts" if include_semcod_artifacts else ""
                )
                _hp("+ " + scan_cmd)
                scan_result = run_scan(
                    project=project,
                    apply=True,
                    include_semcod_artifacts=include_semcod_artifacts,
                )
                _hp(
                    f"  scan: suggestions={len(scan_result.suggestions)} "
                    f"applied={len(scan_result.applied)} skipped={len(scan_result.skipped)}",
                )
                _emit(
                    "ScanCompleted",
                    {
                        "cycle": cycle,
                        "suggestions_count": len(scan_result.suggestions),
                        "applied_count": len(scan_result.applied),
                        "skipped_count": len(scan_result.skipped),
                        "semcod_artifacts": bool(include_semcod_artifacts),
                    },
                    command=scan_cmd,
                )
                state.scan_clean_streak = (
                    state.scan_clean_streak + 1 if not scan_result.suggestions else 0
                )
                state.scan_last_head = head_now
    return scan_result


def handle_scan_after_idle(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    scan_after_idle_queue: bool,
    include_semcod_artifacts: bool | None,
    scan_after_idle_min_interval_seconds: float,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> ScanResult | None:
    scan_result: ScanResult | None = None
    if (
        scan_after_idle_queue
        and queue_result.last_status == "idle"
        and is_topology_enabled(
            project,
            "scan:on-change",
            fallback=True,
            enabled=topology_integration,
        )
    ):
        now = time.time()
        too_soon = (
            scan_after_idle_min_interval_seconds > 0.0
            and state.last_scan_after_idle_ts >= 0.0
            and now - state.last_scan_after_idle_ts < scan_after_idle_min_interval_seconds
        )
        if too_soon:
            wait = scan_after_idle_min_interval_seconds - (now - state.last_scan_after_idle_ts)
            _hp(
                f"- koru scan after idle skipped (min-interval "
                f"{scan_after_idle_min_interval_seconds}s, ~{wait:.0f}s remaining)",
            )
            _emit(
                "ScanSkipped",
                {
                    "cycle": cycle,
                    "reason": "after_idle_rate_limit",
                    "min_interval_seconds": scan_after_idle_min_interval_seconds,
                },
            )
            cycle_telemetry["scan_after_idle_skipped_rate_limit"] = True
        else:
            scan_cmd = f"koru scan --apply{' --semcod-artifacts' if include_semcod_artifacts else ''}"
            _hp(f"+ {scan_cmd} (queue idle → intake scan)")
            idle_scan = run_scan(
                project=project,
                apply=True,
                include_semcod_artifacts=include_semcod_artifacts,
            )
            scan_result = idle_scan
            state.last_scan_after_idle_ts = now
            state.telemetry_scan_after_idle_runs += 1
            state.telemetry_scan_after_idle_tickets_applied += len(idle_scan.applied)
            cycle_telemetry["scan_after_idle_run"] = True
            cycle_telemetry["scan_after_idle_applied"] = len(idle_scan.applied)
            _hp(
                f"  scan: suggestions={len(idle_scan.suggestions)} "
                f"applied={len(idle_scan.applied)} skipped={len(idle_scan.skipped)}",
            )
            _emit(
                "ScanCompleted",
                {
                    "cycle": cycle,
                    "suggestions_count": len(idle_scan.suggestions),
                    "applied_count": len(idle_scan.applied),
                    "skipped_count": len(idle_scan.skipped),
                    "semcod_artifacts": bool(include_semcod_artifacts),
                    "phase": "after_idle_queue",
                },
                command=scan_cmd,
            )
            if include_semcod_artifacts and not idle_scan.applied:
                discovery = _run_code2llm_discovery_after_idle(project, _hp, _emit)
                if discovery is not None:
                    applied_count = len(discovery.get("applied", []))
                    skipped_count = len(discovery.get("skipped", []))
                    state.telemetry_scan_after_idle_tickets_applied += applied_count
                    cycle_telemetry["code2llm_discovery_run"] = bool(discovery.get("ran"))
                    cycle_telemetry["code2llm_discovery_applied"] = applied_count
                    cycle_telemetry["code2llm_discovery_skipped"] = skipped_count
    return scan_result


def _run_code2llm_discovery_after_idle(
    project: Path,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> dict[str, Any] | None:
    """Run broad code2llm ticket discovery after an idle scan found no new work."""
    try:
        from koru.autonomy.code2llm_discovery import (
            format_discovery_summary,
            run_code2llm_discovery,
        )
    except Exception as exc:  # noqa: BLE001 - optional integration
        _hp(f"- code2llm discovery unavailable: {exc}")
        return None

    outcome = run_code2llm_discovery(project)
    summary = format_discovery_summary(outcome)
    _hp(f"  {summary}")
    payload = outcome.to_dict()
    _emit("Code2llmDiscoveryCompleted", payload)
    return payload
