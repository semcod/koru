from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .autonomous_wup import WupHealthResult
from .autonomous_wup import _read_wup_health as _read_wup_health_impl
from .autonomy.ide_work import (
    extract_ticket_id_from_text,
    release_stale_in_progress_tickets,
    resolve_idle_drive_prompt,
    resolve_in_progress_stale_minutes,
)
from .autonomy.post_run_verify import (
    load_post_run_verify_config,
    verify_after_ide_work,
    verify_completed_tickets,
)
from .autonomy.prompts import DEFAULT_ESCALATION_THRESHOLD, build_prompt
from .autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
from .queue import QueueLoopResult, run_planfile_queue_loop
from .queue import default_human_prompt as _default_human_prompt
from .queue import run_api_request as _run_api_request
from .queue import run_llm_request as _run_llm_request
from .queue import run_process as _run_process
from .queue import run_shell_command as _run_shell_command
from .scan import ScanResult, run_scan
from .stdio_events import write_stdio_event
from .tasks import create_nl_task
from .topology import is_component_enabled, is_pipeline_enabled


def _stdio_info(msg: str, *, fmt: str) -> None:
    from .activity_log import activity_info

    activity_info(msg, fmt=fmt)


@dataclass(frozen=True)
class DiagnosticResult:
    status: str
    failed: list[str]


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


def _queue_loop_waiting_ticket_label(queue_result: QueueLoopResult) -> str:
    waiting = getattr(queue_result, "waiting", None) or []
    return waiting[-1] if waiting else "-"


def _is_topology_enabled(project: Path, key: str, *, fallback: bool, enabled: bool) -> bool:
    if not enabled:
        return fallback
    try:
        if key in {"idle-diagnostics", "autoloop:queue", "scan:on-change", "autopilot:drive"}:
            return is_pipeline_enabled(project, key)
        return is_component_enabled(project, key)
    except Exception:
        return fallback


def _current_head(project: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _status_in_skip_list(status: str, skip_statuses: str) -> bool:
    return status.lower() in {
        item.strip().lower() for item in skip_statuses.split(",") if item.strip()
    }


def _allow_keyboard_autopilot_fallback() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _prefer_keyboard_autopilot() -> bool:
    for key in ("KORU_AUTOPILOT_PREFER_KEYBOARD", "KORU_AUTOPILOT_VISIBLE_TYPING"):
        if os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_os_injector_fallback` (monkeypatch-friendly)."""
    from . import autonomous as _autonomous_mod

    return _autonomous_mod._try_os_injector_fallback(prompt, submit=submit)


def _run_command_check(
    project: Path,
    check_id: str,
    command: list[str],
    *,
    stdio_format: str = "human",
) -> bool:
    _stdio_info("+ " + " ".join(command), fmt=stdio_format)
    result = subprocess.run(command, cwd=project, check=False)
    if result.returncode != 0:
        _stdio_info(f"! {check_id} failed (continuing loop)", fmt=stdio_format)
        return False
    return True


def _create_diagnostic_ticket(
    *,
    stdio_format: str = "human",
    project: Path,
    check_id: str,
    summary: str,
    cycle: int,
    queue_status: str,
    queue_name: str,
    priority: str,
    state_dir: Path,
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    marker = state_dir / f"{check_id}.failed"
    if marker.exists():
        _stdio_info(
            f"- diagnostic ticket marker exists for {check_id}, skipping create",
            fmt=stdio_format,
        )
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    created = create_nl_task(project, prompt, queue_name=queue_name, priority=priority)
    marker.write_text(created.ticket_id, encoding="utf-8")
    _stdio_info(
        f"+ created diagnostic ticket {created.ticket_id} for {check_id} (queue={queue_name})",
        fmt=stdio_format,
    )


def _clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    (state_dir / f"{check_id}.failed").unlink(missing_ok=True)


def _read_wup_health(
    *,
    project: Path,
    state: AutoloopState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
) -> WupHealthResult:
    return _read_wup_health_impl(
        project=project,
        state=state,
        diagnostic_tickets=diagnostic_tickets,
        ticket_queue=ticket_queue,
        state_dir=state_dir,
        create_diagnostic_ticket=_create_diagnostic_ticket,
    )


def _run_idle_diagnostics(
    *,
    stdio_format: str = "human",
    project: Path,
    profile: str,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> DiagnosticResult:
    from . import autonomous_diagnostics as diag

    def create_ticket(**kwargs: Any) -> None:
        _create_diagnostic_ticket(stdio_format=stdio_format, **kwargs)

    return diag.run_idle_diagnostics(
        stdio_info=_stdio_info,
        is_topology_enabled=_is_topology_enabled,
        run_command=_run_command_check,
        clear_marker=_clear_diagnostic_marker,
        create_ticket=create_ticket,
        make_result=lambda status, failed: DiagnosticResult(status=status, failed=failed),
        stdio_format=stdio_format,
        project=project,
        profile=profile,
        cycle=cycle,
        queue_status=queue_status,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        topology_integration=topology_integration,
    )


def _autopilot_event_path() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "koru-autopilot-events.ndjson"


def _drain_autopilot_events(state: AutoloopState) -> list[dict[str, Any]]:
    path = _autopilot_event_path()
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if events:
        path.write_text("", encoding="utf-8")
    return events


def _initialize_cycle_telemetry() -> dict[str, Any]:
    return {
        "autopilot_skipped_idle_streak": False,
        "scan_after_idle_run": False,
        "scan_after_idle_applied": 0,
        "scan_after_idle_skipped_rate_limit": False,
    }


def _heal_stale_socket() -> None:
    """Auto-heal: best-effort stale socket removal so daemon restart can bind."""
    try:
        from .autonomy.environment import probe_socket_health
        from .autonomy.heal import remove_stale_socket
        from .autopilot import default_socket_path

        sock = probe_socket_health(default_socket_path())
        if sock.stale:
            result = remove_stale_socket(sock)
            if result.status == "fixed":
                print(f"koru autonomous: auto-healed stale socket {sock.path}")
    except Exception:
        pass


def _handle_autopilot_events(
    state: AutoloopState,
    _hp: callable,
) -> None:
    events = _drain_autopilot_events(state)
    if events:
        for ev in events:
            ev_type = ev.get("type", "unknown")
            _hp(f"  event: {ev_type} ide={ev.get('ide', '?')}")
        state.autopilot_events.extend(events)
        for ev in events:
            if ev.get("type") == "message.sent":
                state.last_message_sent_ts = ev.get("ts", time.time())


def _handle_queue_hygiene(
    project: Path,
    cycle: int,
    _hp: callable,
    _emit: callable,
) -> None:
    stale_minutes = resolve_in_progress_stale_minutes(project)
    if stale_minutes is not None:
        released_stale = release_stale_in_progress_tickets(
            project,
            stale_minutes=stale_minutes,
            runner=_run_process,
        )
        if released_stale:
            _hp(
                f"  queue hygiene: reopened {released_stale} stale in_progress "
                f"(>{stale_minutes:.0f}m)",
            )
            _emit(
                "QueueStaleReleased",
                {"cycle": cycle, "count": released_stale, "stale_minutes": stale_minutes},
            )


def _handle_post_run_verify_ide(
    project: Path,
    state: AutoloopState,
    cycle: int,
    _hp: callable,
    _emit: callable,
) -> Any:
    verify_config = load_post_run_verify_config(project)
    ide_verify_outcomes = verify_after_ide_work(
        project,
        state,
        config=verify_config,
        planfile_runner=_run_process,
        shell_runner=_run_shell_command,
    )
    if ide_verify_outcomes:
        failed_ide = [o for o in ide_verify_outcomes if not o.get("ok")]
        _hp(
            f"  post_run_verify (IDE): tickets={len(ide_verify_outcomes)} failed={len(failed_ide)}",
        )
        _emit(
            "PostRunVerifyIdeCompleted",
            {
                "cycle": cycle,
                "ticket_count": len(ide_verify_outcomes),
                "failed_count": len(failed_ide),
                "outcomes": ide_verify_outcomes,
            },
            command="; ".join(verify_config.commands) if verify_config else None,
        )
    return verify_config


def _handle_scan_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    enable_scan: bool,
    include_semcod_artifacts: bool | None,
    scan_skip_if_clean: bool,
    scan_skip_after: int,
    topology_integration: bool,
    _hp: callable,
    _emit: callable,
) -> ScanResult | None:
    scan_result: ScanResult | None = None
    if enable_scan:
        if not _is_topology_enabled(
            project,
            "scan:on-change",
            fallback=True,
            enabled=topology_integration,
        ):
            _hp("- koru scan --apply skipped (scan:on-change disabled in topology)")
            _emit("ScanSkipped", {"cycle": cycle, "reason": "topology:scan:on-change_disabled"})
        else:
            head_now = _current_head(project)
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


def _build_queue_command(max_iterations: int, queue_name: str | None) -> str:
    """Build the queue loop command string."""
    base = f"koru --queue --loop --max-iterations {max_iterations}"
    return base + (" --all-queues" if queue_name is None else f" --queue-name {queue_name}")


def _run_queue_loop(
    project: Path,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
) -> QueueLoopResult:
    """Execute the planfile queue loop."""
    return run_planfile_queue_loop(
        project=project,
        actor=actor,
        queue_name=queue_name,
        max_iterations=max_iterations,
        planfile_runner=_run_process,
        shell_runner=_run_shell_command,
        api_runner=_run_api_request,
        llm_runner=_run_llm_request,
        prompt_runner=_default_human_prompt,
    )


def _emit_queue_iteration_event(
    queue_result: QueueLoopResult,
    cycle: int,
    queue_name: str | None,
    actor: str,
    qcmd: str,
    _emit: callable,
) -> None:
    """Emit queue iteration event."""
    qname = "__all__" if queue_name is None else queue_name
    _sum_fn = getattr(queue_result, "summary", None)
    _queue_summary = _sum_fn() if callable(_sum_fn) else str(_sum_fn or "")
    _emit(
        "QueueIteration",
        {
            "cycle": cycle,
            "queue_name": qname,
            "actor": actor,
            "iterations": int(getattr(queue_result, "iterations", 0)),
            "completed": list(getattr(queue_result, "completed", []) or []),
            "failed": list(getattr(queue_result, "failed", []) or []),
            "waiting": list(getattr(queue_result, "waiting", []) or []),
            "last_status": str(getattr(queue_result, "last_status", "")),
            "last_message": str(getattr(queue_result, "last_message", "")),
            "last_ticket_id": getattr(queue_result, "last_ticket_id", None),
            "summary": _queue_summary,
        },
        command=qcmd,
    )


def _handle_post_run_verify(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    verify_config: Any,
    _hp: callable,
    _emit: callable,
) -> None:
    """Handle post-run verification for completed tickets."""
    completed_ids = list(getattr(queue_result, "completed", []) or [])
    if completed_ids and verify_config is not None:
        verify_outcomes = verify_completed_tickets(
            project,
            completed_ids,
            config=verify_config,
            planfile_runner=_run_process,
            shell_runner=_run_shell_command,
        )
        failed = [o for o in verify_outcomes if not o.get("ok")]
        for outcome in verify_outcomes:
            if outcome.get("ok"):
                tid = str(outcome.get("ticket_id") or "").strip()
                if tid:
                    state.post_verify_seen.add(tid)
        if verify_outcomes:
            _hp(
                f"  post_run_verify (queue): tickets={len(completed_ids)} failed={len(failed)}",
            )
            _emit(
                "PostRunVerifyCompleted",
                {
                    "cycle": cycle,
                    "ticket_count": len(completed_ids),
                    "failed_count": len(failed),
                    "outcomes": verify_outcomes,
                },
                command="; ".join(verify_config.commands),
            )


def _handle_queue_loop_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    actor: str,
    queue_name: str | None,
    max_iterations: int,
    topology_integration: bool,
    verify_config: Any,
    _hp: callable,
    _emit: callable,
) -> tuple[QueueLoopResult, Any]:
    if not _is_topology_enabled(
        project,
        "autoloop:queue",
        fallback=True,
        enabled=topology_integration,
    ):
        _hp("- autoloop queue phase skipped (autoloop:queue disabled in topology)")
        queue_result = QueueLoopResult(0, [], [], [], "disabled", "")
    else:
        qcmd = _build_queue_command(max_iterations, queue_name)
        _hp("+ " + qcmd)
        queue_result = _run_queue_loop(project, actor, queue_name, max_iterations)
        _hp(f"  queue: {queue_result.summary()}")
        _emit_queue_iteration_event(queue_result, cycle, queue_name, actor, qcmd, _emit)
        _handle_post_run_verify(project, state, cycle, queue_result, verify_config, _hp, _emit)
    return queue_result, verify_config


def _handle_scan_after_idle(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    scan_after_idle_queue: bool,
    include_semcod_artifacts: bool | None,
    scan_after_idle_min_interval_seconds: float,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> ScanResult | None:
    scan_result: ScanResult | None = None
    if (
        scan_after_idle_queue
        and queue_result.last_status == "idle"
        and _is_topology_enabled(
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
            scan_cmd = "koru scan --apply" + (
                " --semcod-artifacts" if include_semcod_artifacts else ""
            )
            _hp("+ " + scan_cmd + " (queue idle → intake scan)")
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
    return scan_result


def _update_stagnation_state(
    state: AutoloopState,
    queue_result: QueueLoopResult,
) -> None:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    signature = f"{queue_result.last_status}:{waiting_ticket}"
    if state.previous_signature and state.previous_signature == signature:
        state.stagnation_streak += 1
    else:
        state.stagnation_streak = 0
    state.previous_signature = signature


def _waiting_ticket_has_label(
    project: Path,
    queue_result: QueueLoopResult,
    label: str,
) -> bool:
    ticket_id = _queue_loop_waiting_ticket_label(queue_result)
    if ticket_id == "-":
        ticket_id = getattr(queue_result, "last_ticket_id", None) or ""
    if not ticket_id:
        return False

    for sprint_path in (
        project / ".planfile" / "sprints" / "current.yaml",
        project / "planfile.yaml",
    ):
        if not sprint_path.is_file():
            continue
        try:
            data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        tickets = data.get("tickets")
        if tickets is None and isinstance(data.get("sprint"), dict):
            tickets = data["sprint"].get("tickets")
        if not isinstance(tickets, dict):
            continue
        ticket = tickets.get(ticket_id)
        if not isinstance(ticket, dict):
            continue
        labels = ticket.get("labels") or []
        return label in {str(item) for item in labels}
    return False


def _handle_diagnostics(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    idle_diagnostics: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path | None,
    wup_watch_enabled: bool,
    wup_diagnostic_tickets: bool,
    wup_ticket_queue: str,
    topology_integration: bool,
    _hp: callable,
    _emit: callable,
) -> tuple[DiagnosticResult, WupHealthResult]:
    diag_result = DiagnosticResult(status="skipped", failed=[])
    if queue_result.last_status == "idle" and idle_diagnostics not in {"off", "none"}:
        diag_result = _run_idle_diagnostics(
            stdio_format="human",
            project=project,
            profile=idle_diagnostics,
            cycle=cycle,
            queue_status=queue_result.last_status,
            diagnostic_tickets=diagnostic_tickets,
            diagnostic_ticket_queue=diagnostic_ticket_queue,
            diagnostic_ticket_priority=diagnostic_ticket_priority,
            diagnostic_state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
            topology_integration=topology_integration,
        )

    wup_health = WupHealthResult(status="skipped", failing_services=[], new_events=0)
    if wup_watch_enabled:
        wup_health = _read_wup_health(
            project=project,
            state=state,
            diagnostic_tickets=wup_diagnostic_tickets,
            ticket_queue=wup_ticket_queue,
            state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
        )
        if wup_health.status != "ok":
            _hp(
                f"koru autonomous: WUP health={wup_health.status} "
                f"failing={','.join(wup_health.failing_services) or '-'} "
                f"new_events={wup_health.new_events}",
            )
            if diag_result.status in {"skipped", "off", "ok"} and wup_health.status == "failed":
                diag_result = DiagnosticResult(status="failed", failed=["wup"])

    _emit(
        "WupHealthChanged",
        {
            "cycle": cycle,
            "watcher_enabled": wup_watch_enabled,
            "status": wup_health.status,
            "failing_services": list(wup_health.failing_services),
            "new_events": wup_health.new_events,
        },
    )
    _emit(
        "DiagnosticsCompleted",
        {"cycle": cycle, "status": diag_result.status, "failed": list(diag_result.failed)},
    )
    return diag_result, wup_health


def _check_autopilot_skip_conditions(
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    autopilot_action: str,
    autopilot_on_idle_only: bool,
    autopilot_skip_on_diagnostics_fail: bool,
    autopilot_skip_drive_idle_streak: int,
    autopilot_skip_statuses: str,
    diag_result: DiagnosticResult,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> tuple[bool, str]:
    """Check if autopilot should be skipped and return (should_skip, skip_reason)."""
    if not _is_topology_enabled(
        project,
        "autopilot:drive",
        fallback=True,
        enabled=topology_integration,
    ):
        _hp("- autopilot skipped (autopilot:drive disabled in topology)")
        return True, "skipped(topology)"
    elif autopilot_action == "off":
        _hp("- autopilot action set to off, skipping")
        return True, "skipped(action_off)"
    elif autopilot_on_idle_only and queue_result.last_status != "idle":
        _hp("- autopilot skipped (idle_only)")
        return True, "skipped(idle_only)"
    elif autopilot_skip_on_diagnostics_fail and diag_result.status == "failed":
        _hp("- autopilot skipped (diagnostics_fail)")
        return True, "skipped(diagnostics_fail)"
    elif (
        autopilot_skip_drive_idle_streak > 0
        and queue_result.last_status == "idle"
        and state.stagnation_streak >= autopilot_skip_drive_idle_streak
    ):
        _hp(
            "- autopilot skipped "
            f"(idle_streak_{state.stagnation_streak}>={autopilot_skip_drive_idle_streak})",
        )
        state.telemetry_autopilot_idle_streak_skips += 1
        cycle_telemetry["autopilot_skipped_idle_streak"] = True
        return True, "skipped(idle_streak)"
    elif 0 < state.stagnation_streak < DEFAULT_ESCALATION_THRESHOLD and _status_in_skip_list(
        queue_result.last_status,
        autopilot_skip_statuses,
    ):
        if _waiting_ticket_has_label(project, queue_result, "llm-ready"):
            _hp(
                "- autopilot not skipped "
                f"(waiting ticket is llm-ready, streak={state.stagnation_streak})",
            )
            return False, ""
        _hp(
            "- autopilot skipped "
            f"(stuck_{queue_result.last_status}_streak_{state.stagnation_streak})",
        )
        return True, f"skipped(stuck_{queue_result.last_status})"
    return False, ""


def _execute_autopilot_drive(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    _hp: callable,
) -> tuple[dict[str, Any], bool, str, str | None]:
    """Execute autopilot drive and return (reply, ok, decision_kind, idle_prompt_kind)."""
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    effective_drive_prompt = drive_prompt
    idle_prompt_kind: str | None = None
    if queue_result.last_status == "idle":
        effective_drive_prompt, idle_prompt_kind = resolve_idle_drive_prompt(
            project,
            drive_prompt=drive_prompt,
            runner=_run_process,
        )
    decision = build_prompt(
        queue_status=queue_result.last_status,
        last_message=getattr(queue_result, "last_message", "") or "",
        waiting_ticket_id=(
            waiting_ticket
            if waiting_ticket != "-"
            else getattr(queue_result, "last_ticket_id", None)
        ),
        drive_prompt=effective_drive_prompt,
        autopilot_action=autopilot_action,
        stagnation_streak=state.stagnation_streak,
    )
    reply = client.drive(
        decision.prompt,
        submit=submit,
        ide=autopilot_ide,
        require_plugin=(
            not _allow_keyboard_autopilot_fallback() and not _prefer_keyboard_autopilot()
        ),
    )
    ok = bool(reply.get("ok", True))
    if not ok:
        fallback = _try_os_injector_fallback(decision.prompt, submit=submit)
        if fallback is not None:
            reply = fallback
            ok = bool(reply.get("ok", True))
    return reply, ok, decision.kind, idle_prompt_kind


def _update_autopilot_state(
    state: AutoloopState,
    ok: bool,
    decision_kind: str,
    autopilot_drive_kind: str,
    decision_prompt: str,
) -> None:
    """Update autoloop state based on autopilot result."""
    if ok and autopilot_drive_kind == "idle_ticket_prompt":
        ticket_id = extract_ticket_id_from_text(decision_prompt)
        if ticket_id:
            state.pending_ide_verify_id = ticket_id
    if ok and decision_kind == "escalation_prompt":
        state.stagnation_streak = 0
        state.previous_signature = ""


def _log_autopilot_result(
    ok: bool,
    queue_result: QueueLoopResult,
    autopilot_ide: str,
    decision_kind: str,
    reply: dict[str, Any],
    _hp: callable,
) -> None:
    """Log autopilot result."""
    if ok:
        backend = reply.get("backend", "?")
        if decision_kind == "ticket_prompt":
            waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
            _hp(
                "  autopilot: ok (ticket="
                f"{waiting_ticket}, ide={autopilot_ide}, "
                f"backend={backend}, kind={decision_kind})",
            )
        else:
            _hp(
                f"  autopilot: ok (ide={autopilot_ide}, backend={backend}, kind={decision_kind})",
            )
    else:
        _hp(
            f"  autopilot: failed ({reply.get('message', 'unknown error')}, kind={decision_kind})",
        )


def _handle_autopilot_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    enable_autopilot: bool,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    autopilot_on_idle_only: bool,
    autopilot_skip_on_diagnostics_fail: bool,
    autopilot_skip_drive_idle_streak: int,
    autopilot_skip_statuses: str,
    diag_result: DiagnosticResult,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
    _emit: callable,
) -> tuple[str, str | None, str | None]:
    autopilot_status = "skipped"
    autopilot_backend: str | None = None
    autopilot_drive_kind: str | None = None

    if enable_autopilot and client is not None:
        should_skip, skip_reason = _check_autopilot_skip_conditions(
            project,
            queue_result,
            state,
            autopilot_action,
            autopilot_on_idle_only,
            autopilot_skip_on_diagnostics_fail,
            autopilot_skip_drive_idle_streak,
            autopilot_skip_statuses,
            diag_result,
            topology_integration,
            cycle_telemetry,
            _hp,
        )
        if should_skip:
            autopilot_status = skip_reason
        else:
            reply, ok, decision_kind, idle_prompt_kind = _execute_autopilot_drive(
                project,
                state,
                queue_result,
                client,
                autopilot_ide,
                drive_prompt,
                submit,
                autopilot_action,
                _hp,
            )
            autopilot_drive_kind = idle_prompt_kind or decision_kind
            autopilot_status = "ok" if ok else "failed"
            autopilot_backend = (
                str(reply.get("backend")) if reply.get("backend") is not None else None
            )
            _update_autopilot_state(
                state, ok, decision_kind, autopilot_drive_kind, reply.get("prompt", "")
            )
            _log_autopilot_result(ok, queue_result, autopilot_ide, decision_kind, reply, _hp)

    return autopilot_status, autopilot_backend, autopilot_drive_kind


def _emit_cycle_completion_events(
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
    _hp: callable,
    _emit: callable,
) -> None:
    _emit(
        "AutopilotDecision",
        {
            "cycle": cycle,
            "decision": autopilot_status,
            "queue_status": queue_result.last_status,
            "ide": autopilot_ide,
            "backend": autopilot_backend,
            "drive_kind": autopilot_drive_kind,
        },
    )
    _hp(
        f"koru autonomous: cycle={cycle} queue={queue_result.last_status} "
        f"diagnostics={diag_result.status} wup={wup_health.status} autopilot={autopilot_status}",
    )
    _emit(
        "CycleCompleted",
        {
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
        },
    )

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


def run_cycle(
    *,
    cycle: int,
    project: Path,
    actor: str,
    queue_name: str | None,
    enable_scan: bool,
    max_iterations: int,
    enable_autopilot: bool,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    include_semcod_artifacts: bool | None,
    client: Any,
    state: AutoloopState | None = None,
    idle_diagnostics: str = "off",
    diagnostic_tickets: bool = False,
    diagnostic_ticket_queue: str = "default",
    diagnostic_ticket_priority: str = "high",
    diagnostic_state_dir: Path | None = None,
    wup_watch_enabled: bool = False,
    wup_diagnostic_tickets: bool = True,
    wup_ticket_queue: str = "default",
    strict_diagnostics: bool = False,
    autopilot_action: str = "drive",
    autopilot_on_idle_only: bool = False,
    autopilot_skip_on_diagnostics_fail: bool = True,
    autopilot_skip_drive_idle_streak: int = 0,
    autopilot_skip_statuses: str = "waiting_input",
    scan_skip_if_clean: bool = False,
    scan_skip_after: int = 1,
    scan_after_idle_queue: bool = False,
    scan_after_idle_min_interval_seconds: float = 0.0,
    topology_integration: bool = True,
    stdio_format: str = "human",
    correlation_id: str = "",
) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    state = state or AutoloopState()
    cycle_telemetry = _initialize_cycle_telemetry()
    _heal_stale_socket()

    def _emit(event_type: str, payload: dict, command: str | None = None) -> None:
        if stdio_format == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type=event_type,
                correlation_id=correlation_id,
                payload=payload,
                command=command,
            )

    def _hp(msg: str) -> None:
        from .activity_log import activity, activity_info

        if msg.startswith("+ "):
            activity("RUN", msg[2:], fmt=stdio_format)
        elif msg.startswith("  scan:"):
            activity("SCAN", msg.strip(), fmt=stdio_format)
        elif msg.startswith("  queue:"):
            activity("QUEUE", msg.strip(), fmt=stdio_format)
        elif msg.startswith("  autopilot:"):
            activity("CHAT", msg.strip(), fmt=stdio_format)
        elif stdio_format == "human":
            activity_info(msg, fmt=stdio_format)
        else:
            activity_info(msg, fmt=stdio_format)

    _handle_autopilot_events(state, _hp)
    scan_result: ScanResult | None = None
    _emit("CycleStarted", {"cycle": cycle, "project": str(project.resolve())})

    _handle_queue_hygiene(project, cycle, _hp, _emit)
    verify_config = _handle_post_run_verify_ide(project, state, cycle, _hp, _emit)

    scan_result = _handle_scan_phase(
        project,
        state,
        cycle,
        enable_scan,
        include_semcod_artifacts,
        scan_skip_if_clean,
        scan_skip_after,
        topology_integration,
        _hp,
        _emit,
    )

    queue_result, verify_config = _handle_queue_loop_phase(
        project,
        state,
        cycle,
        actor,
        queue_name,
        max_iterations,
        topology_integration,
        verify_config,
        _hp,
        _emit,
    )

    idle_scan_result = _handle_scan_after_idle(
        project,
        state,
        cycle,
        queue_result,
        scan_after_idle_queue,
        include_semcod_artifacts,
        scan_after_idle_min_interval_seconds,
        topology_integration,
        cycle_telemetry,
        _hp,
        _emit,
    )
    if idle_scan_result is not None:
        scan_result = idle_scan_result

    _update_stagnation_state(state, queue_result)

    diag_result, wup_health = _handle_diagnostics(
        project,
        state,
        cycle,
        queue_result,
        idle_diagnostics,
        diagnostic_tickets,
        diagnostic_ticket_queue,
        diagnostic_ticket_priority,
        diagnostic_state_dir,
        wup_watch_enabled,
        wup_diagnostic_tickets,
        wup_ticket_queue,
        topology_integration,
        _hp,
        _emit,
    )

    if strict_diagnostics and diag_result.status == "failed":
        _emit("AutonomousStopped", {"reason": "strict_diagnostics_failure", "cycle": cycle})
        _stdio_info(
            "koru autonomous: strict diagnostics enabled -> stopping on diagnostics failure",
            fmt=stdio_format,
        )
        raise SystemExit(2)

    autopilot_status, autopilot_backend, autopilot_drive_kind = _handle_autopilot_phase(
        project,
        state,
        cycle,
        queue_result,
        enable_autopilot,
        client,
        autopilot_ide,
        drive_prompt,
        submit,
        autopilot_action,
        autopilot_on_idle_only,
        autopilot_skip_on_diagnostics_fail,
        autopilot_skip_drive_idle_streak,
        autopilot_skip_statuses,
        diag_result,
        topology_integration,
        cycle_telemetry,
        _hp,
        _emit,
    )

    _emit_cycle_completion_events(
        project,
        state,
        cycle,
        queue_result,
        diag_result,
        wup_health,
        autopilot_status,
        autopilot_ide,
        autopilot_backend,
        autopilot_drive_kind,
        cycle_telemetry,
        scan_after_idle_queue,
        scan_after_idle_min_interval_seconds,
        autopilot_skip_drive_idle_streak,
        _hp,
        _emit,
    )

    return scan_result, queue_result, autopilot_status, diag_result


__all__ = ["AutoloopState", "DiagnosticResult", "run_cycle"]
