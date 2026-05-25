
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity import (
    _autopilot_redrive_cooldown_seconds,
    _extract_needs_input_question,
    _skip_due_to_recent_chat_activity,
)
from koru.autonomous_cycle_common import DiagnosticResult, _queue_loop_waiting_ticket_label
from koru.autonomous_cycle_drive_retry import (
    _log_autopilot_result,
    _reply_chat_input_busy,
    _resolve_autopilot_drive_decision,
)
from koru.autonomous_cycle_orchestrator import _handle_autopilot_phase
from koru.autonomous_cycle_skip_conditions import (
    _is_topology_enabled,
)
from koru.autonomous_wup import WupHealthResult
from koru.autonomous_wup import _read_wup_health as _read_wup_health_impl
from koru.autonomy.cycle_finalize import (
    emit_cycle_completion_events as _emit_cycle_completion_events_impl,
)
from koru.autonomy.cycle_trace import (
    decision_next_step_hint as _decision_next_step_hint_impl,
)
from koru.autonomy.cycle_trace import (
    record_decision_trace as _record_decision_trace_impl,
)
from koru.autonomy.env import plugin_required_for_ide as _plugin_required_for_ide
from koru.autonomy.phases.queue_phase import handle_queue_hygiene as _handle_queue_hygiene
from koru.autonomy.phases.verify_phase import (
    handle_post_run_verify_ide as _handle_post_run_verify_ide,
)
from koru.autonomy.post_run_verify import (
    verify_completed_tickets,
)
from koru.autonomy.state import AutoloopState
from koru.environment_profile import environment_profile_payload
from koru.queue import QueueLoopResult, run_planfile_queue_loop
from koru.queue import default_human_prompt as _default_human_prompt
from koru.queue import run_api_request as _run_api_request
from koru.queue import run_llm_request as _run_llm_request
from koru.queue import run_process as _run_process
from koru.queue import run_shell_command as _run_shell_command
from koru.scan import ScanResult, run_scan
from koru.stdio_events import write_stdio_event
from koru.tasks import create_nl_task
from koruide.ide import detect_terminal_host_ide_id

_LEGACY_AUTONOMOUS_CYCLE_EXPORTS = (
    detect_terminal_host_ide_id,
    _plugin_required_for_ide,
    _autopilot_redrive_cooldown_seconds,
    _skip_due_to_recent_chat_activity,
    _extract_needs_input_question,
    _reply_chat_input_busy,
    _resolve_autopilot_drive_decision,
    _log_autopilot_result,
)


def _stdio_info(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def _emit_stdio_cycle_event(
    event_type: str,
    payload: dict,
    *,
    command: str | None = None,
    stdio_format: str,
    correlation_id: str,
) -> None:
    if stdio_format == "jsonl":
        write_stdio_event(
            sys.stdout,
            event_type=event_type,
            correlation_id=correlation_id,
            payload=payload,
            command=command,
        )


def _cycle_human_progress(msg: str, *, stdio_format: str) -> None:
    from koru.activity_log import activity, activity_info

    if msg.startswith("+ "):
        activity("RUN", msg[2:], fmt=stdio_format)
    elif msg.startswith("  scan:"):
        activity("SCAN", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  queue:"):
        activity("QUEUE", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  autopilot:"):
        activity("CHAT", msg.strip(), fmt=stdio_format)
    elif msg.startswith("- autopilot skipped"):
        activity("CHAT", msg[2:].strip(), fmt=stdio_format)
    elif msg.startswith("  decision:"):
        activity("DECISION", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  planfile snapshot:") or msg.startswith(
        ("  what koru auto", "  to give koru work", "  →")
    ):
        activity("KORUAUTONOMOUS", msg.strip(), fmt=stdio_format)
    elif stdio_format == "human":
        activity_info(msg, fmt=stdio_format)
    else:
        activity_info(msg, fmt=stdio_format)


def _current_head(project: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""












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


def _attach_environment_profile(
    project: Path,
    cycle_telemetry: dict[str, Any],
    *,
    autopilot_ide: str,
) -> None:
    try:
        cycle_telemetry["environment_profile"] = environment_profile_payload(
            project,
            ide=autopilot_ide,
        )
    except Exception as exc:
        cycle_telemetry["environment_profile_error"] = f"{type(exc).__name__}: {exc}"


def _heal_stale_socket() -> None:
    """Auto-heal: remove only orphan socket files (not the active daemon's socket)."""
    try:
        from koru.autopilot import default_socket_path
        from koru.ide_adapters.bridge import gc_stale_sockets_for_lane

        target = default_socket_path()
        for removed in gc_stale_sockets_for_lane(target):
            print(f"koru autonomous: auto-healed stale socket {removed}")
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
                state.last_message_sent_ide = str(ev.get("ide") or "")


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
    from koru.autonomy.phases import scan_phase

    scan_phase.run_scan = run_scan

    return scan_phase.handle_scan_phase(
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
    from koru.autonomy.phases import scan_phase

    scan_phase.run_scan = run_scan
    scan_phase._run_code2llm_discovery_after_idle = _run_code2llm_discovery_after_idle

    return scan_phase.handle_scan_after_idle(
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


def _run_code2llm_discovery_after_idle(
    project: Path,
    _hp: callable,
    _emit: callable,
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


def _record_decision_trace(
    *,
    project: Path,
    cycle: int,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    wup_health: WupHealthResult,
    autopilot_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
    stagnation_streak: int,
    _hp: callable,
) -> None:
    _record_decision_trace_impl(
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
        stagnation_streak=stagnation_streak,
        hp=_hp,
    )


def _decision_next_step_hint(
    *,
    queue_status: str,
    autopilot_status: str,
    cycle_telemetry: dict[str, Any],
) -> str:
    return _decision_next_step_hint_impl(
        queue_status=queue_status,
        autopilot_status=autopilot_status,
        cycle_telemetry=cycle_telemetry,
    )


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
    hp: callable,
    emit: callable,
) -> None:
    _emit_cycle_completion_events_impl(
        project=project,
        state=state,
        cycle=cycle,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        cycle_telemetry=cycle_telemetry,
        scan_after_idle_queue=scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
        autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
        hp=hp,
        emit=emit,
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
    _attach_environment_profile(project, cycle_telemetry, autopilot_ide=autopilot_ide)
    _heal_stale_socket()

    def _emit(event_type: str, payload: dict, command: str | None = None) -> None:
        _emit_stdio_cycle_event(
            event_type,
            payload,
            command=command,
            stdio_format=stdio_format,
            correlation_id=correlation_id,
        )

    def _hp(msg: str) -> None:
        _cycle_human_progress(msg, stdio_format=stdio_format)

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
        project=project,
        state=state,
        cycle=cycle,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        cycle_telemetry=cycle_telemetry,
        scan_after_idle_queue=scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
        autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
        hp=_hp,
        emit=_emit,
    )

    return scan_result, queue_result, autopilot_status, diag_result


__all__ = ["AutoloopState", "DiagnosticResult", "run_cycle"]
