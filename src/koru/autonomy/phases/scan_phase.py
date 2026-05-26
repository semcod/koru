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
_DUPLICATE_ONLY_SCAN_COOLDOWN_SECONDS = 300.0


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


def _scan_result_is_duplicate_only(result: ScanResult) -> bool:
    return (
        bool(result.skipped_as_duplicate)
        and not result.applied
        and len(result.skipped) == len(result.skipped_as_duplicate)
    )


def _scan_create_failed_fingerprint(result: ScanResult) -> str:
    parts = list(result.skipped_create_failed_details) or list(result.skipped_create_failed)
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return f"{len(result.skipped_create_failed)}:{digest}"


def _scan_duplicate_fingerprint(result: ScanResult) -> str:
    digest = hashlib.sha1(
        "|".join(result.skipped_as_duplicate).encode("utf-8"),
    ).hexdigest()
    return f"{len(result.skipped_as_duplicate)}:{digest}"


def _create_failed_scan_cooldown_seconds() -> float:
    raw = os.environ.get("KORU_SCAN_CREATE_FAILED_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return _CREATE_FAILED_SCAN_COOLDOWN_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _CREATE_FAILED_SCAN_COOLDOWN_SECONDS


def _duplicate_only_scan_cooldown_seconds() -> float:
    raw = os.environ.get("KORU_SCAN_DUPLICATE_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return _DUPLICATE_ONLY_SCAN_COOLDOWN_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _DUPLICATE_ONLY_SCAN_COOLDOWN_SECONDS


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


def _remember_scan_duplicate_state(
    state: AutoloopState,
    result: ScanResult,
    *,
    now: float,
) -> None:
    if _scan_result_is_duplicate_only(result):
        state.last_scan_duplicate_fingerprint = _scan_duplicate_fingerprint(result)
        state.last_scan_duplicate_ts = now
        return
    if result.applied or not result.skipped_as_duplicate:
        state.last_scan_duplicate_fingerprint = ""
        state.last_scan_duplicate_ts = -1.0


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


def _should_skip_repeated_duplicate_scan(state: AutoloopState) -> tuple[bool, float]:
    cooldown = _duplicate_only_scan_cooldown_seconds()
    if (
        cooldown <= 0.0
        or not state.last_scan_duplicate_fingerprint
        or state.last_scan_duplicate_ts < 0.0
    ):
        return False, 0.0
    elapsed = time.time() - state.last_scan_duplicate_ts
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
        skip_repeated_duplicates, duplicate_remaining = _should_skip_repeated_duplicate_scan(state)
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
        elif skip_repeated_duplicates:
            _hp(
                "- koru scan --apply skipped "
                f"(duplicate-only results, cooldown active, ~{duplicate_remaining:.0f}s remaining)",
            )
            _emit(
                "ScanSkipped",
                {
                    "cycle": cycle,
                    "reason": "duplicate_only_cooldown",
                    "cooldown_remaining_seconds": duplicate_remaining,
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
                _remember_scan_duplicate_state(state, scan_result, now=time.time())
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
    if (
        not scan_after_idle_queue
        or queue_result.last_status != "idle"
        or not is_topology_enabled(
            project,
            "scan:on-change",
            fallback=True,
            enabled=topology_integration,
        )
    ):
        return None

    now = time.time()
    if _skip_scan_after_idle_for_rate_limit(
        state,
        cycle,
        scan_after_idle_min_interval_seconds,
        now,
        cycle_telemetry,
        _hp,
        _emit,
    ):
        return None
    if _skip_scan_after_idle_for_create_failed_cooldown(state, cycle, cycle_telemetry, _hp, _emit):
        return None
    if _skip_scan_after_idle_for_duplicate_cooldown(
        project,
        state,
        cycle,
        include_semcod_artifacts,
        cycle_telemetry,
        _hp,
        _emit,
    ):
        return None
    return _run_scan_after_idle(
        project,
        state,
        cycle,
        include_semcod_artifacts,
        now,
        cycle_telemetry,
        _hp,
        _emit,
    )


def _skip_scan_after_idle_for_rate_limit(
    state: AutoloopState,
    cycle: int,
    scan_after_idle_min_interval_seconds: float,
    now: float,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> bool:
    too_soon = (
        scan_after_idle_min_interval_seconds > 0.0
        and state.last_scan_after_idle_ts >= 0.0
        and now - state.last_scan_after_idle_ts < scan_after_idle_min_interval_seconds
    )
    if not too_soon:
        return False
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
    return True


def _skip_scan_after_idle_for_create_failed_cooldown(
    state: AutoloopState,
    cycle: int,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> bool:
    skip_repeated_create_failed, remaining = _should_skip_repeated_create_failed_scan(state)
    if not skip_repeated_create_failed:
        return False
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
    return True


def _skip_scan_after_idle_for_duplicate_cooldown(
    project: Path,
    state: AutoloopState,
    cycle: int,
    include_semcod_artifacts: bool | None,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> bool:
    skip_repeated_duplicates, duplicate_remaining = _should_skip_repeated_duplicate_scan(state)
    if not skip_repeated_duplicates:
        return False
    _hp(
        "- koru scan after idle skipped "
        f"(duplicate-only results, cooldown active, ~{duplicate_remaining:.0f}s remaining)",
    )
    _emit(
        "ScanSkipped",
        {
            "cycle": cycle,
            "reason": "duplicate_only_cooldown",
            "cooldown_remaining_seconds": duplicate_remaining,
            "phase": "after_idle_queue",
        },
    )
    cycle_telemetry["scan_after_idle_skipped_duplicate_cooldown"] = True
    if include_semcod_artifacts:
        _hp(
            "  idle strategy: detailed scan is in duplicate cooldown; "
            "continue detail→general by checking whole-project discovery",
        )
        discovery = _run_code2llm_discovery_after_idle(project, _hp, _emit)
        _record_code2llm_discovery_telemetry(state, cycle_telemetry, discovery)
    return True


def _run_scan_after_idle(
    project: Path,
    state: AutoloopState,
    cycle: int,
    include_semcod_artifacts: bool | None,
    now: float,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> ScanResult:
    scan_cmd = "koru scan --apply" f"{' --semcod-artifacts' if include_semcod_artifacts else ''}"
    if include_semcod_artifacts:
        _hp(
            "  idle strategy: detail→general; first apply concrete scan "
            "signals, then run whole-project code2llm discovery if no "
            "tickets were created",
        )
    _hp(f"+ {scan_cmd} (queue idle → intake scan)")
    idle_scan = run_scan(
        project=project,
        apply=True,
        include_semcod_artifacts=include_semcod_artifacts,
    )
    _record_scan_after_idle_result(
        state,
        cycle,
        idle_scan,
        scan_cmd,
        include_semcod_artifacts,
        now,
        cycle_telemetry,
        _hp,
        _emit,
    )
    if include_semcod_artifacts and not idle_scan.applied:
        discovery = _run_code2llm_discovery_after_idle(project, _hp, _emit)
        _record_code2llm_discovery_telemetry(state, cycle_telemetry, discovery)
    return idle_scan


def _record_scan_after_idle_result(
    state: AutoloopState,
    cycle: int,
    idle_scan: ScanResult,
    scan_cmd: str,
    include_semcod_artifacts: bool | None,
    now: float,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> None:
    _remember_scan_create_failed_state(state, idle_scan, now=now)
    _remember_scan_duplicate_state(state, idle_scan, now=now)
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


def _record_code2llm_discovery_telemetry(
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    discovery: dict[str, Any] | None,
) -> None:
    if discovery is None:
        return
    applied_count = len(discovery.get("applied", []))
    skipped_count = len(discovery.get("skipped", []))
    state.telemetry_scan_after_idle_tickets_applied += applied_count
    cycle_telemetry["code2llm_discovery_run"] = bool(discovery.get("ran"))
    cycle_telemetry["code2llm_discovery_applied"] = applied_count
    cycle_telemetry["code2llm_discovery_skipped"] = skipped_count
    follow_up_ticket_id = str(discovery.get("follow_up_ticket_id") or "").strip()
    if follow_up_ticket_id:
        cycle_telemetry["code2llm_discovery_follow_up_ticket_id"] = follow_up_ticket_id
        cycle_telemetry["code2llm_discovery_follow_up_workflow"] = str(
            discovery.get("follow_up_workflow") or "",
        ).strip() or "standardized_project_discovery"


def _run_code2llm_discovery_after_idle(
    project: Path,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> dict[str, Any] | None:
    """Run broad code2llm ticket discovery after an idle scan found no new work."""
    _hp(_format_idle_discovery_toolchain_line(project))
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
    payload = _ensure_standardized_discovery_follow_up(project, payload=payload, _hp=_hp)
    _emit("Code2llmDiscoveryCompleted", payload)
    return payload


def _ensure_standardized_discovery_follow_up(
    project: Path,
    *,
    payload: dict[str, Any],
    _hp: Callable[..., Any],
) -> dict[str, Any]:
    """Guarantee a standard idle workflow ticket when discovery found no runnable work."""
    applied = payload.get("applied")
    if isinstance(applied, list) and applied:
        return payload
    try:
        from koru.autonomy.ide_work import ensure_project_discovery_ticket
    except Exception as exc:  # noqa: BLE001 - optional integration
        _hp(f"  idle workflow: standardized follow-up unavailable: {exc}")
        return payload
    try:
        ticket = ensure_project_discovery_ticket(project, auto_run_code2llm=False)
    except Exception as exc:  # noqa: BLE001 - best-effort fallback
        _hp(f"  idle workflow: failed to ensure standardized follow-up ticket: {exc}")
        return payload
    if not isinstance(ticket, dict):
        return payload
    ticket_id = str(ticket.get("id") or "").strip()
    if not ticket_id:
        return payload
    payload["follow_up_workflow"] = "standardized_project_discovery"
    payload["follow_up_ticket_id"] = ticket_id
    _hp(
        "  idle workflow: standardized follow-up ticket "
        f"{ticket_id} ready for IDE LLM",
    )
    return payload


def _format_idle_discovery_toolchain_line(project: Path) -> str:
    try:
        from koru.semcod_tools import detect_semcod_tools

        tools = {tool.id: tool for tool in detect_semcod_tools(project)}
    except Exception:  # noqa: BLE001 - advisory log only
        return (
            "  discovery toolchain: automated sources=koru scan + code2llm; "
            "optional prefact/metrun status unavailable"
        )
    interesting = []
    for tool_id in ("code2llm", "redup", "testql", "prefact", "metrun"):
        tool = tools.get(tool_id)
        if tool is None:
            continue
        interesting.append(f"{tool_id}={tool.via if tool.available else 'missing'}")
    suffix = ", ".join(interesting) if interesting else "no optional tools detected"
    return (
        "  discovery toolchain: automated sources=koru scan + code2llm; "
        f"tool availability: {suffix}; prefact/metrun are advisory until "
        "dedicated ticket adapters are enabled"
    )
