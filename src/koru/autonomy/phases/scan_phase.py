"""Scan phase logic for autonomous cycle."""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomy.phases.utils import current_head, is_topology_enabled
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.scan import ScanResult, run_scan

_CREATE_FAILED_SCAN_COOLDOWN_SECONDS = 120.0


def _format_scan_summary_line(result: ScanResult) -> str:
    """One-line summary that distinguishes 'duplicate' vs 'create failed'."""
    parts = [
        f"suggestions={len(result.suggestions)}",
        f"applied={len(result.applied)}",
        f"skipped={len(result.skipped)}",
    ]
    if result.skipped_as_duplicate:
        parts.append(f"duplicates={len(result.skipped_as_duplicate)}")
    if result.skipped_create_failed:
        parts.append(f"create_failed={len(result.skipped_create_failed)}")
    return "  scan: " + " ".join(parts)


def _hp_scan_skip_hint(result: ScanResult, _hp: Callable[..., Any]) -> None:
    """Emit a follow-up explanation when scan applied nothing but had work."""
    if result.applied:
        return
    if not result.suggestions:
        return
    if result.skipped_as_duplicate and not result.skipped_create_failed:
        sample = ", ".join(result.skipped_as_duplicate[:3])
        more = (
            f" (+{len(result.skipped_as_duplicate) - 3} more)"
            if len(result.skipped_as_duplicate) > 3
            else ""
        )
        _hp(
            f"  scan: all {len(result.skipped_as_duplicate)} suggestion(s) "
            "are duplicates of *active* planfile tickets (closed tickets are "
            "ignored on purpose so regressing signals can reopen). "
            f"Examples: {sample}{more}. "
            "To force fresh tickets, either reopen the matching done ticket "
            "in the dashboard, or `rm -rf project/` + "
            "`KORU_SCAN_FORCE_RESCAN=1 koru auto`.",
        )
        return
    if result.skipped_create_failed:
        sample = ", ".join(result.skipped_create_failed[:3])
        more = (
            f" (+{len(result.skipped_create_failed) - 3} more)"
            if len(result.skipped_create_failed) > 3
            else ""
        )
        detail = ""
        if result.skipped_create_failed_details:
            detail = f" First error: {result.skipped_create_failed_details[0]}."
        _hp(
            f"  scan: {len(result.skipped_create_failed)} suggestion(s) "
            "could not be turned into a planfile ticket (create failed — "
            "check `.planfile/` permissions, lockfile, or run "
            "`koru ide doctor --explain`). "
            f"Examples: {sample}{more}.{detail}",
        )


def _scan_result_is_create_failed_only(result: ScanResult) -> bool:
    return (
        bool(result.skipped_create_failed)
        and not result.applied
        and len(result.skipped) == len(result.skipped_create_failed)
    )


def _scan_create_failed_fingerprint(result: ScanResult) -> str:
    parts = list(result.skipped_create_failed_details) or list(result.skipped_create_failed)
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return f"{len(result.skipped_create_failed)}:{digest}"


def _create_failed_scan_cooldown_seconds() -> float:
    raw = os.environ.get("KORU_SCAN_CREATE_FAILED_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return _CREATE_FAILED_SCAN_COOLDOWN_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _CREATE_FAILED_SCAN_COOLDOWN_SECONDS


def _remember_scan_create_failed_state(
    state: AutoloopState,
    result: ScanResult,
    *,
    now: float,
) -> None:
    if _scan_result_is_create_failed_only(result):
        state.last_scan_create_failed_fingerprint = _scan_create_failed_fingerprint(result)
        state.last_scan_create_failed_ts = now
        return
    if result.applied or not result.skipped_create_failed:
        state.last_scan_create_failed_fingerprint = ""
        state.last_scan_create_failed_ts = -1.0


def _should_skip_repeated_create_failed_scan(
    state: AutoloopState,
) -> tuple[bool, float]:
    cooldown = _create_failed_scan_cooldown_seconds()
    if (
        cooldown <= 0.0
        or not state.last_scan_create_failed_fingerprint
        or state.last_scan_create_failed_ts < 0.0
    ):
        return False, 0.0
    elapsed = time.time() - state.last_scan_create_failed_ts
    if elapsed >= cooldown:
        return False, 0.0
    return True, cooldown - elapsed


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
        skip_repeated_create_failed, remaining = _should_skip_repeated_create_failed_scan(state)
        if not is_topology_enabled(
            project,
            "scan:on-change",
            fallback=True,
            enabled=topology_integration,
        ):
            _hp("- koru scan --apply skipped (scan:on-change disabled in topology)")
            _emit("ScanSkipped", {"cycle": cycle, "reason": "topology:scan:on-change_disabled"})
        elif skip_repeated_create_failed:
            _hp(
                "- koru scan --apply skipped "
                f"(repeated create_failed, cooldown active, ~{remaining:.0f}s remaining)",
            )
            _emit(
                "ScanSkipped",
                {
                    "cycle": cycle,
                    "reason": "create_failed_cooldown",
                    "cooldown_remaining_seconds": remaining,
                },
            )
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
                _remember_scan_create_failed_state(state, scan_result, now=time.time())
                _hp(_format_scan_summary_line(scan_result))
                _hp_scan_skip_hint(scan_result, _hp)
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
        skip_repeated_create_failed, remaining = _should_skip_repeated_create_failed_scan(state)
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
        elif skip_repeated_create_failed:
            _hp(
                "- koru scan after idle skipped "
                f"(repeated create_failed, cooldown active, ~{remaining:.0f}s remaining)",
            )
            _emit(
                "ScanSkipped",
                {
                    "cycle": cycle,
                    "reason": "create_failed_cooldown",
                    "cooldown_remaining_seconds": remaining,
                    "phase": "after_idle_queue",
                },
            )
            cycle_telemetry["scan_after_idle_skipped_create_failed_cooldown"] = True
        else:
            scan_cmd = (
                "koru scan --apply"
                f"{' --semcod-artifacts' if include_semcod_artifacts else ''}"
            )
            _hp(f"+ {scan_cmd} (queue idle → intake scan)")
            idle_scan = run_scan(
                project=project,
                apply=True,
                include_semcod_artifacts=include_semcod_artifacts,
            )
            scan_result = idle_scan
            _remember_scan_create_failed_state(state, idle_scan, now=now)
            state.last_scan_after_idle_ts = now
            state.telemetry_scan_after_idle_runs += 1
            state.telemetry_scan_after_idle_tickets_applied += len(idle_scan.applied)
            cycle_telemetry["scan_after_idle_run"] = True
            cycle_telemetry["scan_after_idle_applied"] = len(idle_scan.applied)
            _hp(_format_scan_summary_line(idle_scan))
            _hp_scan_skip_hint(idle_scan, _hp)
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
