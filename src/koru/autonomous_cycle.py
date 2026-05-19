from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .autonomous_wup import WupHealthResult
from .autonomous_wup import _read_wup_health as _read_wup_health_impl
from .autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
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
    project: Path, check_id: str, command: list[str], *, stdio_format: str = "human"
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
            f"- diagnostic ticket marker exists for {check_id}, skipping create", fmt=stdio_format
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
    profile = profile.lower()
    if profile in {"off", "none"}:
        _stdio_info(
            f"koru autonomous: idle diagnostics disabled (profile={profile})",
            fmt=stdio_format,
        )
        return DiagnosticResult(status="off", failed=[])
    if not _is_topology_enabled(
        project, "idle-diagnostics", fallback=True, enabled=topology_integration
    ):
        _stdio_info("koru autonomous: idle diagnostics disabled in topology", fmt=stdio_format)
        return DiagnosticResult(status="disabled(topology)", failed=[])
    _stdio_info(
        f"koru autonomous: queue idle -> running semcod diagnostics (profile={profile})",
        fmt=stdio_format,
    )
    checks: list[tuple[str, str, list[str]]] = []
    if shutil.which("regix"):
        checks.append(
            (
                "regix",
                "regix compare HEAD --local --format rich",
                ["regix", "compare", "HEAD", "--local", "--format", "rich"],
            )
        )
    if shutil.which("wup") and (project / "wup.yaml").is_file():
        checks.append(("wup", "wup status", ["wup", "status"]))
    if profile in {"full", "deep"}:
        if shutil.which("redup"):
            checks.append(
                (
                    "redup",
                    "redup scan . --min-lines 10",
                    ["redup", "scan", ".", "--min-lines", "10"],
                )
            )
        if shutil.which("testql") and any(project.rglob("*.testql.toon.yaml")):
            checks.append(
                (
                    "testql",
                    "testql suite --pattern *.testql.toon.yaml --output console --fail-fast",
                    [
                        "testql",
                        "suite",
                        "--pattern",
                        "*.testql.toon.yaml",
                        "--output",
                        "console",
                        "--fail-fast",
                    ],
                )
            )
        if shutil.which("redsl"):
            checks.append(("redsl", "redsl gate check .", ["redsl", "gate", "check", "."]))
        if (project / "scripts" / "sumr-refresh.sh").is_file():
            checks.append(
                (
                    "sumr",
                    "bash scripts/sumr-refresh.sh --status",
                    ["bash", "scripts/sumr-refresh.sh", "--status"],
                )
            )
    failed: list[str] = []
    diagnostic_state_dir.mkdir(parents=True, exist_ok=True)
    for check_id, summary, command in checks:
        if not _is_topology_enabled(project, check_id, fallback=True, enabled=topology_integration):
            _stdio_info(f"- {check_id} disabled in topology, skipping", fmt=stdio_format)
            continue
        if _run_command_check(project, check_id, command, stdio_format=stdio_format):
            _clear_diagnostic_marker(diagnostic_state_dir, check_id)
            continue
        failed.append(check_id)
        if diagnostic_tickets:
            _create_diagnostic_ticket(
                project=project,
                check_id=check_id,
                summary=summary,
                cycle=cycle,
                queue_status=queue_status,
                queue_name=diagnostic_ticket_queue,
                priority=diagnostic_ticket_priority,
                state_dir=diagnostic_state_dir,
            )
    return DiagnosticResult(status="failed" if failed else "ok", failed=failed)


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
    cycle_telemetry: dict[str, Any] = {
        "autopilot_skipped_idle_streak": False,
        "scan_after_idle_run": False,
        "scan_after_idle_applied": 0,
        "scan_after_idle_skipped_rate_limit": False,
    }

    # Auto-heal: best-effort stale socket removal so daemon restart can bind.
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

    events = _drain_autopilot_events(state)
    if events:
        for ev in events:
            ev_type = ev.get("type", "unknown")
            _hp(f"  event: {ev_type} ide={ev.get('ide', '?')}")
        state.autopilot_events.extend(events)
        for ev in events:
            if ev.get("type") == "message.sent":
                state.last_message_sent_ts = ev.get("ts", time.time())

    scan_result: ScanResult | None = None
    _emit("CycleStarted", {"cycle": cycle, "project": str(project.resolve())})

    stale_minutes = resolve_in_progress_stale_minutes(project)
    if stale_minutes is not None:
        released_stale = release_stale_in_progress_tickets(
            project, stale_minutes=stale_minutes, runner=_run_process
        )
        if released_stale:
            _hp(
                f"  queue hygiene: reopened {released_stale} stale in_progress "
                f"(>{stale_minutes:.0f}m)"
            )
            _emit(
                "QueueStaleReleased",
                {"cycle": cycle, "count": released_stale, "stale_minutes": stale_minutes},
            )

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
            f"  post_run_verify (IDE): tickets={len(ide_verify_outcomes)} "
            f"failed={len(failed_ide)}"
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

    if enable_scan:
        if not _is_topology_enabled(
            project, "scan:on-change", fallback=True, enabled=topology_integration
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
                    f"(clean_streak={state.scan_clean_streak}, HEAD unchanged)"
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
                    project=project, apply=True, include_semcod_artifacts=include_semcod_artifacts
                )
                _hp(
                    f"  scan: suggestions={len(scan_result.suggestions)} "
                    f"applied={len(scan_result.applied)} skipped={len(scan_result.skipped)}"
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

    if not _is_topology_enabled(
        project, "autoloop:queue", fallback=True, enabled=topology_integration
    ):
        _hp("- autoloop queue phase skipped (autoloop:queue disabled in topology)")
        queue_result = QueueLoopResult(0, [], [], [], "disabled", "")
    else:
        qcmd = f"koru --queue --loop --max-iterations {max_iterations}" + (
            " --all-queues" if queue_name is None else f" --queue-name {queue_name}"
        )
        _hp("+ " + qcmd)
        queue_result = run_planfile_queue_loop(
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
        _hp(f"  queue: {queue_result.summary()}")
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
                    f"  post_run_verify (queue): tickets={len(completed_ids)} "
                    f"failed={len(failed)}"
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

    if (
        scan_after_idle_queue
        and queue_result.last_status == "idle"
        and _is_topology_enabled(
            project, "scan:on-change", fallback=True, enabled=topology_integration
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
                f"{scan_after_idle_min_interval_seconds}s, ~{wait:.0f}s remaining)"
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
                project=project, apply=True, include_semcod_artifacts=include_semcod_artifacts
            )
            scan_result = idle_scan
            state.last_scan_after_idle_ts = now
            state.telemetry_scan_after_idle_runs += 1
            state.telemetry_scan_after_idle_tickets_applied += len(idle_scan.applied)
            cycle_telemetry["scan_after_idle_run"] = True
            cycle_telemetry["scan_after_idle_applied"] = len(idle_scan.applied)
            _hp(
                f"  scan: suggestions={len(idle_scan.suggestions)} "
                f"applied={len(idle_scan.applied)} skipped={len(idle_scan.skipped)}"
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

    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    signature = f"{queue_result.last_status}:{waiting_ticket}"
    if state.previous_signature and state.previous_signature == signature:
        state.stagnation_streak += 1
    else:
        state.stagnation_streak = 0
    state.previous_signature = signature

    diag_result = DiagnosticResult(status="skipped", failed=[])
    if queue_result.last_status == "idle" and idle_diagnostics not in {"off", "none"}:
        diag_result = _run_idle_diagnostics(
            stdio_format=stdio_format,
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
                f"new_events={wup_health.new_events}"
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

    if strict_diagnostics and diag_result.status == "failed":
        _emit("AutonomousStopped", {"reason": "strict_diagnostics_failure", "cycle": cycle})
        _stdio_info(
            "koru autonomous: strict diagnostics enabled -> stopping on diagnostics failure",
            fmt=stdio_format,
        )
        raise SystemExit(2)

    autopilot_status = "skipped"
    autopilot_backend: str | None = None
    autopilot_drive_kind: str | None = None
    if enable_autopilot and client is not None:
        if not _is_topology_enabled(
            project, "autopilot:drive", fallback=True, enabled=topology_integration
        ):
            _hp("- autopilot skipped (autopilot:drive disabled in topology)")
            autopilot_status = "skipped(topology)"
        elif autopilot_action == "off":
            _hp("- autopilot action set to off, skipping")
        elif autopilot_on_idle_only and queue_result.last_status != "idle":
            _hp("- autopilot skipped (idle_only)")
            autopilot_status = "skipped(idle_only)"
        elif autopilot_skip_on_diagnostics_fail and diag_result.status == "failed":
            _hp("- autopilot skipped (diagnostics_fail)")
            autopilot_status = "skipped(diagnostics_fail)"
        elif (
            autopilot_skip_drive_idle_streak > 0
            and queue_result.last_status == "idle"
            and state.stagnation_streak >= autopilot_skip_drive_idle_streak
        ):
            _hp(
                "- autopilot skipped "
                f"(idle_streak_{state.stagnation_streak}>={autopilot_skip_drive_idle_streak})"
            )
            autopilot_status = "skipped(idle_streak)"
            state.telemetry_autopilot_idle_streak_skips += 1
            cycle_telemetry["autopilot_skipped_idle_streak"] = True
        elif (
            0 < state.stagnation_streak < DEFAULT_ESCALATION_THRESHOLD
            and _status_in_skip_list(
            queue_result.last_status, autopilot_skip_statuses
            )
        ):
            _hp(
                "- autopilot skipped "
                f"(stuck_{queue_result.last_status}_streak_{state.stagnation_streak})"
            )
            autopilot_status = f"skipped(stuck_{queue_result.last_status})"
        else:
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
            autopilot_drive_kind = idle_prompt_kind or decision.kind
            reply = client.drive(
                decision.prompt,
                submit=submit,
                ide=autopilot_ide,
                require_plugin=(
                    not _allow_keyboard_autopilot_fallback()
                    and not _prefer_keyboard_autopilot()
                ),
            )
            ok = bool(reply.get("ok", True))
            if not ok:
                fallback = _try_os_injector_fallback(decision.prompt, submit=submit)
                if fallback is not None:
                    reply = fallback
                    ok = bool(reply.get("ok", True))
            autopilot_status = "ok" if ok else "failed"
            autopilot_backend = (
                str(reply.get("backend")) if reply.get("backend") is not None else None
            )
            if ok and autopilot_drive_kind == "idle_ticket_prompt":
                ticket_id = extract_ticket_id_from_text(decision.prompt)
                if ticket_id:
                    state.pending_ide_verify_id = ticket_id
            if ok:
                if decision.kind == "escalation_prompt":
                    state.stagnation_streak = 0
                    state.previous_signature = ""
                backend = reply.get("backend", "?")
                if decision.kind == "ticket_prompt":
                    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
                    _hp(
                        "  autopilot: ok (ticket="
                        f"{waiting_ticket}, ide={autopilot_ide}, "
                        f"backend={backend}, kind={decision.kind})"
                    )
                else:
                    _hp(
                        f"  autopilot: ok (ide={autopilot_ide}, "
                        f"backend={backend}, kind={decision.kind})"
                    )
            else:
                _hp(
                    "  autopilot: failed "
                    f"({reply.get('message', 'unknown error')}, kind={decision.kind})"
                )

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
        f"diagnostics={diag_result.status} wup={wup_health.status} autopilot={autopilot_status}"
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
                    "scan_after_idle_tickets_applied": state.telemetry_scan_after_idle_tickets_applied,
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

    return scan_result, queue_result, autopilot_status, diag_result


__all__ = ["AutoloopState", "DiagnosticResult", "run_cycle"]
