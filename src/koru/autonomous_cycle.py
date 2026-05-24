
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from koru.autonomous_wup import WupHealthResult
from koru.autonomous_wup import _read_wup_health as _read_wup_health_impl
from koru.autonomy.ide_work import (
    extract_ticket_id_from_text,
    release_stale_in_progress_tickets,
    resolve_idle_drive_prompt,
    resolve_in_progress_stale_minutes,
)
from koru.autonomy.post_run_verify import (
    load_post_run_verify_config,
    verify_after_ide_work,
    verify_completed_tickets,
)
from koru.autonomy.prompts import DEFAULT_ESCALATION_THRESHOLD, build_prompt
from koru.autonomy.prompts import PromptDecision
from koru.autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
from koru.queue import QueueLoopResult, run_planfile_queue_loop
from koru.queue import default_human_prompt as _default_human_prompt
from koru.queue import run_api_request as _run_api_request
from koru.queue import run_llm_request as _run_llm_request
from koru.queue import run_process as _run_process
from koru.queue import run_shell_command as _run_shell_command
from koru.scan import ScanResult, run_scan
from koru.stdio_events import write_stdio_event
from koru.tasks import create_nl_task
from koru.topology import is_component_enabled, is_pipeline_enabled
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import (
    detect_terminal_host_ide_id,
    normalize_ide_id,
    supports_vscode_extension_plugin,
)


def _stdio_info(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


@dataclass(frozen=True)
class DiagnosticResult:
    status: str
    failed: list[str]


from koru.autonomy.state import AutoloopState


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


from koru.autonomy.env import (
    autopilot_terminal_conflict_reason as _autopilot_terminal_conflict_reason,
    plugin_required_for_ide as _plugin_required_for_ide,
)


def _client_has_usable_plugin(client: Any, autopilot_ide: str) -> tuple[bool, str]:
    """Return whether a daemon status has a live plugin usable for this IDE."""
    from koru.autonomous_plugin import plugin_status_decision

    status_fn = getattr(client, "status", None)
    if not callable(status_fn):
        return True, ""
    try:
        status = status_fn()
    except (OSError, TimeoutError, RuntimeError) as exc:
        return False, f"daemon status unavailable: {exc}"
    
    plugins = status.get("plugins")
    if plugins is None:
        return True, ""
    
    return plugin_status_decision(status, autopilot_ide)


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_os_injector_fallback` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_os_injector_fallback(prompt, submit=submit)


def _run_command_check(
    project: Path,
    check_id: str,
    command: list[str],
    *,
    stdio_format: str = "human",
) -> bool:
    _stdio_info(f"+ {' '.join(command)}", fmt=stdio_format)
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
    from koru.autonomous_diag_markers import diagnostic_marker_path

    state_dir.mkdir(parents=True, exist_ok=True)
    marker = diagnostic_marker_path(state_dir, check_id)
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
    from koru.autonomous_diag_markers import diagnostic_marker_path

    diagnostic_marker_path(state_dir, check_id).unlink(missing_ok=True)


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
    from koru import autonomous_diagnostics as diag

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
        from koru.autonomy.environment import probe_socket_health
        from koru.autonomy.heal import remove_stale_socket
        from koru.autopilot import default_socket_path

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
        if len(state.autopilot_events) > 500:
            state.autopilot_events = state.autopilot_events[-500:]
        for ev in events:
            if ev.get("type") == "message.sent":
                try:
                    state.last_message_sent_ts = float(ev.get("ts") or time.time())
                except (TypeError, ValueError):
                    state.last_message_sent_ts = time.time()


from koru.autonomy.phases.queue_phase import handle_queue_hygiene as _handle_queue_hygiene
from koru.autonomy.phases.verify_phase import handle_post_run_verify_ide as _handle_post_run_verify_ide


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
    return base if queue_name is None else f"{base} --queue-name {queue_name}"


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
        _hp(f"+ {qcmd}")
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
            if _skip_due_to_recent_chat_activity(
                project=project,
                queue_result=queue_result,
                state=state,
                cycle_telemetry=cycle_telemetry,
                _hp=_hp,
            ):
                return True, "skipped(chat_activity)"
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


def _autopilot_redrive_cooldown_seconds() -> float:
    """Operator-tunable cooldown (env: ``KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS``).

    Defaults to 300 s. The autopilot loop must NOT redrive the same
    ``llm-ready`` ticket prompt if a ``message.sent`` or ``message.received``
    event has been logged within this window — that means the IDE-side LLM
    is still working, or just answered, and a re-paste would clobber its
    output. Set to ``0`` (or negative) to disable the new behavior and
    restore the legacy "redrive every cycle" semantics.
    """
    raw = os.environ.get("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return 300.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 300.0


def _autopilot_escalation_cooldown_seconds(base_cooldown: float) -> float:
    """Cooldown applied when the LAST drive was an ``escalation_prompt``.

    Escalations ("Ticket X has been stuck in status 'waiting_input' for N
    cycles…") are explicit nudges aimed at an LLM that has likely already
    asked the user a clarifying question. Hammering the chat with another
    escalation every 30 s actively destroys the dialog: it concatenates new
    text on top of the user's pending reply or scrolls the LLM's question
    out of view. Use ``KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS`` (default
    1800 = 30 min) to give a real human / the IDE-side LLM enough time to
    converge before the next nudge. Falls back to ``base_cooldown`` when set
    to a value below it (cooldown can never shrink below the global one).
    """
    raw = os.environ.get("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return max(base_cooldown, 1800.0)
    try:
        value = float(raw)
    except ValueError:
        return max(base_cooldown, 1800.0)
    return max(base_cooldown, max(0.0, value))


def _llm_reflection_summary_max_age_seconds() -> float:
    raw = os.environ.get("KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS", "").strip()
    if not raw:
        return 1800.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 1800.0


def _recent_llm_reflection_summary(state: "AutoloopState") -> str:
    summary = str(getattr(state, "last_llm_reflection_summary", "") or "").strip()
    if not summary:
        return ""
    ts_raw = getattr(state, "last_llm_reflection_ts", 0.0)
    try:
        ts = float(ts_raw or 0.0)
    except (TypeError, ValueError):
        ts = 0.0
    if ts <= 0:
        return ""
    max_age = _llm_reflection_summary_max_age_seconds()
    if max_age > 0 and (time.time() - ts) > max_age:
        return ""
    return summary


def _llm_needs_input_ticket_enabled() -> bool:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _llm_needs_input_ticket_queue_name() -> str:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_QUEUE", "").strip()
    return raw or "operator"


def _llm_needs_input_ticket_priority() -> str:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY", "").strip()
    return raw or "high"


def _llm_needs_input_heuristic_enabled() -> bool:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_HEURISTIC", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _compact_question_text(text: str, *, limit: int = 240) -> str:
    collapsed = " ".join(str(text or "").split()).strip()
    if not collapsed:
        return ""
    return collapsed[:limit]


def _extract_needs_input_question(
    reflection_events: list[Any],
    reflection_summary: str,
) -> str:
    """Best-effort extraction of the concrete question asked by IDE LLM."""
    for event in reversed(reflection_events):
        ev_type = str(getattr(event, "type", "") or "")
        if ev_type != "message.received":
            continue
        text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
        if not text.strip():
            continue
        collapsed = _compact_question_text(text, limit=600)
        if not collapsed:
            continue
        matches = re.findall(r"([^?]{8,260}\?)", collapsed)
        if matches:
            return _compact_question_text(matches[-1], limit=240)
        for marker in (
            "please provide",
            "can you provide",
            "could you provide",
            "what is",
            "which",
            "need ",
            "missing ",
        ):
            if marker in collapsed.lower():
                return _compact_question_text(collapsed, limit=240)

    summary = _compact_question_text(reflection_summary, limit=240)
    if "?" in summary:
        return summary
    return ""


def _latest_received_text(reflection_events: list[Any]) -> str:
    for event in reversed(reflection_events):
        ev_type = str(getattr(event, "type", "") or "")
        if ev_type != "message.received":
            continue
        text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
        if not text.strip():
            continue
        return _compact_question_text(text, limit=320)
    return ""


def _llm_needs_input_waiting_ticket(queue_result: QueueLoopResult) -> str:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    if waiting_ticket == "-":
        waiting_ticket = str(getattr(queue_result, "last_ticket_id", "") or "-")
    return waiting_ticket


def _llm_needs_input_summary(
    queue_result: QueueLoopResult,
    reflection_summary: str,
) -> str:
    summary = (reflection_summary or "").strip()
    if summary:
        return summary
    summary = str(getattr(queue_result, "last_message", "") or "").strip()
    if summary:
        return summary
    return "IDE-side LLM requested additional input without details."


def _llm_needs_input_operator_payload(
    *,
    queue_result: QueueLoopResult,
    waiting_ticket: str,
    summary: str,
    question: str,
) -> tuple[str, str, dict[str, Any]]:
    title = f"[OPERATOR] {waiting_ticket}: provide missing IDE input"
    prompt = (
        f"{title}\n\n"
        + "IDE-side LLM asked for more context while this task is blocked in waiting_input.\n\n"
        + f"Blocked ticket: {waiting_ticket}\n"
        + f"Queue message: {str(getattr(queue_result, 'last_message', '') or '-').strip()}\n"
        + (f"Detected question: {question}\n" if question else "")
        + f"Reflection summary: {summary}\n\n"
        + "Action:\n"
        + "1. Open the related IDE chat thread.\n"
        + "2. Answer the missing question/context from this summary.\n"
        + "3. Let the LLM continue and close this operator ticket when unblocked."
    )
    scaffold: dict[str, Any] = {
        "title": title,
        "executor_kind": "human",
        "executor_mode": "interactive",
        "labels": ["koru", "operator", "autopilot-needs-input", f"waiting:{waiting_ticket}"],
        "source_tool": "koru-autonomous-llx-reflect",
        "source_context": {
            "waiting_ticket": waiting_ticket,
            "reflection_question": question,
            "reflection_summary": summary,
            "dedupe_key": f"autopilot-needs-input:{waiting_ticket}",
        },
    }
    return title, prompt, scaffold


def _note_reused_llm_needs_input_operator_ticket(
    *,
    project: Path,
    created: Any,
    waiting_ticket: str,
    question: str,
    summary: str,
    _hp: Any,
) -> None:
    try:
        from koru.queue.planfile_ticket_note import append_shell_evidence_note

        def _planfile_runner(
            command: list[str],
            cwd: Path,
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        note = (
            "[AUTOPILOT] llx reflection still needs operator input.\n"
            + f"blocked_ticket={waiting_ticket}\n"
            + (f"question={question}\n" if question else "")
            + f"summary={summary}"
        )
        result, kind = append_shell_evidence_note(
            project,
            created.ticket_id,
            note,
            run_id=f"llx-{int(time.time())}",
            planfile_runner=_planfile_runner,
        )
        if result.returncode == 0:
            _hp(
                "- llx reflect: updated operator ticket "
                f"{created.ticket_id} ({kind})",
            )
        else:
            detail = (result.stderr or result.stdout or "").strip()
            _hp(
                "- llx reflect: operator ticket note failed "
                f"({created.ticket_id}: {detail})",
            )
    except Exception as exc:
        _hp(
            "- llx reflect: operator ticket note skipped "
            f"({created.ticket_id}: {exc})",
        )


def _upsert_llm_needs_input_operator_ticket(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    reflection_summary: str,
    reflection_events: list[Any],
    _hp: Any,
) -> str | None:
    """Create/update one deduplicated operator ticket for ``llm needs_input``."""
    if not _llm_needs_input_ticket_enabled():
        return None

    waiting_ticket = _llm_needs_input_waiting_ticket(queue_result)
    summary = _llm_needs_input_summary(queue_result, reflection_summary)
    question = _extract_needs_input_question(reflection_events, summary)

    signature_key = question or summary
    signature = f"{waiting_ticket}|{signature_key[:240]}"
    previous_signature = str(getattr(state, "last_operator_needs_input_signature", "") or "")
    previous_ticket = str(getattr(state, "last_operator_needs_input_ticket_id", "") or "")
    if signature == previous_signature:
        return previous_ticket or None

    queue_name = _llm_needs_input_ticket_queue_name()
    priority = _llm_needs_input_ticket_priority()
    _, prompt, scaffold = _llm_needs_input_operator_payload(
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        summary=summary,
        question=question,
    )

    try:
        created = create_nl_task(
            project,
            prompt,
            queue_name=queue_name,
            priority=priority,
            scaffold=scaffold,
        )
    except Exception as exc:
        _hp(f"- llx reflect: operator ticket upsert failed ({exc})")
        return None

    state.last_operator_needs_input_signature = signature
    state.last_operator_needs_input_ticket_id = created.ticket_id

    if getattr(created, "reused", False):
        _note_reused_llm_needs_input_operator_ticket(
            project=project,
            created=created,
            waiting_ticket=waiting_ticket,
            question=question,
            summary=summary,
            _hp=_hp,
        )
    else:
        _hp(
            "- llx reflect: created operator ticket "
            f"{created.ticket_id} (queue={queue_name})",
        )
    if question:
        _hp(f"- llx reflect: operator question candidate={question!r}")
    return created.ticket_id


def _inject_reflection_summary_into_prompt(
    state: "AutoloopState",
    queue_result: QueueLoopResult,
    decision: PromptDecision,
) -> PromptDecision:
    if queue_result.last_status != "waiting_input":
        return decision
    if decision.kind not in {"ticket_prompt", "fallback_prompt", "escalation_prompt"}:
        return decision
    summary = _recent_llm_reflection_summary(state)
    if not summary:
        return decision
    snippet = summary[:320]
    augmented = (
        decision.prompt.rstrip()
        + "\n\nRecent IDE chat context:\n"
        + f"- {snippet}\n"
        + "Use this context to continue from current progress. Do not restart from scratch."
    )
    return PromptDecision(
        prompt=augmented,
        kind=decision.kind,
        skip=decision.skip,
        skip_reason=decision.skip_reason,
    )


_CHAT_ACTIVITY_TYPES = ("message.sent", "message.received")


def _event_timestamp(payload: dict[str, Any], *, default: float = 0.0) -> float:
    try:
        return float(payload.get("ts") or default)
    except (TypeError, ValueError):
        return default


def _recent_chat_activity_events(
    state: "AutoloopState",
    *,
    ide: str | None,
    within_seconds: float,
) -> list[dict[str, Any]]:
    now = time.time()
    recent: list[dict[str, Any]] = []
    raw_events = getattr(state, "autopilot_events", None)
    if not isinstance(raw_events, list):
        return []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        ev_type = str(raw.get("type") or "")
        if ev_type not in _CHAT_ACTIVITY_TYPES:
            continue
        if ide and str(raw.get("ide") or "") != ide:
            continue
        ts = _event_timestamp(raw, default=0.0)
        if ts <= 0:
            continue
        if (now - ts) > within_seconds:
            continue
        recent.append(raw)
    return recent[-20:]


def _state_events_to_chat_events(recent_events: list[dict[str, Any]]) -> list[Any]:
    try:
        from koruide.chat_history import ChatEvent
    except ImportError:
        return []
    converted: list[Any] = []
    for event in recent_events:
        converted.append(
            ChatEvent(
                ts=_event_timestamp(event, default=time.time()),
                type=str(event.get("type") or ""),
                ide=str(event.get("ide") or ""),
                chat=str(event.get("chat") or "default"),
                text=str(event.get("text") or ""),
                summary=str(event.get("summary") or ""),
                length=int(event.get("length") or 0),
                reason=str(event.get("reason") or ""),
            ),
        )
    return converted


def _chat_activity_cooldown_for_state(state: "AutoloopState") -> float:
    cooldown = _autopilot_redrive_cooldown_seconds()
    if cooldown <= 0:
        return cooldown
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if last_kind == "escalation_prompt":
        return _autopilot_escalation_cooldown_seconds(cooldown)
    return cooldown


def _last_successful_drive_ack_age(
    state: "AutoloopState",
    *,
    waiting_ticket: str,
) -> float | None:
    try:
        last_sent_ts = float(getattr(state, "last_message_sent_ts", 0.0) or 0.0)
    except (TypeError, ValueError):
        last_sent_ts = 0.0
    last_driven_ticket = str(getattr(state, "last_driven_ticket_id", "") or "")
    if waiting_ticket == "-" or last_driven_ticket != waiting_ticket or last_sent_ts <= 0:
        return None
    return max(0.0, time.time() - last_sent_ts)


def _recent_message_sent_allows_redrive(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    recent_events: list[dict[str, Any]],
    last_type: str,
    age: str,
    waiting_ticket: str,
    _hp: Any,
) -> bool:
    has_received = any(str(ev.get("type") or "") == "message.received" for ev in recent_events)
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if not (
        last_type == "message.sent"
        and not has_received
        and getattr(queue_result, "last_status", "") == "waiting_input"
        and last_kind != "escalation_prompt"
        and not _waiting_ticket_has_label(project, queue_result, "llm-ready")
    ):
        return False
    _hp(
        "- autopilot redrive allowed (message.sent without "
        f"message.received age={age} ticket={waiting_ticket})",
    )
    return True


def _recent_chat_history_fallback(
    *,
    ide: str | None,
    cooldown: float,
    reflection_events: list[Any],
) -> tuple[str, str, list[Any]] | None:
    try:
        from koruide.chat_history import has_recent_activity, last_event, read_events
    except ImportError:
        return None
    if not has_recent_activity(
        ide=ide,
        within_seconds=cooldown,
        types=_CHAT_ACTIVITY_TYPES,
    ):
        return None
    last = last_event(ide=ide, types=_CHAT_ACTIVITY_TYPES)
    age = f"{last.age_seconds:.0f}s" if last is not None else "?"
    last_type = last.type if last is not None else "?"
    if not reflection_events:
        reflection_events = read_events(
            ide=ide,
            max_age_seconds=cooldown,
            types=_CHAT_ACTIVITY_TYPES,
            limit=20,
        )
    return last_type, age, reflection_events


def _upsert_reflection_needs_input_ticket(
    *,
    reflection: Any,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    summary: str,
    reflection_events: list[Any],
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> None:
    """Upsert an operator ticket when reflection indicates needs_input and not done."""
    if not (reflection.needs_input and not reflection.done):
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=summary,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket


def _apply_llx_chat_reflection(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    cycle_telemetry: dict[str, Any],
    waiting_ticket: str,
    ide: str | None,
    reflection_events: list[Any],
    _hp: Any,
) -> tuple[bool, bool]:
    try:
        from koru.llm_reflect import llm_reflect_enabled, reflect_on_chat
    except ImportError:
        return False, False
    if not llm_reflect_enabled():
        return False, False
    ticket_title = getattr(queue_result, "last_message", "") or ""
    raw_driven_prompt = getattr(state, "last_driven_prompt", "")
    driven_prompt = raw_driven_prompt if isinstance(raw_driven_prompt, str) else ""
    reflection = reflect_on_chat(
        ticket_id=waiting_ticket or "-",
        ticket_title=ticket_title,
        driven_prompt=driven_prompt or ticket_title,
        ide=ide or "",
        events=reflection_events or None,
    )
    if reflection is None:
        return False, False
    cycle_telemetry["autopilot_llx_reflection"] = {
        "done": reflection.done,
        "needs_input": reflection.needs_input,
        "summary": reflection.summary,
    }
    summary = (reflection.summary or "").strip()
    if summary:
        state.last_llm_reflection_summary = summary[:320]
        state.last_llm_reflection_ts = time.time()
    _hp(
        "- llx reflect: "
        f"done={reflection.done} needs_input={reflection.needs_input} "
        f"summary={reflection.summary!r}",
    )
    _upsert_reflection_needs_input_ticket(
        reflection=reflection,
        project=project,
        queue_result=queue_result,
        state=state,
        summary=summary,
        reflection_events=reflection_events,
        cycle_telemetry=cycle_telemetry,
        _hp=_hp,
    )
    return True, bool(reflection.done)


def _apply_needs_input_heuristic(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    cycle_telemetry: dict[str, Any],
    reflection_events: list[Any],
    _hp: Any,
) -> None:
    if not _llm_needs_input_heuristic_enabled():
        return
    question = _extract_needs_input_question(reflection_events, "")
    if not question:
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=_latest_received_text(reflection_events) or question,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_needs_input_heuristic"] = True
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket
    _hp(f"- needs_input heuristic: question={question!r}")


def _skip_due_to_recent_chat_activity(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: "AutoloopState",
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    """Return True iff the loop should skip drive because the IDE chat is busy.

    Two signals (both optional, fail-closed → no skip):

    1. Plain cooldown: ``message.sent`` for the same ticket within
       :func:`_autopilot_redrive_cooldown_seconds`. This is the cheap path —
       no llx, no network — and covers the common case where koru just drove
       the prompt and the LLM is still streaming a response.
    2. Optional :mod:`koru.llm_reflect` (when enabled and llx
       is on PATH). Asks an OpenRouter-backed model to read the recent
       ``message.received`` events and decide ``{done, needs_input}``. If
         it returns ``needs_input=true`` we skip and upsert one operator ticket;
         if ``done=true`` we also skip redrive and let the queue state update
         naturally.
    """
    cooldown = _chat_activity_cooldown_for_state(state)
    if cooldown <= 0:
        return False

    ide = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip().lower() or None
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)

    # Fallback dedupe when plugin chat events are delayed/missing: rely on
    # the last successful drive for this exact waiting ticket.
    drive_ack_age = _last_successful_drive_ack_age(state, waiting_ticket=waiting_ticket)
    if drive_ack_age is not None and drive_ack_age <= cooldown:
        age = f"{drive_ack_age:.0f}s"
        cycle_telemetry["autopilot_skipped_chat_activity"] = True
        cycle_telemetry["autopilot_chat_activity_last_event"] = "drive.ack"
        _hp(
            "- autopilot skipped (recent_drive_ack "
            f"last=drive.ack age={age} cooldown={cooldown:.0f}s "
            f"ticket={waiting_ticket})",
        )
        return True

    recent_events = _recent_chat_activity_events(
        state,
        ide=ide,
        within_seconds=cooldown,
    )
    reflection_events = _state_events_to_chat_events(recent_events)

    if recent_events:
        last_payload = recent_events[-1]
        last_type = str(last_payload.get("type") or "?")
        age_seconds = max(0.0, time.time() - _event_timestamp(last_payload, default=0.0))
        age = f"{age_seconds:.0f}s"
        # ``message.sent`` only means the plugin *attempted* a drive — on
        # Wayland a false-positive xdotool submit still logs sent while nothing
        # reached the IDE LLM. If we never saw ``message.received`` afterwards
        # and the queue is still ``waiting_input``, allow redrive instead of
        # waiting out the full cooldown.
        if _recent_message_sent_allows_redrive(
            project=project,
            queue_result=queue_result,
            state=state,
            recent_events=recent_events,
            last_type=last_type,
            age=age,
            waiting_ticket=waiting_ticket,
            _hp=_hp,
        ):
            # Non-llm-ready: allow redrive — false-positive submits (Wayland
            # xdotool, composer.sendToAgent no-op) still log message.sent.
            # llm-ready: the IDE LLM is expected to be working; keep cooldown
            # even without message.received (regression:
            # test_run_cycle_llm_ready_skips_redrive_on_recent_in_memory_chat_activity).
            return False
    else:
        fallback = _recent_chat_history_fallback(
            ide=ide,
            cooldown=cooldown,
            reflection_events=reflection_events,
        )
        if fallback is None:
            return False
        last_type, age, reflection_events = fallback

    cycle_telemetry["autopilot_skipped_chat_activity"] = True
    cycle_telemetry["autopilot_chat_activity_last_event"] = last_type
    _hp(
        "- autopilot skipped (recent_chat_activity "
        f"last={last_type} age={age} cooldown={cooldown:.0f}s "
        f"ticket={waiting_ticket})",
    )
    reflection_resolved, reflection_done = _apply_llx_chat_reflection(
        project=project,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=cycle_telemetry,
        waiting_ticket=waiting_ticket,
        ide=ide,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if reflection_done:
        return True

    # Fallback for environments where llx/OpenRouter is unavailable.
    if not reflection_resolved:
        _apply_needs_input_heuristic(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            reflection_events=reflection_events,
            _hp=_hp,
        )
    return True


def _resolve_autopilot_drive_decision(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    *,
    drive_prompt: str,
    autopilot_action: str,
) -> tuple[Any, str | None]:
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
    decision = _inject_reflection_summary_into_prompt(state, queue_result, decision)
    return decision, idle_prompt_kind


def _drive_autopilot_once(
    client: Any,
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
) -> tuple[dict[str, Any], bool]:
    reply = client.drive(
        prompt,
        submit=submit,
        ide=autopilot_ide,
        require_plugin=require_plugin,
    )
    ok = bool(reply.get("ok", True))
    if ok or require_plugin:
        return reply, ok
    fallback = _try_os_injector_fallback(prompt, submit=submit)
    if fallback is None:
        return reply, ok
    return fallback, bool(fallback.get("ok", True))


def _reply_missing_autopilot_plugin(reply: dict[str, Any]) -> bool:
    return "no connected autopilot plugin" in str(reply.get("message") or "").lower()


def _reply_chat_input_busy(reply: dict[str, Any]) -> bool:
    """``True`` when plugin (≥0.1.50) reported the chat input is non-empty.

    The plugin acks with ``verification="input_busy"`` and
    ``reason="chat_input_not_empty"`` when its pre-paste probe finds
    un-submitted text in the chat textarea — typically the user is mid-reply
    or the IDE-side LLM left a clarifying question. The autonomous loop
    treats this exactly like a successful skip-with-cooldown so it does not
    keep retrying every cycle.
    """
    if str(reply.get("verification") or "").lower() == "input_busy":
        return True
    return str(reply.get("reason") or "").lower() == "chat_input_not_empty"


def _reply_needs_focus_retry(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    return "focus" in msg


def _reply_needs_plugin_retry(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "no connected autopilot plugin" in msg:
        return False
    if "focus" in msg:
        return False
    return (
        "plugin_error" in msg
        or "connection" in msg
        or "verification" in msg
        or "connected" in msg
        or str(reply.get("verification") or "").lower() == "plugin_error"
    )


def _reply_requires_manual_chat_focus(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" not in msg:
        return False
    diagnostics = reply.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return False
    candidates = diagnostics.get("focusOpenCandidates")
    return isinstance(candidates, list) and not candidates


def _format_autopilot_failure_details(reply: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    message = str(reply.get("message") or "").strip()
    if message:
        lines.append(f"Plugin message: {message}")
    diagnostics = reply.get("diagnostics")
    if isinstance(diagnostics, dict):
        for key in ("ide", "appName", "logPath", "probeLadder", "cacheFocusOpen"):
            if key in diagnostics:
                lines.append(f"{key}: {diagnostics[key]}")
        candidates = diagnostics.get("focusOpenCandidates")
        if isinstance(candidates, list):
            preview = ", ".join(str(item) for item in candidates[:8])
            if len(candidates) > 8:
                preview += f", ... (+{len(candidates) - 8})"
            lines.append(f"focusOpenCandidates: {preview or '(none)'}")
        rejected = diagnostics.get("rejected")
        if isinstance(rejected, list) and rejected:
            lines.append(f"lastRejected: {rejected[-1]}")
    elif reply.get("details"):
        lines.append(f"Details: {reply['details']}")
    return lines


def _warn_autopilot_focus_retry(attempt: int, attempts: int, reply: dict[str, Any] | None = None) -> None:
    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS ERROR] Please place your cursor inside the IDE chat input!")
    print("Make sure the cursor is blinking inside the chat input field.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _warn_autopilot_manual_focus_required(reply: dict[str, Any] | None = None) -> None:
    from koru.activity_log import activity

    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS REQUIRED] Please place your cursor inside the IDE chat input.")
    print("No focus-open command is available, so Koru will not retry this drive automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print("================================================================================")
    print("\033[0m")  # reset colors
    activity(
        "CHAT",
        "manual focus required; no automatic retry",
        data={"reply": reply or {}},
    )


def _warn_autopilot_plugin_retry(attempt: int, attempts: int, reply: dict[str, Any] | None = None) -> None:
    print("\033[1;33m")  # bold yellow
    print("================================================================================")
    print("[AUTOPILOT PLUGIN RETRY] Plugin send did not succeed yet.")
    print("This is usually transient in Windsurf; Koru will retry automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


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
    decision, idle_prompt_kind = _resolve_autopilot_drive_decision(
        project,
        state,
        queue_result,
        drive_prompt=drive_prompt,
        autopilot_action=autopilot_action,
    )
    state.last_driven_prompt = decision.prompt
    # Telemetry hook used by ``_skip_due_to_recent_chat_activity`` to decide
    # whether to apply the escalation-cooldown multiplier on the next cycle.
    state.last_driven_kind = decision.kind
    require_plugin = _plugin_required_for_ide(autopilot_ide)
    attempts = 5
    for attempt in range(attempts):
        reply, ok = _drive_autopilot_once(
            client,
            prompt=decision.prompt,
            submit=submit,
            autopilot_ide=autopilot_ide,
            require_plugin=require_plugin,
        )
        if ok:
            break
        if _reply_missing_autopilot_plugin(reply):
            break
        if _reply_chat_input_busy(reply):
            # Plugin already declined to paste; do not retry within this
            # cycle — the cooldown path on the next cycle will hold us off
            # until the user has cleared their pending chat input.
            break
        if _reply_requires_manual_chat_focus(reply):
            _warn_autopilot_manual_focus_required(reply)
            break
        if _reply_needs_focus_retry(reply) and attempt < attempts - 1:
            _warn_autopilot_focus_retry(attempt, attempts, reply)
            time.sleep(5)
        elif _reply_needs_plugin_retry(reply) and attempt < attempts - 1:
            _warn_autopilot_plugin_retry(attempt, attempts, reply)
            time.sleep(5)
        else:
            break

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
        verification = reply.get("verification", "-")
        if backend in (None, "?") and verification == "-" and not reply.get("event"):
            _hp(
                "  autopilot: no confirmed IDE delivery "
                f"(kind={decision_kind}, queue_status={queue_result.last_status})",
            )
            return
        extra = ""
        if verification != "-":
            extra = f", verification={verification}"
        if reply.get("winning_submit"):
            extra += f", submit={reply['winning_submit']}"
        if reply.get("event"):
            extra += f", event={reply['event']}"
        if decision_kind == "ticket_prompt":
            waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
            _hp(
                "  autopilot: ok (ticket="
                f"{waiting_ticket}, ide={autopilot_ide}, "
                f"backend={backend}, kind={decision_kind}{extra})",
            )
        else:
            _hp(
                "  autopilot: ok "
                f"(ide={autopilot_ide}, backend={backend}, kind={decision_kind}{extra})",
            )
    else:
        if _reply_requires_manual_chat_focus(reply):
            _hp(
                "  autopilot: skipped(manual_focus) "
                f"({reply.get('message', 'unknown error')}, kind={decision_kind})",
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
        plugin_ok = True
        plugin_reason = ""
        if _plugin_required_for_ide(autopilot_ide):
            plugin_ok, plugin_reason = _client_has_usable_plugin(client, autopilot_ide)
            if not plugin_ok:
                _hp(f"- autopilot skipped (plugin_missing: {plugin_reason})")
                cycle_telemetry["autopilot_skipped_plugin_missing"] = True
                return "skipped(plugin_missing)", None, None
        if conflict_reason := _autopilot_terminal_conflict_reason(
            autopilot_ide,
            plugin_connected=plugin_ok and _plugin_required_for_ide(autopilot_ide),
        ):
            _hp(f"- autopilot skipped (ide_mismatch: {conflict_reason})")
            cycle_telemetry["autopilot_skipped_ide_mismatch"] = True
            return "skipped(ide_mismatch)", None, None
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
            if ok:
                autopilot_status = "ok"
            elif _reply_requires_manual_chat_focus(reply):
                autopilot_status = "skipped(manual_focus)"
                cycle_telemetry["autopilot_skipped_manual_focus"] = True
            else:
                autopilot_status = "failed"
            autopilot_backend = (
                str(reply.get("backend")) if reply.get("backend") is not None else None
            )
            if ok:
                state.last_message_sent_ts = time.time()
                state.last_driven_ticket_id = _queue_loop_waiting_ticket_label(queue_result)
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
        from koru.activity_log import activity, activity_info

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
